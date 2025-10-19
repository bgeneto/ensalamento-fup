"""
Repository for AlocacaoSemestral (Semester Allocation) operations.

Provides data access methods for course-room allocation queries with
conflict detection and availability checking.
"""

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models.allocation import AlocacaoSemestral
from src.schemas.allocation import AlocacaoSemestralRead, AlocacaoSemestralCreate
from src.repositories.base import BaseRepository


class AlocacaoRepository(BaseRepository[AlocacaoSemestral, AlocacaoSemestralRead]):
    """Repository for AlocacaoSemestral CRUD and queries."""

    def __init__(self, session: Session):
        """Initialize AlocacaoRepository.

        Args:
            session: SQLAlchemy session
        """
        super().__init__(session, AlocacaoSemestral)

    def orm_to_dto(self, orm_obj: AlocacaoSemestral) -> AlocacaoSemestralRead:
        """Convert ORM AlocacaoSemestral model to AlocacaoSemestralRead DTO.

        Args:
            orm_obj: AlocacaoSemestral ORM model instance

        Returns:
            AlocacaoSemestralRead DTO
        """
        return AlocacaoSemestralRead(
            id=orm_obj.id,
            semestre_id=orm_obj.semestre_id,
            demanda_id=orm_obj.demanda_id,
            sala_id=orm_obj.sala_id,
            dia_semana_id=orm_obj.dia_semana_id,
            codigo_bloco=orm_obj.codigo_bloco,
        )

    def dto_to_orm_create(self, dto: AlocacaoSemestralCreate) -> AlocacaoSemestral:
        """Convert AlocacaoSemestralCreate DTO to ORM AlocacaoSemestral model for creation.

        Args:
            dto: AlocacaoSemestralCreate DTO

        Returns:
            AlocacaoSemestral ORM model instance (not persisted)
        """
        return AlocacaoSemestral(
            semestre_id=dto.semestre_id,
            demanda_id=dto.demanda_id,
            sala_id=dto.sala_id,
            dia_semana_id=dto.dia_semana_id,
            codigo_bloco=dto.codigo_bloco,
        )

    # ========================================================================
    # DOMAIN-SPECIFIC QUERY METHODS
    # ========================================================================

    def get_by_demanda(self, demanda_id: int) -> List[AlocacaoSemestralRead]:
        """Get all allocations for a specific course demand.

        Args:
            demanda_id: Course demand ID

        Returns:
            List of AlocacaoSemestralRead DTOs
        """
        orm_objs = (
            self.session.query(AlocacaoSemestral)
            .filter(AlocacaoSemestral.demanda_id == demanda_id)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_sala(self, sala_id: int) -> List[AlocacaoSemestralRead]:
        """Get all allocations in a specific room.

        Args:
            sala_id: Room ID

        Returns:
            List of AlocacaoSemestralRead DTOs sorted by day and time
        """
        orm_objs = (
            self.session.query(AlocacaoSemestral)
            .filter(AlocacaoSemestral.sala_id == sala_id)
            .order_by(AlocacaoSemestral.dia_semana_id, AlocacaoSemestral.codigo_bloco)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_sala_and_dia(
        self, sala_id: int, dia_semana_id: int
    ) -> List[AlocacaoSemestralRead]:
        """Get all allocations in a room on a specific day.

        Args:
            sala_id: Room ID
            dia_semana_id: Weekday ID

        Returns:
            List of AlocacaoSemestralRead DTOs sorted by time block
        """
        orm_objs = (
            self.session.query(AlocacaoSemestral)
            .filter(
                and_(
                    AlocacaoSemestral.sala_id == sala_id,
                    AlocacaoSemestral.dia_semana_id == dia_semana_id,
                )
            )
            .order_by(AlocacaoSemestral.codigo_bloco)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_horario(
        self, dia_semana_id: int, codigo_bloco: str
    ) -> List[AlocacaoSemestralRead]:
        """Get all allocations at a specific time slot.

        Args:
            dia_semana_id: Weekday ID
            codigo_bloco: Time block code (M1, M2, T1, etc.)

        Returns:
            List of AlocacaoSemestralRead DTOs
        """
        orm_objs = (
            self.session.query(AlocacaoSemestral)
            .filter(
                and_(
                    AlocacaoSemestral.dia_semana_id == dia_semana_id,
                    AlocacaoSemestral.codigo_bloco == codigo_bloco,
                )
            )
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def check_conflict(
        self,
        sala_id: int,
        dia_semana_id: int,
        codigo_bloco: str,
        exclude_alocacao_id: Optional[int] = None,
    ) -> bool:
        """Check if there's a conflict (double-booking) at a specific time slot.

        Args:
            sala_id: Room ID
            dia_semana_id: Weekday ID
            codigo_bloco: Time block code
            exclude_alocacao_id: Allocation ID to exclude (for updates)

        Returns:
            True if conflict exists, False otherwise
        """
        query = self.session.query(AlocacaoSemestral).filter(
            and_(
                AlocacaoSemestral.sala_id == sala_id,
                AlocacaoSemestral.dia_semana_id == dia_semana_id,
                AlocacaoSemestral.codigo_bloco == codigo_bloco,
            )
        )

        if exclude_alocacao_id:
            query = query.filter(AlocacaoSemestral.id != exclude_alocacao_id)

        return query.first() is not None

    def get_conflicts_in_room(self, sala_id: int) -> List[Tuple[int, str]]:
        """Get all conflicting time slots in a room (multiple courses at same time).

        Args:
            sala_id: Room ID

        Returns:
            List of (dia_semana_id, codigo_bloco) tuples with conflicts
        """
        # Get all allocations in room
        allocations = self.get_by_sala(sala_id)

        # Find time slots with multiple allocations
        time_slots = {}
        for alloc in allocations:
            key = (alloc.dia_semana_id, alloc.codigo_bloco)
            time_slots[key] = time_slots.get(key, 0) + 1

        # Return only conflicted slots (count > 1)
        return [key for key, count in time_slots.items() if count > 1]

    def get_by_semestre(self, semestre_id: int) -> List[AlocacaoSemestralRead]:
        """Get all allocations in a specific semester.

        Args:
            semestre_id: Semester ID

        Returns:
            List of AlocacaoSemestralRead DTOs
        """
        orm_objs = (
            self.session.query(AlocacaoSemestral)
            .filter(AlocacaoSemestral.semestre_id == semestre_id)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_allocation_summary(self) -> dict:
        """Get allocation statistics and summary.

        Returns:
            Dictionary with statistics:
            - total_allocations: Total number of allocations
            - total_demands_allocated: Total unique demands with allocations
            - total_rooms_allocated: Total unique rooms allocated
            - total_conflicts: Total number of conflicting time slots
            - rooms_with_conflicts: List of room IDs with conflicts
        """
        all_allocs = self.get_all()

        # Get unique values
        demands = set(a.demanda_id for a in all_allocs)
        rooms = set(a.sala_id for a in all_allocs)

        # Find rooms with conflicts
        rooms_with_conflicts = set()
        for alloc in all_allocs:
            if self.check_conflict(
                alloc.sala_id,
                alloc.dia_semana_id,
                alloc.codigo_bloco,
                exclude_alocacao_id=alloc.id,
            ):
                rooms_with_conflicts.add(alloc.sala_id)

        return {
            "total_allocations": len(all_allocs),
            "total_demands_allocated": len(demands),
            "total_rooms_allocated": len(rooms),
            "total_conflicts": len(rooms_with_conflicts),
            "rooms_with_conflicts": list(rooms_with_conflicts),
        }

    def get_room_schedule(self, sala_id: int) -> dict:
        """Get complete schedule for a room (organized by day and time).

        Args:
            sala_id: Room ID

        Returns:
            Nested dictionary: {dia_id: {codigo_bloco: [allocation_ids]}}
        """
        allocations = self.get_by_sala(sala_id)

        schedule = {}
        for alloc in allocations:
            dia = alloc.dia_semana_id
            bloco = alloc.codigo_bloco

            if dia not in schedule:
                schedule[dia] = {}
            if bloco not in schedule[dia]:
                schedule[dia][bloco] = []

            schedule[dia][bloco].append(alloc.id)

        return schedule
