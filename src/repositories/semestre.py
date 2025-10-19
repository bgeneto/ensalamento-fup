"""
Repository for semester management (Semestre)

Implements the Repository pattern for semester data access,
providing a clean abstraction over database operations with
proper session management and ORM ↔ DTO conversion.
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import joinedload
from sqlalchemy import func

from database import DatabaseSession, Semestre as SemestreORM, Demanda as DemandaORM
from database import AlocacaoSemestral as AlocacaoSemestralORM
from src.repositories.base import BaseRepository
from src.schemas.semestre import (
    SemestreDTO,
    SemestreCreateDTO,
    SemestreUpdateDTO,
    SemestreSimplifiedDTO,
    DemandaDTO,
    DemandaCreateDTO,
    DemandaUpdateDTO,
)

logger = logging.getLogger(__name__)


class SemestreRepository(BaseRepository[SemestreORM, SemestreDTO]):
    """
    Repository for semester operations.

    Provides CRUD operations and custom queries for semesters,
    with automatic ORM ↔ DTO conversion at session boundaries.

    Usage:
        repo = SemestreRepository()
        semesters = repo.get_all_with_counts()
        for sem in semesters:
            print(f"{sem.nome}: {sem.demandas_count} demands, {sem.alocacoes_count} allocations")
    """

    @property
    def orm_model(self) -> type:
        """Return the ORM model class"""
        return SemestreORM

    def orm_to_dto(self, orm_obj: SemestreORM) -> SemestreDTO:
        """
        Convert ORM object to DTO.

        Args:
            orm_obj: SQLAlchemy ORM model instance

        Returns:
            SemestreDTO: Data transfer object with counts
        """
        try:
            # Count related objects while session is open
            demandas_count = len(orm_obj.demandas) if orm_obj.demandas else 0
            alocacoes_count = 0
            if orm_obj.demandas:
                for demanda in orm_obj.demandas:
                    if demanda.alocacoes_semestrais:
                        alocacoes_count += len(demanda.alocacoes_semestrais)

            return SemestreDTO(
                id=orm_obj.id,
                nome=orm_obj.nome,
                status=orm_obj.status,
                demandas_count=demandas_count,
                alocacoes_count=alocacoes_count,
            )
        except Exception as e:
            logger.error(f"Error converting Semestre to DTO: {e}", exc_info=True)
            return SemestreDTO(
                id=orm_obj.id,
                nome=orm_obj.nome,
                status=orm_obj.status,
            )

    def dto_to_orm_create(self, dto: SemestreCreateDTO) -> dict:
        """
        Convert create DTO to ORM constructor kwargs.

        Args:
            dto: SemestreCreateDTO with creation data

        Returns:
            dict: Kwargs for ORM model constructor
        """
        return {
            "nome": dto.nome,
            "status": dto.status,
        }

    def get_all_with_counts(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[SemestreDTO]:
        """
        Get all semesters with demand and allocation counts.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List[SemestreDTO]: All semesters with counts
        """
        try:
            with DatabaseSession() as session:
                query = session.query(self.orm_model).options(
                    joinedload(SemestreORM.demandas).joinedload(
                        DemandaORM.alocacoes_semestrais
                    ),
                )

                if limit:
                    query = query.limit(limit)
                if offset:
                    query = query.offset(offset)

                orm_objs = query.all()
                return [self.orm_to_dto(obj) for obj in orm_objs]
        except Exception as e:
            logger.error(f"Error getting all semesters with counts: {e}", exc_info=True)
            return []

    def get_by_status(self, status: str) -> List[SemestreDTO]:
        """
        Get all semesters with a specific status.

        Args:
            status: Status to filter by (e.g., "Planejamento", "Execução", "Finalizado")

        Returns:
            List[SemestreDTO]: Matching semesters
        """
        try:
            with DatabaseSession() as session:
                query = (
                    session.query(self.orm_model)
                    .filter(SemestreORM.status == status)
                    .options(
                        joinedload(SemestreORM.demandas).joinedload(
                            DemandaORM.alocacoes_semestrais
                        ),
                    )
                )

                orm_objs = query.all()
                return [self.orm_to_dto(obj) for obj in orm_objs]
        except Exception as e:
            logger.error(
                f"Error getting semesters by status {status}: {e}", exc_info=True
            )
            return []

    def get_active(self) -> List[SemestreDTO]:
        """
        Get all active semesters (Execução status).

        Returns:
            List[SemestreDTO]: Active semesters
        """
        return self.get_by_status("Execução")

    def get_by_nome(self, nome: str) -> Optional[SemestreDTO]:
        """
        Get a semester by name.

        Args:
            nome: Semester name (e.g., "2024.1")

        Returns:
            Optional[SemestreDTO]: Semester if found, None otherwise
        """
        try:
            with DatabaseSession() as session:
                orm_obj = (
                    session.query(self.orm_model)
                    .filter(SemestreORM.nome == nome)
                    .options(
                        joinedload(SemestreORM.demandas).joinedload(
                            DemandaORM.alocacoes_semestrais
                        ),
                    )
                    .first()
                )

                if orm_obj:
                    return self.orm_to_dto(orm_obj)
                return None
        except Exception as e:
            logger.error(f"Error getting semester by name {nome}: {e}", exc_info=True)
            return None

    def get_simplified(self) -> List[SemestreSimplifiedDTO]:
        """
        Get all semesters in simplified format (for dropdowns).

        Returns:
            List[SemestreSimplifiedDTO]: Simplified semester list
        """
        try:
            with DatabaseSession() as session:
                orm_objs = session.query(self.orm_model).all()

                return [
                    SemestreSimplifiedDTO(
                        id=obj.id,
                        nome=obj.nome,
                        status=obj.status,
                    )
                    for obj in orm_objs
                ]
        except Exception as e:
            logger.error(f"Error getting simplified semesters: {e}", exc_info=True)
            return []

    def get_latest(self) -> Optional[SemestreDTO]:
        """
        Get the most recently created semester.

        Returns:
            Optional[SemestreDTO]: Latest semester or None
        """
        try:
            with DatabaseSession() as session:
                orm_obj = (
                    session.query(self.orm_model)
                    .order_by(SemestreORM.id.desc())
                    .first()
                )

                if orm_obj:
                    return self.orm_to_dto(orm_obj)
                return None
        except Exception as e:
            logger.error(f"Error getting latest semester: {e}", exc_info=True)
            return None


# ============================================================================
# DEMAND REPOSITORY
# ============================================================================


class DemandaRepository(BaseRepository[DemandaORM, DemandaDTO]):
    """
    Repository for demand operations.

    Provides CRUD operations and custom queries for demands,
    with automatic ORM ↔ DTO conversion at session boundaries.

    Usage:
        repo = DemandaRepository()
        demands = repo.get_by_semestre(1)
    """

    @property
    def orm_model(self) -> type:
        """Return the ORM model class"""
        return DemandaORM

    def orm_to_dto(self, orm_obj: DemandaORM) -> DemandaDTO:
        """
        Convert ORM object to DTO.

        Args:
            orm_obj: SQLAlchemy ORM model instance

        Returns:
            DemandaDTO: Data transfer object
        """
        try:
            alocacoes_count = (
                len(orm_obj.alocacoes_semestrais) if orm_obj.alocacoes_semestrais else 0
            )

            return DemandaDTO(
                id=orm_obj.id,
                semestre_id=orm_obj.semestre_id,
                codigo_disciplina=orm_obj.codigo_disciplina,
                nome_disciplina=orm_obj.nome_disciplina,
                professores_disciplina=orm_obj.professores_disciplina,
                turma_disciplina=orm_obj.turma_disciplina,
                vagas_disciplina=orm_obj.vagas_disciplina,
                horario_sigaa_bruto=orm_obj.horario_sigaa_bruto,
                nivel_disciplina=orm_obj.nivel_disciplina,
                alocacoes_count=alocacoes_count,
            )
        except Exception as e:
            logger.error(f"Error converting Demanda to DTO: {e}", exc_info=True)
            return DemandaDTO(
                id=orm_obj.id,
                semestre_id=orm_obj.semestre_id,
                codigo_disciplina=orm_obj.codigo_disciplina,
                horario_sigaa_bruto=orm_obj.horario_sigaa_bruto,
            )

    def dto_to_orm_create(self, dto: DemandaCreateDTO) -> dict:
        """
        Convert create DTO to ORM constructor kwargs.

        Args:
            dto: DemandaCreateDTO with creation data

        Returns:
            dict: Kwargs for ORM model constructor
        """
        return {
            "semestre_id": dto.semestre_id,
            "codigo_disciplina": dto.codigo_disciplina,
            "nome_disciplina": dto.nome_disciplina,
            "professores_disciplina": dto.professores_disciplina,
            "turma_disciplina": dto.turma_disciplina,
            "vagas_disciplina": dto.vagas_disciplina,
            "horario_sigaa_bruto": dto.horario_sigaa_bruto,
            "nivel_disciplina": dto.nivel_disciplina,
        }

    def get_by_semestre(self, semestre_id: int) -> List[DemandaDTO]:
        """
        Get all demands for a specific semester.

        Args:
            semestre_id: Semester ID

        Returns:
            List[DemandaDTO]: Demands for the semester
        """
        try:
            with DatabaseSession() as session:
                orm_objs = (
                    session.query(self.orm_model)
                    .filter(DemandaORM.semestre_id == semestre_id)
                    .options(
                        joinedload(DemandaORM.alocacoes_semestrais),
                    )
                    .all()
                )

                return [self.orm_to_dto(obj) for obj in orm_objs]
        except Exception as e:
            logger.error(
                f"Error getting demands by semestre {semestre_id}: {e}", exc_info=True
            )
            return []

    def get_by_codigo(self, codigo_disciplina: str) -> List[DemandaDTO]:
        """
        Get demands by discipline code.

        Args:
            codigo_disciplina: Discipline code

        Returns:
            List[DemandaDTO]: Matching demands
        """
        try:
            with DatabaseSession() as session:
                orm_objs = (
                    session.query(self.orm_model)
                    .filter(DemandaORM.codigo_disciplina == codigo_disciplina)
                    .options(
                        joinedload(DemandaORM.alocacoes_semestrais),
                    )
                    .all()
                )

                return [self.orm_to_dto(obj) for obj in orm_objs]
        except Exception as e:
            logger.error(
                f"Error getting demands by codigo {codigo_disciplina}: {e}",
                exc_info=True,
            )
            return []

    def get_by_semestre_and_codigo(
        self, semestre_id: int, codigo_disciplina: str
    ) -> Optional[DemandaDTO]:
        """
        Get a specific demand by semester and code.

        Args:
            semestre_id: Semester ID
            codigo_disciplina: Discipline code

        Returns:
            Optional[DemandaDTO]: Demand if found, None otherwise
        """
        try:
            with DatabaseSession() as session:
                orm_obj = (
                    session.query(self.orm_model)
                    .filter(
                        DemandaORM.semestre_id == semestre_id,
                        DemandaORM.codigo_disciplina == codigo_disciplina,
                    )
                    .options(
                        joinedload(DemandaORM.alocacoes_semestrais),
                    )
                    .first()
                )

                if orm_obj:
                    return self.orm_to_dto(orm_obj)
                return None
        except Exception as e:
            logger.error(
                f"Error getting demand by semestre and codigo: {e}", exc_info=True
            )
            return None


# ============================================================================
# SINGLETON FACTORIES
# ============================================================================


_semestre_repository: Optional[SemestreRepository] = None
_demanda_repository: Optional[DemandaRepository] = None


def get_semestre_repository() -> SemestreRepository:
    """
    Get or create the singleton SemestreRepository instance.

    Returns:
        SemestreRepository: Singleton instance
    """
    global _semestre_repository
    if _semestre_repository is None:
        _semestre_repository = SemestreRepository()
    return _semestre_repository


def get_demanda_repository() -> DemandaRepository:
    """
    Get or create the singleton DemandaRepository instance.

    Returns:
        DemandaRepository: Singleton instance
    """
    global _demanda_repository
    if _demanda_repository is None:
        _demanda_repository = DemandaRepository()
    return _demanda_repository
