"""
Repository for ReservaEvento operations.
"""

from sqlalchemy.orm import Session
from typing import Optional, List
from sqlalchemy import and_, or_

from src.repositories.base import BaseRepository
from src.models.allocation import ReservaEvento
from src.schemas.allocation import (
    ReservaEventoCreate,
    ReservaEventoRead,
    ReservaEventoReadWithOccurrences,
)


class ReservaEventoRepository(BaseRepository[ReservaEvento, ReservaEventoRead]):
    """
    Repository for ReservaEvento operations.
    """

    def __init__(self, session: Session):
        super().__init__(session, ReservaEvento)

    def orm_to_dto(self, orm_obj: ReservaEvento) -> ReservaEventoRead:
        """Convert ReservaEvento ORM to DTO."""
        return ReservaEventoRead(
            id=orm_obj.id,
            sala_id=orm_obj.sala_id,
            titulo_evento=orm_obj.titulo_evento,
            username_criador=orm_obj.username_criador,
            nome_solicitante=orm_obj.nome_solicitante,
            nome_responsavel=orm_obj.nome_responsavel,
            regra_recorrencia_json=orm_obj.regra_recorrencia_json,
            status=orm_obj.status,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def dto_to_orm_create(self, dto: ReservaEventoCreate) -> ReservaEvento:
        """Convert ReservaEventoCreate DTO to ORM model."""
        return ReservaEvento(
            sala_id=dto.sala_id,
            titulo_evento=dto.titulo_evento,
            username_criador=dto.username_criador,
            nome_solicitante=dto.nome_solicitante,
            nome_responsavel=dto.nome_responsavel,
            regra_recorrencia_json=dto.regra_recorrencia_json,
            status=dto.status,
        )

    def get_by_creator(self, username: str) -> List[ReservaEventoRead]:
        """
        Get events by creator username.

        Args:
            username: Username of the creator

        Returns:
            List of events created by the user
        """
        orm_objs = (
            self.session.query(self.model_class)
            .filter(self.model_class.username_criador == username)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_room(self, room_id: int) -> List[ReservaEventoRead]:
        """
        Get events by room.

        Args:
            room_id: Room ID

        Returns:
            List of events for the room
        """
        orm_objs = (
            self.session.query(self.model_class)
            .filter(self.model_class.sala_id == room_id)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_room_in_date_range(
        self, room_id: int, start_date: str, end_date: str
    ) -> List[ReservaEventoRead]:
        """
        Get events for a room within a date range.

        Args:
            room_id: Room ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of events that have occurrences in the date range
        """
        # Query events that might have occurrences in the date range
        # This is a simplified check - the actual date filtering happens
        # when checking occurrences
        orm_objs = (
            self.session.query(self.model_class)
            .filter(
                and_(
                    self.model_class.sala_id == room_id,
                    # For now, we'll return all events for the room
                    # The actual date filtering should happen at the occurrence level
                )
            )
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_with_occurrences(
        self, event_id: int
    ) -> Optional[ReservaEventoReadWithOccurrences]:
        """
        Get event with all its occurrences.

        Args:
            event_id: Event ID

        Returns:
            Event with occurrences or None if not found
        """
        orm_obj = (
            self.session.query(self.model_class)
            .filter(self.model_class.id == event_id)
            .first()
        )
        if not orm_obj:
            return None

        # Convert to basic DTO
        evento_dto = self.orm_to_dto(orm_obj)

        # Get occurrences
        from src.repositories.reserva_ocorrencia import ReservaOcorrenciaRepository

        ocorrencia_repo = ReservaOcorrenciaRepository(self.session)
        ocorrencias = ocorrencia_repo.get_by_evento(event_id)

        # Create enhanced DTO
        return ReservaEventoReadWithOccurrences(
            **evento_dto.model_dump(),
            ocorrencias=ocorrencias,
        )

    def get_active_events_for_room(
        self, room_id: int, start_date: str, end_date: str
    ) -> List[ReservaEventoRead]:
        """
        Get active events for a room within a date range.

        Args:
            room_id: Room ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of active events for the room
        """
        orm_objs = (
            self.session.query(self.model_class)
            .filter(
                and_(
                    self.model_class.sala_id == room_id,
                    self.model_class.status == "Aprovada",
                )
            )
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def check_room_availability(
        self, room_id: int, data_reserva: str, codigo_bloco: str
    ) -> bool:
        """
        Check if a room is available for a specific date and time block.

        Args:
            room_id: Room ID
            data_reserva: Date in YYYY-MM-DD format
            codigo_bloco: Time block code

        Returns:
            True if available, False if there's a conflict
        """
        from src.repositories.reserva_ocorrencia import ReservaOcorrenciaRepository

        ocorrencia_repo = ReservaOcorrenciaRepository(self.session)
        conflicting_occurrences = ocorrencia_repo.get_conflicting_occurrences(
            room_id, data_reserva, codigo_bloco
        )

        return len(conflicting_occurrences) == 0

    def search_events(
        self,
        query: str,
        room_id: Optional[int] = None,
        creator_username: Optional[str] = None,
    ) -> List[ReservaEventoRead]:
        """
        Search events by title, requester, or responsible person.

        Args:
            query: Search query string
            room_id: Optional room filter
            creator_username: Optional creator filter

        Returns:
            List of matching events
        """
        filters = [
            or_(
                self.model_class.titulo_evento.ilike(f"%{query}%"),
                self.model_class.nome_solicitante.ilike(f"%{query}%"),
                self.model_class.nome_responsavel.ilike(f"%{query}%"),
            )
        ]

        if room_id:
            filters.append(self.model_class.sala_id == room_id)

        if creator_username:
            filters.append(self.model_class.username_criador == creator_username)

        orm_objs = self.session.query(self.model_class).filter(and_(*filters)).all()
        return [self.orm_to_dto(obj) for obj in orm_objs]
