"""
Sala (Room) Repository Implementation

This is a concrete example of how to implement the repository pattern.
It shows:
1. How to convert ORM models to DTOs
2. How to handle relationships safely
3. How to manage database sessions properly
4. How to return clean data to services
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import joinedload

from database import DatabaseSession, Sala as SalaORM
from src.repositories.base import BaseRepository
from src.schemas.sala import (
    SalaDTO,
    SalaSimplifiedDTO,
    SalaDetailDTO,
    SalaCreateDTO,
    SalaUpdateDTO,
    PredioDTO,
    TipoSalaDTO,
    CaracteristicaDTO,
)

logger = logging.getLogger(__name__)


class SalaRepository(BaseRepository[SalaORM, SalaDTO]):
    """Repository for room (Sala) operations"""

    @property
    def orm_model(self):
        return SalaORM

    def orm_to_dto(self, orm_obj: SalaORM) -> SalaDTO:
        """
        Convert ORM Sala model to DTO.

        This is called ONLY inside the repository while the session is still open.
        This ensures all relationships are accessible.

        IMPORTANT: This method is only called within the `with DatabaseSession()`
        context, so all lazy-loaded relationships are available.
        """
        if not orm_obj:
            return None

        # Convert nested relationships to DTOs
        predio_dto = None
        if orm_obj.predio:
            predio_dto = PredioDTO(
                id=orm_obj.predio.id,
                nome=orm_obj.predio.nome,
                campus_id=orm_obj.predio.campus_id,
                campus=None,  # Avoid infinite nesting
            )

        tipo_sala_dto = None
        if orm_obj.tipo_sala:
            tipo_sala_dto = TipoSalaDTO(
                id=orm_obj.tipo_sala.id,
                nome=orm_obj.tipo_sala.nome,
                descricao=orm_obj.tipo_sala.descricao,
            )

        caracteristicas_dto = []
        if orm_obj.caracteristicas:
            caracteristicas_dto = [
                CaracteristicaDTO(id=c.id, nome=c.nome) for c in orm_obj.caracteristicas
            ]

        # Create and return DTO - a plain data object with no DB connection
        return SalaDTO(
            id=orm_obj.id,
            nome=orm_obj.nome,
            codigo=orm_obj.codigo if hasattr(orm_obj, "codigo") else None,
            capacidade=orm_obj.capacidade,
            andar=orm_obj.andar,
            tipo_assento=orm_obj.tipo_assento,
            predio=predio_dto,
            tipo_sala=tipo_sala_dto,
            caracteristicas=caracteristicas_dto,
        )

    def dto_to_orm_create(self, dto: SalaCreateDTO) -> dict:
        """Convert create DTO to ORM constructor kwargs"""
        return {
            "nome": dto.nome,
            "codigo": dto.codigo,
            "predio_id": dto.predio_id,
            "tipo_sala_id": dto.tipo_sala_id,
            "capacidade": dto.capacidade,
            "andar": dto.andar,
            "tipo_assento": dto.tipo_assento,
        }

    # ===== CUSTOM QUERIES =====

    def get_all_with_eager_load(self) -> List[SalaDTO]:
        """
        Get all rooms with eager-loaded relationships.

        This uses joinedload to fetch related data in a single query,
        preventing N+1 query problems.
        """
        try:
            with DatabaseSession() as session:
                # Eager load all relationships to avoid lazy loading
                salas = (
                    session.query(SalaORM)
                    .options(
                        joinedload(SalaORM.predio),
                        joinedload(SalaORM.tipo_sala),
                        joinedload(SalaORM.caracteristicas),
                    )
                    .order_by(SalaORM.nome)
                    .all()
                )

                # Convert to DTOs while still in session
                return [self.orm_to_dto(sala) for sala in salas]

        except Exception as e:
            logger.exception(f"Error getting all rooms with eager load: {e}")
            return []

    def get_by_campus(self, campus_id: int) -> List[SalaDTO]:
        """Get all rooms in a specific campus"""
        try:
            with DatabaseSession() as session:
                from database import Predio

                salas = (
                    session.query(SalaORM)
                    .join(Predio)
                    .filter(Predio.campus_id == campus_id)
                    .options(
                        joinedload(SalaORM.predio),
                        joinedload(SalaORM.tipo_sala),
                    )
                    .all()
                )

                return [self.orm_to_dto(sala) for sala in salas]

        except Exception as e:
            logger.exception(f"Error getting rooms by campus {campus_id}: {e}")
            return []

    def get_by_predio(self, predio_id: int) -> List[SalaDTO]:
        """Get all rooms in a specific building"""
        try:
            with DatabaseSession() as session:
                salas = (
                    session.query(SalaORM)
                    .filter(SalaORM.predio_id == predio_id)
                    .options(
                        joinedload(SalaORM.tipo_sala),
                        joinedload(SalaORM.caracteristicas),
                    )
                    .order_by(SalaORM.nome)
                    .all()
                )

                return [self.orm_to_dto(sala) for sala in salas]

        except Exception as e:
            logger.exception(f"Error getting rooms by building {predio_id}: {e}")
            return []

    def get_by_tipo_sala(self, tipo_sala_id: int) -> List[SalaDTO]:
        """Get all rooms of a specific type"""
        try:
            with DatabaseSession() as session:
                salas = (
                    session.query(SalaORM)
                    .filter(SalaORM.tipo_sala_id == tipo_sala_id)
                    .options(
                        joinedload(SalaORM.predio),
                        joinedload(SalaORM.caracteristicas),
                    )
                    .order_by(SalaORM.nome)
                    .all()
                )

                return [self.orm_to_dto(sala) for sala in salas]

        except Exception as e:
            logger.exception(f"Error getting rooms by type {tipo_sala_id}: {e}")
            return []

    def get_by_capacidade_range(self, min_cap: int, max_cap: int) -> List[SalaDTO]:
        """Get all rooms within a capacity range"""
        try:
            with DatabaseSession() as session:
                salas = (
                    session.query(SalaORM)
                    .filter(SalaORM.capacidade.between(min_cap, max_cap))
                    .options(
                        joinedload(SalaORM.predio),
                        joinedload(SalaORM.tipo_sala),
                    )
                    .order_by(SalaORM.capacidade)
                    .all()
                )

                return [self.orm_to_dto(sala) for sala in salas]

        except Exception as e:
            logger.exception(
                f"Error getting rooms by capacity range {min_cap}-{max_cap}: {e}"
            )
            return []

    def search_by_name(self, name: str) -> List[SalaDTO]:
        """Search rooms by name (contains search)"""
        try:
            with DatabaseSession() as session:
                salas = (
                    session.query(SalaORM)
                    .filter(SalaORM.nome.ilike(f"%{name}%"))
                    .options(
                        joinedload(SalaORM.predio),
                        joinedload(SalaORM.tipo_sala),
                    )
                    .order_by(SalaORM.nome)
                    .all()
                )

                return [self.orm_to_dto(sala) for sala in salas]

        except Exception as e:
            logger.exception(f"Error searching rooms by name '{name}': {e}")
            return []

    def get_simplified(self) -> List[SalaSimplifiedDTO]:
        """Get simplified room list (for dropdowns, etc)"""
        try:
            with DatabaseSession() as session:
                salas = (
                    session.query(SalaORM)
                    .options(
                        joinedload(SalaORM.predio),
                        joinedload(SalaORM.tipo_sala),
                    )
                    .all()
                )

                return [
                    SalaSimplifiedDTO(
                        id=sala.id,
                        nome=sala.nome,
                        capacidade=sala.capacidade,
                        predio_nome=sala.predio.nome if sala.predio else "Unknown",
                        tipo_sala_nome=(
                            sala.tipo_sala.nome if sala.tipo_sala else "Unknown"
                        ),
                    )
                    for sala in salas
                ]

        except Exception as e:
            logger.exception(f"Error getting simplified rooms: {e}")
            return []

    def get_available_count(self) -> int:
        """Get count of available rooms"""
        try:
            with DatabaseSession() as session:
                return session.query(SalaORM).count()
        except Exception as e:
            logger.exception(f"Error counting available rooms: {e}")
            return 0

    # ===== WRITE OPERATIONS (with proper session handling) =====

    def create_with_characteristics(
        self,
        dto: SalaCreateDTO,
        caracteristica_ids: List[int] = None,
    ) -> Optional[SalaDTO]:
        """Create a room with characteristics"""
        try:
            with DatabaseSession() as session:
                # Create ORM object
                orm_data = self.dto_to_orm_create(dto)
                sala = SalaORM(**orm_data)

                # Add characteristics if provided
                if caracteristica_ids:
                    from database import Caracteristica

                    for car_id in caracteristica_ids:
                        caracteristica = (
                            session.query(Caracteristica)
                            .filter(Caracteristica.id == car_id)
                            .first()
                        )
                        if caracteristica:
                            sala.caracteristicas.append(caracteristica)

                session.add(sala)
                session.flush()

                return self.orm_to_dto(sala)

        except Exception as e:
            logger.exception(f"Error creating room with characteristics: {e}")
            return None


# ===== SINGLETON INSTANCE =====
# For convenience, provide a module-level instance

_sala_repository = None


def get_sala_repository() -> SalaRepository:
    """Get or create the singleton SalaRepository instance"""
    global _sala_repository
    if _sala_repository is None:
        _sala_repository = SalaRepository()
    return _sala_repository
