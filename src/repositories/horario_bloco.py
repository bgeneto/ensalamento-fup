"""
Repository for HorarioBloco (Time Block) operations.

Provides data access methods for time slot queries organized by period
(morning, afternoon, night).
"""

from typing import List

from sqlalchemy.orm import Session

from src.models.horario import HorarioBloco
from src.schemas.horario import HorarioBlocoRead, HorarioBlocoCreate
from src.repositories.base import BaseRepository


class HorarioBlocoRepository(BaseRepository[HorarioBloco, HorarioBlocoRead]):
    """Repository for HorarioBloco CRUD and queries."""

    def __init__(self, session: Session):
        """Initialize HorarioBlocoRepository.

        Args:
            session: SQLAlchemy session
        """
        super().__init__(session, HorarioBloco)

    def orm_to_dto(self, orm_obj: HorarioBloco) -> HorarioBlocoRead:
        """Convert ORM HorarioBloco model to HorarioBlocoRead DTO.

        Args:
            orm_obj: HorarioBloco ORM model instance

        Returns:
            HorarioBlocoRead DTO
        """
        return HorarioBlocoRead(
            codigo_bloco=orm_obj.codigo_bloco,
            turno=orm_obj.turno,
            horario_inicio=orm_obj.horario_inicio,
            horario_fim=orm_obj.horario_fim,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def dto_to_orm_create(self, dto: HorarioBlocoCreate) -> HorarioBloco:
        """Convert HorarioBlocoCreate DTO to ORM HorarioBloco model for creation.

        Args:
            dto: HorarioBlocoCreate DTO

        Returns:
            HorarioBloco ORM model instance (not persisted)
        """
        return HorarioBloco(
            codigo_bloco=dto.codigo_bloco,
            turno=dto.turno,
            horario_inicio=dto.horario_inicio,
            horario_fim=dto.horario_fim,
        )

    # ========================================================================
    # DOMAIN-SPECIFIC QUERY METHODS
    # ========================================================================

    def get_by_codigo_bloco(self, codigo_bloco: str) -> HorarioBlocoRead:
        """Get time block by code (M1, M2, T1, T2, N1, N2, etc.).

        Args:
            codigo_bloco: Time block code

        Returns:
            HorarioBlocoRead DTO or None if not found
        """
        orm_obj = (
            self.session.query(HorarioBloco)
            .filter(HorarioBloco.codigo_bloco == codigo_bloco)
            .first()
        )
        if orm_obj:
            return self.orm_to_dto(orm_obj)
        return None

    def get_morning(self) -> List[HorarioBlocoRead]:
        """Get morning time blocks (turno='M').

        Returns:
            List of HorarioBlocoRead DTOs for morning periods, sorted by code
        """
        orm_objs = (
            self.session.query(HorarioBloco)
            .filter(HorarioBloco.turno == "M")
            .order_by(HorarioBloco.codigo_bloco)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_afternoon(self) -> List[HorarioBlocoRead]:
        """Get afternoon time blocks (turno='T').

        Returns:
            List of HorarioBlocoRead DTOs for afternoon periods, sorted by code
        """
        orm_objs = (
            self.session.query(HorarioBloco)
            .filter(HorarioBloco.turno == "T")
            .order_by(HorarioBloco.codigo_bloco)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_night(self) -> List[HorarioBlocoRead]:
        """Get night time blocks (turno='N').

        Returns:
            List of HorarioBlocoRead DTOs for night periods, sorted by code
        """
        orm_objs = (
            self.session.query(HorarioBloco)
            .filter(HorarioBloco.turno == "N")
            .order_by(HorarioBloco.codigo_bloco)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_turno(self, turno: str) -> List[HorarioBlocoRead]:
        """Get all time blocks for a specific shift.

        Args:
            turno: Shift code (M, T, or N)

        Returns:
            List of HorarioBlocoRead DTOs sorted by code
        """
        orm_objs = (
            self.session.query(HorarioBloco)
            .filter(HorarioBloco.turno == turno)
            .order_by(HorarioBloco.codigo_bloco)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_all_ordered(self) -> List[HorarioBlocoRead]:
        """Get all time blocks ordered by shift and code (morning, afternoon, night).

        Returns:
            List of all HorarioBlocoRead DTOs in chronological order
        """
        # Create a sort order mapping: M=morning, T=afternoon, N=night
        turno_order = {"M": 0, "T": 1, "N": 2}

        orm_objs = self.session.query(HorarioBloco).all()

        # Sort by turno order then by codigo_bloco
        sorted_objs = sorted(
            orm_objs, key=lambda x: (turno_order.get(x.turno, 3), x.codigo_bloco)
        )

        return [self.orm_to_dto(obj) for obj in sorted_objs]

    def get_dict_by_codigo(self) -> dict:
        """Get all time blocks as dictionary with codigo_bloco as key.

        Returns:
            Dictionary mapping codigo_bloco -> HorarioBlocoRead DTO
        """
        blocos = self.get_all()
        return {bloco.codigo_bloco: bloco for bloco in blocos}

    def get_dict_by_turno(self) -> dict:
        """Get all time blocks grouped by turno (shift).

        Returns:
            Dictionary mapping turno -> list of HorarioBlocoRead DTOs
        """
        result = {
            "M": self.get_morning(),
            "T": self.get_afternoon(),
            "N": self.get_night(),
        }
        return result

    def get_statistics(self) -> dict:
        """Get time block statistics.

        Returns:
            Dictionary with statistics:
            - total_blocks: Total number of time blocks
            - by_period: Count by period
            - periods: List of available periods
        """
        all_blocks = self.get_all()

        if not all_blocks:
            return {
                "total_blocks": 0,
                "by_period": {},
                "periods": [],
            }

        by_period = {}
        for block in all_blocks:
            period = block.periodo or "Sem Período"
            by_period[period] = by_period.get(period, 0) + 1

        return {
            "total_blocks": len(all_blocks),
            "by_period": by_period,
            "periods": sorted(by_period.keys()),
        }
