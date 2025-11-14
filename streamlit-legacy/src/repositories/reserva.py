"""
Repository for ReservaEsporadica operations.
"""

from sqlalchemy.orm import Session
from typing import Optional

from src.repositories.base import BaseRepository
from src.models.allocation import ReservaEsporadica
from src.schemas.allocation import ReservaEsporadicaCreate, ReservaEsporadicaRead


class ReservaRepository(BaseRepository[ReservaEsporadica, ReservaEsporadicaRead]):
    """
    Repository for ReservaEsporadica operations.
    """

    def __init__(self, session: Session):
        super().__init__(session, ReservaEsporadica)

    def orm_to_dto(self, orm_obj: ReservaEsporadica) -> ReservaEsporadicaRead:
        """Convert ReservaEsporadica ORM to DTO."""
        return ReservaEsporadicaRead(
            id=orm_obj.id,
            sala_id=orm_obj.sala_id,
            username_solicitante=orm_obj.username_solicitante,
            titulo_evento=orm_obj.titulo_evento,
            data_reserva=orm_obj.data_reserva,
            codigo_bloco=orm_obj.codigo_bloco,
            status=orm_obj.status,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def dto_to_orm_create(self, dto: ReservaEsporadicaCreate) -> ReservaEsporadica:
        """Convert ReservaEsporadicaCreate DTO to ORM model."""
        return ReservaEsporadica(
            sala_id=dto.sala_id,
            username_solicitante=dto.username_solicitante,
            titulo_evento=dto.titulo_evento,
            data_reserva=dto.data_reserva,
            codigo_bloco=dto.codigo_bloco,
            status=dto.status,
        )

    def get_by_user(self, username: str) -> list[ReservaEsporadicaRead]:
        """
        Get reservations by user.

        Args:
            username: Username of the user

        Returns:
            List of reservations for the user
        """
        orm_objs = (
            self.session.query(self.model_class)
            .filter(self.model_class.username_solicitante == username)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_room(self, room_id: int) -> list[ReservaEsporadicaRead]:
        """
        Get reservations by room.

        Args:
            room_id: Room ID

        Returns:
            List of reservations for the room
        """
        orm_objs = (
            self.session.query(self.model_class)
            .filter(self.model_class.sala_id == room_id)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def check_conflict(
        self, sala_id: int, codigo_bloco: str, data_reserva: str
    ) -> bool:
        """
        Check if there's a conflict for a given room, block, and date.

        Args:
            sala_id: Room ID
            codigo_bloco: Block code (e.g., 'M1', 'T2')
            data_reserva: Reservation date (YYYY-MM-DD)

        Returns:
            True if there's a conflict, False otherwise
        """
        existing = (
            self.session.query(self.model_class)
            .filter(
                self.model_class.sala_id == sala_id,
                self.model_class.codigo_bloco == codigo_bloco,
                self.model_class.data_reserva == data_reserva,
            )
            .first()
        )
        return existing is not None
