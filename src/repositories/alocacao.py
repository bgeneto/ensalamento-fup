"""
Repository for semester allocations (AlocacaoSemestral)

Implements the Repository pattern for allocation data access,
providing a clean abstraction over database operations with
proper session management and ORM ↔ DTO conversion.
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import joinedload

from database import DatabaseSession, AlocacaoSemestral as AlocacaoSemestralORM
from database import Demanda as DemandaORM, Sala as SalaORM, DiaSemana as DiaSemanaORM
from src.repositories.base import BaseRepository
from src.schemas.alocacao import (
    AlocacaoSemestralDTO,
    AlocacaoCreateDTO,
    AlocacaoUpdateDTO,
    AlocacaoSimplifiedDTO,
)

logger = logging.getLogger(__name__)


class AlocacaoRepository(BaseRepository[AlocacaoSemestralORM, AlocacaoSemestralDTO]):
    """
    Repository for semester allocation operations.

    Provides CRUD operations and custom queries for allocations,
    with automatic ORM ↔ DTO conversion at session boundaries.

    Usage:
        repo = AlocacaoRepository()
        allocations = repo.get_all_with_eager_load()
        for alloc in allocations:
            print(f"{alloc.sala_nome} - {alloc.disciplina_codigo}")
    """

    @property
    def orm_model(self) -> type:
        """Return the ORM model class"""
        return AlocacaoSemestralORM

    def orm_to_dto(self, orm_obj: AlocacaoSemestralORM) -> AlocacaoSemestralDTO:
        """
        Convert ORM object to DTO while session is open.

        This is called inside the DatabaseSession context,
        so all relationships are accessible.

        Args:
            orm_obj: SQLAlchemy ORM model instance

        Returns:
            AlocacaoSemestralDTO: Complete data transfer object

        Raises:
            AttributeError: If relationships cannot be accessed
        """
        try:
            # Access all relationships INSIDE the session
            sala_nome = orm_obj.sala.nome if orm_obj.sala else None
            sala_capacidade = orm_obj.sala.capacidade if orm_obj.sala else None
            predio_nome = (
                orm_obj.sala.predio.nome
                if orm_obj.sala and orm_obj.sala.predio
                else None
            )
            dia_semana_nome = orm_obj.dia_semana.nome if orm_obj.dia_semana else None

            horario_bloco_dto = None
            if orm_obj.horario_bloco:
                horario_bloco_dto = {
                    "codigo_bloco": orm_obj.horario_bloco.codigo_bloco,
                    "descricao": orm_obj.horario_bloco.descricao,
                    "horario_inicio": orm_obj.horario_bloco.horario_inicio,
                    "horario_fim": orm_obj.horario_bloco.horario_fim,
                }

            disciplina_codigo = (
                orm_obj.demanda.codigo_disciplina if orm_obj.demanda else None
            )
            disciplina_nome = (
                orm_obj.demanda.nome_disciplina if orm_obj.demanda else None
            )
            turma = orm_obj.demanda.turma_disciplina if orm_obj.demanda else None

            # Create DTO with plain data (no ORM objects)
            return AlocacaoSemestralDTO(
                id=orm_obj.id,
                demanda_id=orm_obj.demanda_id,
                sala_id=orm_obj.sala_id,
                dia_semana_id=orm_obj.dia_semana_id,
                codigo_bloco=orm_obj.codigo_bloco,
                sala_nome=sala_nome,
                sala_capacidade=sala_capacidade,
                predio_nome=predio_nome,
                dia_semana_nome=dia_semana_nome,
                horario_bloco=horario_bloco_dto,
                disciplina_codigo=disciplina_codigo,
                disciplina_nome=disciplina_nome,
                turma=turma,
            )
        except Exception as e:
            logger.error(
                f"Error converting AlocacaoSemestral to DTO: {e}",
                exc_info=True,
            )
            # Return minimal DTO on error
            return AlocacaoSemestralDTO(
                id=orm_obj.id,
                demanda_id=orm_obj.demanda_id,
                sala_id=orm_obj.sala_id,
                dia_semana_id=orm_obj.dia_semana_id,
                codigo_bloco=orm_obj.codigo_bloco,
            )

    def dto_to_orm_create(self, dto: AlocacaoCreateDTO) -> dict:
        """
        Convert create DTO to ORM constructor kwargs.

        Args:
            dto: AlocacaoCreateDTO with creation data

        Returns:
            dict: Kwargs for ORM model constructor
        """
        return {
            "demanda_id": dto.demanda_id,
            "sala_id": dto.sala_id,
            "dia_semana_id": dto.dia_semana_id,
            "codigo_bloco": dto.codigo_bloco,
        }

    def get_all_with_eager_load(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[AlocacaoSemestralDTO]:
        """
        Get all allocations with eager-loaded relationships.

        Eager loading prevents N+1 queries and allows access to
        relationships within the session context.

        Args:
            limit: Maximum number of results (None for all)
            offset: Number of results to skip

        Returns:
            List[AlocacaoSemestralDTO]: All allocations as DTOs

        Example:
            allocations = repo.get_all_with_eager_load(limit=100)
            for alloc in allocations:
                print(f"{alloc.sala_nome} - {alloc.disciplina_codigo}")
        """
        try:
            with DatabaseSession() as session:
                query = session.query(self.orm_model).options(
                    joinedload(AlocacaoSemestralORM.sala).joinedload(SalaORM.predio),
                    joinedload(AlocacaoSemestralORM.demanda),
                    joinedload(AlocacaoSemestralORM.dia_semana),
                    joinedload(AlocacaoSemestralORM.horario_bloco),
                )

                if limit:
                    query = query.limit(limit)
                if offset:
                    query = query.offset(offset)

                orm_objs = query.all()
                # Convert all while still in session context
                return [self.orm_to_dto(obj) for obj in orm_objs]
        except Exception as e:
            logger.error(f"Error getting all allocations: {e}", exc_info=True)
            return []

    def get_by_sala(self, sala_id: int) -> List[AlocacaoSemestralDTO]:
        """
        Get all allocations for a specific room.

        Args:
            sala_id: Room ID

        Returns:
            List[AlocacaoSemestralDTO]: Allocations for the room
        """
        try:
            with DatabaseSession() as session:
                query = (
                    session.query(self.orm_model)
                    .filter(AlocacaoSemestralORM.sala_id == sala_id)
                    .options(
                        joinedload(AlocacaoSemestralORM.sala).joinedload(
                            SalaORM.predio
                        ),
                        joinedload(AlocacaoSemestralORM.demanda),
                        joinedload(AlocacaoSemestralORM.dia_semana),
                        joinedload(AlocacaoSemestralORM.horario_bloco),
                    )
                )

                orm_objs = query.all()
                return [self.orm_to_dto(obj) for obj in orm_objs]
        except Exception as e:
            logger.error(
                f"Error getting allocations by sala {sala_id}: {e}", exc_info=True
            )
            return []

    def get_by_demanda(self, demanda_id: int) -> List[AlocacaoSemestralDTO]:
        """
        Get all allocations for a specific demand.

        Args:
            demanda_id: Demand ID

        Returns:
            List[AlocacaoSemestralDTO]: Allocations for the demand
        """
        try:
            with DatabaseSession() as session:
                query = (
                    session.query(self.orm_model)
                    .filter(AlocacaoSemestralORM.demanda_id == demanda_id)
                    .options(
                        joinedload(AlocacaoSemestralORM.sala).joinedload(
                            SalaORM.predio
                        ),
                        joinedload(AlocacaoSemestralORM.demanda),
                        joinedload(AlocacaoSemestralORM.dia_semana),
                        joinedload(AlocacaoSemestralORM.horario_bloco),
                    )
                )

                orm_objs = query.all()
                return [self.orm_to_dto(obj) for obj in orm_objs]
        except Exception as e:
            logger.error(
                f"Error getting allocations by demanda {demanda_id}: {e}", exc_info=True
            )
            return []

    def get_by_dia_semana(self, dia_semana_id: int) -> List[AlocacaoSemestralDTO]:
        """
        Get all allocations for a specific day of week.

        Args:
            dia_semana_id: Day of week ID (from SIGAA)

        Returns:
            List[AlocacaoSemestralDTO]: Allocations for the day
        """
        try:
            with DatabaseSession() as session:
                query = (
                    session.query(self.orm_model)
                    .filter(AlocacaoSemestralORM.dia_semana_id == dia_semana_id)
                    .options(
                        joinedload(AlocacaoSemestralORM.sala).joinedload(
                            SalaORM.predio
                        ),
                        joinedload(AlocacaoSemestralORM.demanda),
                        joinedload(AlocacaoSemestralORM.dia_semana),
                        joinedload(AlocacaoSemestralORM.horario_bloco),
                    )
                )

                orm_objs = query.all()
                return [self.orm_to_dto(obj) for obj in orm_objs]
        except Exception as e:
            logger.error(
                f"Error getting allocations by dia_semana {dia_semana_id}: {e}",
                exc_info=True,
            )
            return []

    def get_by_bloco(self, codigo_bloco: str) -> List[AlocacaoSemestralDTO]:
        """
        Get all allocations for a specific time block.

        Args:
            codigo_bloco: Time block code

        Returns:
            List[AlocacaoSemestralDTO]: Allocations in the block
        """
        try:
            with DatabaseSession() as session:
                query = (
                    session.query(self.orm_model)
                    .filter(AlocacaoSemestralORM.codigo_bloco == codigo_bloco)
                    .options(
                        joinedload(AlocacaoSemestralORM.sala).joinedload(
                            SalaORM.predio
                        ),
                        joinedload(AlocacaoSemestralORM.demanda),
                        joinedload(AlocacaoSemestralORM.dia_semana),
                        joinedload(AlocacaoSemestralORM.horario_bloco),
                    )
                )

                orm_objs = query.all()
                return [self.orm_to_dto(obj) for obj in orm_objs]
        except Exception as e:
            logger.error(
                f"Error getting allocations by bloco {codigo_bloco}: {e}", exc_info=True
            )
            return []

    def get_simplified(self) -> List[AlocacaoSimplifiedDTO]:
        """
        Get simplified allocations for dropdowns/lists.

        Returns much less data than full DTOs.

        Returns:
            List[AlocacaoSimplifiedDTO]: Simplified allocations
        """
        try:
            with DatabaseSession() as session:
                query = session.query(self.orm_model).options(
                    joinedload(AlocacaoSemestralORM.sala),
                    joinedload(AlocacaoSemestralORM.demanda),
                    joinedload(AlocacaoSemestralORM.dia_semana),
                    joinedload(AlocacaoSemestralORM.horario_bloco),
                )

                orm_objs = query.all()
                result = []
                for obj in orm_objs:
                    try:
                        result.append(
                            AlocacaoSimplifiedDTO(
                                id=obj.id,
                                sala_nome=obj.sala.nome if obj.sala else "",
                                disciplina_codigo=(
                                    obj.demanda.codigo_disciplina if obj.demanda else ""
                                ),
                                disciplina_nome=(
                                    obj.demanda.nome_disciplina if obj.demanda else ""
                                ),
                                dia_semana_nome=(
                                    obj.dia_semana.nome if obj.dia_semana else ""
                                ),
                                horario_bloco=(
                                    obj.horario_bloco.codigo_bloco
                                    if obj.horario_bloco
                                    else ""
                                ),
                            )
                        )
                    except Exception as e:
                        logger.warning(
                            f"Error converting allocation {obj.id} to simplified: {e}"
                        )
                        continue

                return result
        except Exception as e:
            logger.error(f"Error getting simplified allocations: {e}", exc_info=True)
            return []

    def check_conflict(
        self,
        sala_id: int,
        dia_semana_id: int,
        codigo_bloco: str,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """
        Check if there's a conflict for a room, day, and time block.

        Args:
            sala_id: Room ID
            dia_semana_id: Day of week ID
            codigo_bloco: Time block code
            exclude_id: Allocation ID to exclude (for updates)

        Returns:
            bool: True if conflict exists, False otherwise
        """
        try:
            with DatabaseSession() as session:
                query = session.query(self.orm_model).filter(
                    AlocacaoSemestralORM.sala_id == sala_id,
                    AlocacaoSemestralORM.dia_semana_id == dia_semana_id,
                    AlocacaoSemestralORM.codigo_bloco == codigo_bloco,
                )

                if exclude_id:
                    query = query.filter(AlocacaoSemestralORM.id != exclude_id)

                return query.first() is not None
        except Exception as e:
            logger.error(f"Error checking allocation conflict: {e}", exc_info=True)
            return False


# ============================================================================
# SINGLETON FACTORY
# ============================================================================


_alocacao_repository: Optional[AlocacaoRepository] = None


def get_alocacao_repository() -> AlocacaoRepository:
    """
    Get or create the singleton AlocacaoRepository instance.

    This ensures a single repository instance is used throughout
    the application, reducing memory overhead and ensuring
    consistent behavior.

    Returns:
        AlocacaoRepository: Singleton instance

    Example:
        repo = get_alocacao_repository()
        allocations = repo.get_all_with_eager_load()
    """
    global _alocacao_repository
    if _alocacao_repository is None:
        _alocacao_repository = AlocacaoRepository()
    return _alocacao_repository
