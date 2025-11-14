"""
Repository for Regra operations.

Provides data access methods for allocation rules (hard and soft constraints for disciplines).
"""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.models.allocation import Regra
from src.schemas.allocation import RegraRead, RegraCreate
from src.repositories.base import BaseRepository


class RegraRepository(BaseRepository[Regra, RegraRead]):
    """Repository for Regra CRUD and queries."""

    def __init__(self, session: Session):
        """Initialize RegraRepository.

        Args:
            session: SQLAlchemy session
        """
        super().__init__(session, Regra)

    def orm_to_dto(self, orm_obj: Regra) -> RegraRead:
        """Convert ORM Regra model to RegraRead DTO.

        Args:
            orm_obj: Regra ORM model instance

        Returns:
            RegraRead DTO
        """
        return RegraRead(
            id=orm_obj.id,
            descricao=orm_obj.descricao,
            tipo_regra=orm_obj.tipo_regra,
            config_json=orm_obj.config_json,
            prioridade=orm_obj.prioridade,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def dto_to_orm_create(self, dto: RegraCreate) -> Regra:
        """Convert RegraCreate DTO to ORM Regra model for creation.

        Args:
            dto: RegraCreate DTO

        Returns:
            Regra ORM model instance (not persisted)
        """
        return Regra(
            descricao=dto.descricao,
            tipo_regra=dto.tipo_regra,
            config_json=dto.config_json,
            prioridade=dto.prioridade,
        )

    # ========================================================================
    # DOMAIN-SPECIFIC QUERY METHODS
    # ========================================================================

    def get_by_tipo(self, tipo_regra: str) -> List[RegraRead]:
        """Get all rules of a specific type.

        Args:
            tipo_regra: Rule type (e.g., "DISCIPLINA_TIPO_SALA")

        Returns:
            List of RegraRead DTOs
        """
        orm_objs = (
            self.session.query(Regra)
            .filter(Regra.tipo_regra == tipo_regra)
            .order_by(Regra.descricao)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_hard_rules(self) -> List[RegraRead]:
        """Get all hard rules (prioridade = 0).

        Returns:
            List of RegraRead DTOs sorted by type and description
        """
        orm_objs = (
            self.session.query(Regra)
            .filter(Regra.prioridade == 0)
            .order_by(Regra.tipo_regra, Regra.descricao)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_soft_rules(self) -> List[RegraRead]:
        """Get all soft rules (prioridade > 0).

        Returns:
            List of RegraRead DTOs sorted by priority descending, then description
        """
        orm_objs = (
            self.session.query(Regra)
            .filter(Regra.prioridade > 0)
            .order_by(Regra.prioridade.desc(), Regra.descricao)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def find_rules_by_disciplina(self, codigo_disciplina: str) -> List[RegraRead]:
        """Find all rules that apply to a specific discipline.

        Args:
            codigo_disciplina: Discipline code to search for

        Returns:
            List of RegraRead DTOs that reference this discipline
        """
        # Search in config_json for disciplina references
        # This is a bit hacky since we're searching JSON as text
        pattern = f"%{codigo_disciplina}%"

        orm_objs = (
            self.session.query(Regra)
            .filter(Regra.config_json.like(pattern))
            .order_by(Regra.prioridade, Regra.tipo_regra)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def search_by_descricao(self, search_term: str) -> List[RegraRead]:
        """Search rules by description (case-insensitive).

        Args:
            search_term: Search term for description

        Returns:
            List of RegraRead DTOs
        """
        orm_objs = (
            self.session.query(Regra)
            .filter(Regra.descricao.ilike(f"%{search_term}%"))
            .order_by(Regra.tipo_regra, Regra.descricao)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_used_tipos_regra(self) -> List[str]:
        """Get all unique rule types currently in use.

        Returns:
            List of unique tipo_regra values
        """
        # Get all distinct tipo_regra values
        result = (
            self.session.query(Regra.tipo_regra)
            .distinct()
            .order_by(Regra.tipo_regra)
            .all()
        )
        return [row[0] for row in result]

    def get_statistics(self) -> dict:
        """Get rule statistics.

        Returns:
            Dictionary with statistics:
            - total_regras: Total number of rules
            - regras_duras: Count of hard rules (prioridade=0)
            - regras_suaves: Count of soft rules (prioridade>0)
            - tipos_distintos: Number of different rule types used
        """
        all_regras = self.get_all()

        if not all_regras:
            return {
                "total_regras": 0,
                "regras_duras": 0,
                "regras_suaves": 0,
                "tipos_distintos": 0,
            }

        regras_duras = sum(1 for r in all_regras if r.prioridade == 0)
        regras_suaves = len(all_regras) - regras_duras
        tipos_distintos = len(set(r.tipo_regra for r in all_regras))

        return {
            "total_regras": len(all_regras),
            "regras_duras": regras_duras,
            "regras_suaves": regras_suaves,
            "tipos_distintos": tipos_distintos,
        }
