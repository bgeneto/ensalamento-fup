"""
Repository for ReservaOcorrencia operations.
"""

from datetime import date
from sqlalchemy.orm import Session
from typing import Optional, List
from sqlalchemy import and_, or_

from src.repositories.base import BaseRepository
from src.models.allocation import ReservaOcorrencia
from src.schemas.allocation import (
    ReservaOcorrenciaCreate,
    ReservaOcorrenciaRead,
    ReservaOcorrenciaReadWithEvent,
)


class ReservaOcorrenciaRepository(
    BaseRepository[ReservaOcorrencia, ReservaOcorrenciaRead]
):
    """
    Repository for ReservaOcorrencia operations.
    """

    def __init__(self, session: Session):
        super().__init__(session, ReservaOcorrencia)

    def orm_to_dto(self, orm_obj: ReservaOcorrencia) -> ReservaOcorrenciaRead:
        """Convert ReservaOcorrencia ORM to DTO."""
        return ReservaOcorrenciaRead(
            id=orm_obj.id,
            evento_id=orm_obj.evento_id,
            data_reserva=orm_obj.data_reserva,
            codigo_bloco=orm_obj.codigo_bloco,
            status_excecao=orm_obj.status_excecao,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def dto_to_orm_create(self, dto: ReservaOcorrenciaCreate) -> ReservaOcorrencia:
        """Convert ReservaOcorrenciaCreate DTO to ORM model."""
        return ReservaOcorrencia(
            evento_id=dto.evento_id,
            data_reserva=dto.data_reserva,
            codigo_bloco=dto.codigo_bloco,
            status_excecao=dto.status_excecao,
        )

    def get_by_evento(self, evento_id: int) -> List[ReservaOcorrenciaRead]:
        """
        Get all occurrences for a specific event.

        Args:
            evento_id: Event ID

        Returns:
            List of occurrences for the event
        """
        orm_objs = (
            self.session.query(self.model_class)
            .filter(self.model_class.evento_id == evento_id)
            .order_by(self.model_class.data_reserva, self.model_class.codigo_bloco)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_room_and_date(
        self, room_id: int, data_reserva: str
    ) -> List[ReservaOcorrenciaRead]:
        """
        Get occurrences for a room on a specific date.

        Args:
            room_id: Room ID
            data_reserva: Date in YYYY-MM-DD format

        Returns:
            List of occurrences for the room and date
        """
        orm_objs = (
            self.session.query(self.model_class)
            .join(self.model_class.evento)
            .filter(
                and_(
                    self.model_class.data_reserva == data_reserva,
                    self.model_class.evento.has(sala_id=room_id),
                )
            )
            .order_by(self.model_class.codigo_bloco)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_active_occurrences(
        self, room_id: int, data_reserva: str
    ) -> List[ReservaOcorrenciaRead]:
        """
        Get active (non-cancelled) occurrences for a room on a specific date.

        Args:
            room_id: Room ID
            data_reserva: Date in YYYY-MM-DD format

        Returns:
            List of active occurrences
        """
        orm_objs = (
            self.session.query(self.model_class)
            .join(self.model_class.evento)
            .filter(
                and_(
                    self.model_class.data_reserva == data_reserva,
                    self.model_class.evento.has(sala_id=room_id),
                    or_(
                        self.model_class.status_excecao.is_(None),
                        self.model_class.status_excecao != "Cancelada",
                    ),
                )
            )
            .order_by(self.model_class.codigo_bloco)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_conflicting_occurrences(
        self, room_id: int, data_reserva: str, codigo_bloco: str
    ) -> List[ReservaOcorrenciaRead]:
        """
        Get occurrences that conflict with a specific room, date, and time block.

        Args:
            room_id: Room ID
            data_reserva: Date in YYYY-MM-DD format
            codigo_bloco: Time block code

        Returns:
            List of conflicting occurrences
        """
        orm_objs = (
            self.session.query(self.model_class)
            .join(self.model_class.evento)
            .filter(
                and_(
                    self.model_class.data_reserva == data_reserva,
                    self.model_class.codigo_bloco == codigo_bloco,
                    self.model_class.evento.has(sala_id=room_id),
                    or_(
                        self.model_class.status_excecao.is_(None),
                        self.model_class.status_excecao != "Cancelada",
                    ),
                )
            )
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def create_bulk(
        self, ocorrencias_dtos: List[ReservaOcorrenciaCreate]
    ) -> List[ReservaOcorrenciaRead]:
        """
        Create multiple occurrences efficiently.

        Args:
            ocorrencias_dtos: List of occurrence DTOs to create

        Returns:
            List of created occurrences
        """
        orm_objs = [self.dto_to_orm_create(dto) for dto in ocorrencias_dtos]

        # Add all objects to session
        self.session.add_all(orm_objs)

        # Commit all at once
        self.session.commit()

        # Refresh all objects to get their IDs
        for orm_obj in orm_objs:
            self.session.refresh(orm_obj)

        return [self.orm_to_dto(obj) for obj in orm_objs]

    def delete_by_evento(self, evento_id: int) -> int:
        """
        Delete all occurrences for a specific event.

        Args:
            evento_id: Event ID

        Returns:
            Number of occurrences deleted
        """
        count = (
            self.session.query(self.model_class)
            .filter(self.model_class.evento_id == evento_id)
            .delete()
        )
        self.session.commit()
        return count

    def cancel_occurrence(self, occurrence_id: int) -> bool:
        """
        Cancel a specific occurrence.

        Args:
            occurrence_id: Occurrence ID

        Returns:
            True if cancelled, False if not found
        """
        orm_obj = (
            self.session.query(self.model_class)
            .filter(self.model_class.id == occurrence_id)
            .first()
        )
        if not orm_obj:
            return False

        orm_obj.status_excecao = "Cancelada"
        self.session.commit()
        return True

    def get_with_event(
        self, occurrence_id: int
    ) -> Optional[ReservaOcorrenciaReadWithEvent]:
        """
        Get occurrence with its parent event.

        Args:
            occurrence_id: Occurrence ID

        Returns:
            Occurrence with event or None if not found
        """
        orm_obj = (
            self.session.query(self.model_class)
            .filter(self.model_class.id == occurrence_id)
            .first()
        )
        if not orm_obj:
            return None

        # Convert to basic DTO
        ocorrencia_dto = self.orm_to_dto(orm_obj)

        # Get parent event
        from src.repositories.reserva_evento import ReservaEventoRepository

        evento_repo = ReservaEventoRepository(self.session)
        evento = evento_repo.get_by_id(orm_obj.evento_id)

        # Create enhanced DTO
        return ReservaOcorrenciaReadWithEvent(
            **ocorrencia_dto.model_dump(),
            evento=evento,
        )

    def get_occurrences_in_date_range(
        self, room_id: int, start_date: str, end_date: str
    ) -> List[ReservaOcorrenciaRead]:
        """
        Get occurrences for a room within a date range.

        Args:
            room_id: Room ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of occurrences in the date range
        """
        orm_objs = (
            self.session.query(self.model_class)
            .join(self.model_class.evento)
            .filter(
                and_(
                    self.model_class.data_reserva >= start_date,
                    self.model_class.data_reserva <= end_date,
                    self.model_class.evento.has(sala_id=room_id),
                    or_(
                        self.model_class.status_excecao.is_(None),
                        self.model_class.status_excecao != "Cancelada",
                    ),
                )
            )
            .order_by(self.model_class.data_reserva, self.model_class.codigo_bloco)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def check_duplicate_occurrence(
        self, evento_id: int, data_reserva: str, codigo_bloco: str
    ) -> bool:
        """
        Check if a specific occurrence already exists.

        Args:
            evento_id: Event ID
            data_reserva: Date in YYYY-MM-DD format
            codigo_bloco: Time block code

        Returns:
            True if duplicate exists, False otherwise
        """
        existing = (
            self.session.query(self.model_class)
            .filter(
                and_(
                    self.model_class.evento_id == evento_id,
                    self.model_class.data_reserva == data_reserva,
                    self.model_class.codigo_bloco == codigo_bloco,
                )
            )
            .first()
        )
        return existing is not None

    def get_ocorrencias_by_date_range(
        self, start_date: date, end_date: date, room_ids: Optional[List[int]] = None
    ) -> List[ReservaOcorrencia]:
        """
        Get occurrences within a date range, optionally filtered by rooms.

        Args:
            start_date: Start date
            end_date: End date
            room_ids: Optional list of room IDs to filter by

        Returns:
            List of occurrence ORM objects (with eager loaded relationships)
        """
        from src.models.allocation import ReservaEvento

        # Start with base query
        query = self.session.query(self.model_class)

        # Apply date range filter
        query = query.filter(
            and_(
                self.model_class.data_reserva >= start_date.strftime("%Y-%m-%d"),
                self.model_class.data_reserva <= end_date.strftime("%Y-%m-%d"),
            )
        )

        # Apply room filter if provided by joining with evento
        if room_ids:
            query = query.join(
                ReservaEvento, self.model_class.evento_id == ReservaEvento.id
            ).filter(ReservaEvento.sala_id.in_(room_ids))

        # Order by date and time
        query = query.order_by(
            self.model_class.data_reserva, self.model_class.codigo_bloco
        )

        return query.all()
