"""
Repository for Professor operations.

Provides data access methods for professor queries with filters
and search capabilities.
"""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.models.academic import Professor
from src.schemas.academic import ProfessorRead, ProfessorCreate
from src.repositories.base import BaseRepository


class ProfessorRepository(BaseRepository[Professor, ProfessorRead]):
    """Repository for Professor CRUD and queries."""

    def __init__(self, session: Session):
        """Initialize ProfessorRepository.

        Args:
            session: SQLAlchemy session
        """
        super().__init__(session, Professor)

    def orm_to_dto(self, orm_obj: Professor) -> ProfessorRead:
        """Convert ORM Professor model to ProfessorRead DTO.

        Args:
            orm_obj: Professor ORM model instance

        Returns:
            ProfessorRead DTO
        """
        return ProfessorRead(
            id=orm_obj.id,
            nome_completo=orm_obj.nome_completo,
            username_login=orm_obj.username_login,
            tem_baixa_mobilidade=orm_obj.tem_baixa_mobilidade,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def dto_to_orm_create(self, dto: ProfessorCreate) -> Professor:
        """Convert ProfessorCreate DTO to ORM Professor model for creation.

        Args:
            dto: ProfessorCreate DTO

        Returns:
            Professor ORM model instance (not persisted)
        """
        return Professor(
            nome_completo=dto.nome_completo,
            username_login=getattr(dto, "username_login", None),
            tem_baixa_mobilidade=getattr(dto, "tem_baixa_mobilidade", False),
        )

    # ========================================================================
    # DOMAIN-SPECIFIC QUERY METHODS
    # ========================================================================

    def get_by_username_login(self, username_login: str) -> Optional[ProfessorRead]:
        """Get professor by SIGAA username login.

        Args:
            username_login: Professor SIGAA username

        Returns:
            ProfessorRead DTO or None if not found
        """
        orm_obj = (
            self.session.query(Professor)
            .filter(Professor.username_login == username_login)
            .first()
        )
        if orm_obj:
            return self.orm_to_dto(orm_obj)
        return None

    def get_by_nome_completo(self, nome: str) -> Optional[ProfessorRead]:
        """Get professor by exact full name.

        Args:
            nome: Full professor name

        Returns:
            ProfessorRead DTO or None if not found
        """
        orm_obj = (
            self.session.query(Professor)
            .filter(Professor.nome_completo == nome)
            .first()
        )
        if orm_obj:
            return self.orm_to_dto(orm_obj)
        return None

    def search(self, query: str) -> List[ProfessorRead]:
        """Search professors by name or username (case-insensitive).

        Args:
            query: Search query (partial match)

        Returns:
            List of ProfessorRead DTOs sorted by name
        """
        pattern = f"%{query}%"
        orm_objs = (
            self.session.query(Professor)
            .filter(
                or_(
                    Professor.nome_completo.ilike(pattern),
                    (
                        Professor.username_login.ilike(pattern)
                        if Professor.username_login is not None
                        else False
                    ),
                )
            )
            .order_by(Professor.nome_completo)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def search_by_name(self, name_pattern: str) -> List[ProfessorRead]:
        """Search professors by name (case-insensitive, partial match).

        Args:
            name_pattern: Name pattern (e.g., 'João' to find all professors with João)

        Returns:
            List of ProfessorRead DTOs sorted by name
        """
        orm_objs = (
            self.session.query(Professor)
            .filter(Professor.nome_completo.ilike(f"%{name_pattern}%"))
            .order_by(Professor.nome_completo)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_with_mobility_restrictions(self) -> List[ProfessorRead]:
        """Get all professors with mobility restrictions.

        Returns:
            List of ProfessorRead DTOs sorted by name
        """
        orm_objs = (
            self.session.query(Professor)
            .filter(Professor.tem_baixa_mobilidade == True)
            .order_by(Professor.nome_completo)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_statistics(self) -> dict:
        """Get professor statistics.

        Returns:
            Dictionary with statistics:
            - total_professors: Total number of professors
            - with_mobility_restrictions: Count with mobility restrictions
            - without_restrictions: Count without restrictions
        """
        all_profs = self.get_all()

        if not all_profs:
            return {
                "total_professors": 0,
                "with_mobility_restrictions": 0,
                "without_restrictions": 0,
            }

        with_restrictions = sum(1 for p in all_profs if p.tem_baixa_mobilidade)
        without_restrictions = len(all_profs) - with_restrictions

        return {
            "total_professors": len(all_profs),
            "with_mobility_restrictions": with_restrictions,
            "without_restrictions": without_restrictions,
        }
