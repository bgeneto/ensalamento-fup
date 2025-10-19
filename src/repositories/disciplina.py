"""
Repository for Demanda (Course Demand) operations.

Provides data access methods for course demand queries with filters,
search capabilities, and enrollment information.
"""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.models.academic import Demanda
from src.schemas.academic import DemandaRead, DemandaCreate
from src.repositories.base import BaseRepository


class DisciplinaRepository(BaseRepository[Demanda, DemandaRead]):
    """Repository for Demanda CRUD and queries."""

    def __init__(self, session: Session):
        """Initialize DisciplinaRepository.

        Args:
            session: SQLAlchemy session
        """
        super().__init__(session, Demanda)

    def orm_to_dto(self, orm_obj: Demanda) -> DemandaRead:
        """Convert ORM Demanda model to DemandaRead DTO.

        Args:
            orm_obj: Demanda ORM model instance

        Returns:
            DemandaRead DTO
        """
        return DemandaRead(
            id=orm_obj.id,
            semestre_id=orm_obj.semestre_id,
            codigo_disciplina=orm_obj.codigo_disciplina,
            nome_disciplina=orm_obj.nome_disciplina,
            professores_disciplina=orm_obj.professores_disciplina,
            turma_disciplina=orm_obj.turma_disciplina,
            vagas_disciplina=orm_obj.vagas_disciplina,
            horario_sigaa_bruto=orm_obj.horario_sigaa_bruto,
            nivel_disciplina=orm_obj.nivel_disciplina,
            nao_alocar=orm_obj.nao_alocar,
        )

    def dto_to_orm_create(self, dto: DemandaCreate) -> Demanda:
        """Convert DemandaCreate DTO to ORM Demanda model for creation.

        Args:
            dto: DemandaCreate DTO

        Returns:
            Demanda ORM model instance (not persisted)
        """
        return Demanda(
            semestre_id=dto.semestre_id,
            codigo_disciplina=dto.codigo_disciplina,
            nome_disciplina=dto.nome_disciplina,
            professores_disciplina=dto.professores_disciplina,
            turma_disciplina=dto.turma_disciplina,
            vagas_disciplina=dto.vagas_disciplina,
            horario_sigaa_bruto=dto.horario_sigaa_bruto,
            nivel_disciplina=dto.nivel_disciplina,
            nao_alocar=dto.nao_alocar,
        )

    # ========================================================================
    # DOMAIN-SPECIFIC QUERY METHODS
    # ========================================================================

    def get_by_codigo(self, codigo: str) -> Optional[DemandaRead]:
        """Get course demand by course code.

        Args:
            codigo: Course code (e.g., 'CIC0001')

        Returns:
            DemandaRead DTO or None if not found
        """
        orm_obj = (
            self.session.query(Demanda)
            .filter(Demanda.codigo_disciplina == codigo)
            .first()
        )
        if orm_obj:
            return self.orm_to_dto(orm_obj)
        return None

    def get_by_semestre(self, semestre_id: int) -> List[DemandaRead]:
        """Get all course demands in a specific semester.

        Args:
            semestre_id: Semester ID

        Returns:
            List of DemandaRead DTOs sorted by course code
        """
        orm_objs = (
            self.session.query(Demanda)
            .filter(Demanda.semestre_id == semestre_id)
            .order_by(Demanda.codigo_disciplina)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_professor_name(self, professor_name: str) -> List[DemandaRead]:
        """Get all course demands for a specific professor.

        Args:
            professor_name: Professor name (partial match)

        Returns:
            List of DemandaRead DTOs sorted by course code
        """
        orm_objs = (
            self.session.query(Demanda)
            .filter(Demanda.professores_disciplina.ilike(f"%{professor_name}%"))
            .order_by(Demanda.codigo_disciplina)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_nivel(self, nivel: str) -> List[DemandaRead]:
        """Get courses by level (Graduação, Pós-Graduação).

        Args:
            nivel: Course level

        Returns:
            List of DemandaRead DTOs sorted by course code
        """
        orm_objs = (
            self.session.query(Demanda)
            .filter(Demanda.nivel_disciplina == nivel)
            .order_by(Demanda.codigo_disciplina)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def search(self, query: str) -> List[DemandaRead]:
        """Search courses by code or name (case-insensitive).

        Args:
            query: Search query (partial match)

        Returns:
            List of DemandaRead DTOs sorted by course code
        """
        pattern = f"%{query}%"
        orm_objs = (
            self.session.query(Demanda)
            .filter(
                or_(
                    Demanda.codigo_disciplina.ilike(pattern),
                    Demanda.nome_disciplina.ilike(pattern),
                )
            )
            .order_by(Demanda.codigo_disciplina)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def search_by_name(self, name_pattern: str) -> List[DemandaRead]:
        """Search courses by name (case-insensitive, partial match).

        Args:
            name_pattern: Course name pattern

        Returns:
            List of DemandaRead DTOs sorted by course code
        """
        orm_objs = (
            self.session.query(Demanda)
            .filter(Demanda.nome_disciplina.ilike(f"%{name_pattern}%"))
            .order_by(Demanda.codigo_disciplina)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_large_courses(self, min_vagas: int) -> List[DemandaRead]:
        """Get courses with enrollment above threshold.

        Args:
            min_vagas: Minimum number of students

        Returns:
            List of DemandaRead DTOs sorted by enrollment (highest first)
        """
        orm_objs = (
            self.session.query(Demanda)
            .filter(Demanda.vagas_disciplina >= min_vagas)
            .order_by(Demanda.vagas_disciplina.desc())
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_small_courses(self, max_vagas: int) -> List[DemandaRead]:
        """Get courses with enrollment below threshold.

        Args:
            max_vagas: Maximum number of students

        Returns:
            List of DemandaRead DTOs sorted by enrollment (lowest first)
        """
        orm_objs = (
            self.session.query(Demanda)
            .filter(Demanda.vagas_disciplina <= max_vagas)
            .order_by(Demanda.vagas_disciplina)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_allocatable(self, semestre_id: int) -> List[DemandaRead]:
        """Get courses that should be allocated (nao_alocar=False).

        Args:
            semestre_id: Semester ID

        Returns:
            List of allocatable course demands
        """
        orm_objs = (
            self.session.query(Demanda)
            .filter(
                (Demanda.semestre_id == semestre_id) & (Demanda.nao_alocar == False)
            )
            .order_by(Demanda.codigo_disciplina)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_skip_allocation(self, semestre_id: int) -> List[DemandaRead]:
        """Get courses marked to skip allocation.

        Args:
            semestre_id: Semester ID

        Returns:
            List of DemandaRead DTOs marked with nao_alocar=True
        """
        orm_objs = (
            self.session.query(Demanda)
            .filter((Demanda.semestre_id == semestre_id) & (Demanda.nao_alocar == True))
            .order_by(Demanda.codigo_disciplina)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_statistics_for_semester(self, semestre_id: int) -> dict:
        """Get course demand statistics for a semester.

        Args:
            semestre_id: Semester ID

        Returns:
            Dictionary with statistics:
            - total_demands: Total number of demands
            - total_vagas: Total enrollment across all courses
            - avg_vagas: Average students per course
            - max_vagas: Largest course enrollment
            - min_vagas: Smallest course enrollment
            - demands_over_50: Number of demands with 50+ students
            - demands_over_100: Number of demands with 100+ students
            - skip_allocation: Number of demands marked to skip
        """
        demands = self.get_by_semestre(semestre_id)

        if not demands:
            return {
                "total_demands": 0,
                "total_vagas": 0,
                "avg_vagas": 0,
                "max_vagas": 0,
                "min_vagas": 0,
                "demands_over_50": 0,
                "demands_over_100": 0,
                "skip_allocation": 0,
            }

        vagas = [d.vagas_disciplina for d in demands]
        skip_count = len(self.get_skip_allocation(semestre_id))

        return {
            "total_demands": len(demands),
            "total_vagas": sum(vagas),
            "avg_vagas": sum(vagas) / len(vagas) if vagas else 0,
            "max_vagas": max(vagas) if vagas else 0,
            "min_vagas": min(vagas) if vagas else 0,
            "demands_over_50": len([v for v in vagas if v >= 50]),
            "demands_over_100": len([v for v in vagas if v >= 100]),
            "skip_allocation": skip_count,
        }

    def get_all_by_semestre_sorted(self, semestre_id: int) -> List[DemandaRead]:
        """Get all course demands in semester, sorted by code.

        Args:
            semestre_id: Semester ID

        Returns:
            List of DemandaRead DTOs
        """
        return self.get_by_semestre(semestre_id)
