"""
Repository for Sala (Classroom) operations.

Provides data access methods for room queries with domain-specific filters
and availability checks.
"""

from typing import List, Optional
from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models.inventory import Sala
from src.schemas.inventory import SalaRead, SalaCreate
from src.repositories.base import BaseRepository


class SalaRepository(BaseRepository[Sala, SalaRead]):
    """Repository for Sala (classroom) CRUD and queries."""

    def __init__(self, session: Session):
        """Initialize SalaRepository.

        Args:
            session: SQLAlchemy session
        """
        super().__init__(session, Sala)

    def orm_to_dto(self, orm_obj: Sala) -> SalaRead:
        """Convert ORM Sala model to SalaRead DTO.

        Args:
            orm_obj: Sala ORM model instance

        Returns:
            SalaRead DTO
        """
        return SalaRead(
            id=orm_obj.id,
            nome=orm_obj.nome,
            predio_id=orm_obj.predio_id,
            tipo_sala_id=orm_obj.tipo_sala_id,
            capacidade=orm_obj.capacidade,
            andar=orm_obj.andar,
            descricao=orm_obj.descricao,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def dto_to_orm_create(self, dto: SalaCreate) -> Sala:
        """Convert SalaCreate DTO to ORM Sala model for creation.

        Args:
            dto: SalaCreate DTO

        Returns:
            Sala ORM model instance (not persisted)
        """
        return Sala(
            nome=dto.nome,
            predio_id=dto.predio_id,
            tipo_sala_id=dto.tipo_sala_id,
            capacidade=dto.capacidade,
            andar=dto.andar,
            descricao=dto.descricao,
        )

    # ========================================================================
    # DOMAIN-SPECIFIC QUERY METHODS
    # ========================================================================

    def get_by_andar(self, andar: str) -> List[SalaRead]:
        """Get all rooms on a specific floor.

        Args:
            andar: Floor number as string ("0"=ground, "1"=1st, etc.)

        Returns:
            List of SalaRead DTOs sorted by room name
        """
        orm_objs = (
            self.session.query(Sala)
            .filter(Sala.andar == andar)
            .order_by(Sala.nome)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_capacidade_minima(self, min_capacity: int) -> List[SalaRead]:
        """Get all rooms with minimum capacity.

        Args:
            min_capacity: Minimum room capacity (number of students)

        Returns:
            List of SalaRead DTOs sorted by capacity (highest first)
        """
        orm_objs = (
            self.session.query(Sala)
            .filter(Sala.capacidade >= min_capacity)
            .order_by(Sala.capacidade.desc(), Sala.nome)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_capacidade_exata(self, capacity: int) -> List[SalaRead]:
        """Get all rooms with exact capacity.

        Args:
            capacity: Exact room capacity

        Returns:
            List of SalaRead DTOs sorted by room name
        """
        orm_objs = (
            self.session.query(Sala)
            .filter(Sala.capacidade == capacity)
            .order_by(Sala.nome)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_predio(self, predio_id: int) -> List[SalaRead]:
        """Get all rooms in a specific building.

        Args:
            predio_id: Building ID

        Returns:
            List of SalaRead DTOs sorted by room name
        """
        orm_objs = (
            self.session.query(Sala)
            .filter(Sala.predio_id == predio_id)
            .order_by(Sala.nome)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_tipo_sala(self, tipo_sala_id: int) -> List[SalaRead]:
        """Get all rooms of a specific type.

        Args:
            tipo_sala_id: Room type ID (e.g., classroom, lab, auditorium)

        Returns:
            List of SalaRead DTOs sorted by room name
        """
        orm_objs = (
            self.session.query(Sala)
            .filter(Sala.tipo_sala_id == tipo_sala_id)
            .order_by(Sala.nome)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_descricao(self, descricao: str) -> List[SalaRead]:
        """Get all rooms with specific descricao.

        Args:
            descricao: descricao (e.g., 'Sala de Aulo')

        Returns:
            List of SalaRead DTOs sorted by room name
        """
        orm_objs = (
            self.session.query(Sala)
            .filter(Sala.descricao == descricao)
            .order_by(Sala.nome)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_andar_and_capacidade(
        self, andar: str, min_capacity: int
    ) -> List[SalaRead]:
        """Get rooms on a specific floor with minimum capacity.

        Args:
            andar: Floor number as string
            min_capacity: Minimum capacity

        Returns:
            List of SalaRead DTOs sorted by capacity then room name
        """
        orm_objs = (
            self.session.query(Sala)
            .filter(and_(Sala.andar == andar, Sala.capacidade >= min_capacity))
            .order_by(Sala.capacidade.desc(), Sala.nome)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_predio_and_andar(self, predio_id: int, andar: str) -> List[SalaRead]:
        """Get rooms in a specific building on a specific floor.

        Args:
            predio_id: Building ID
            andar: Floor number as string

        Returns:
            List of SalaRead DTOs sorted by room name
        """
        orm_objs = (
            self.session.query(Sala)
            .filter(and_(Sala.predio_id == predio_id, Sala.andar == andar))
            .order_by(Sala.nome)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def search_by_name(self, name_pattern: str) -> List[SalaRead]:
        """Search rooms by name (case-insensitive, partial match).

        Args:
            name_pattern: Room name pattern (e.g., 'A1-' to find all A1 rooms)

        Returns:
            List of SalaRead DTOs sorted by room name
        """
        orm_objs = (
            self.session.query(Sala)
            .filter(Sala.nome.ilike(f"%{name_pattern}%"))
            .order_by(Sala.nome)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_statistics(self) -> dict:
        """Get room statistics.

        Returns:
            Dictionary with statistics:
            - total_rooms: Total number of rooms
            - rooms_by_floor: Dict with count per floor
            - rooms_by_capacity: Dict with count per capacity
            - avg_capacity: Average room capacity
            - max_capacity: Largest room capacity
            - min_capacity: Smallest room capacity
        """
        all_rooms = self.get_all()
        if not all_rooms:
            return {
                "total_rooms": 0,
                "rooms_by_floor": {},
                "rooms_by_capacity": {},
                "avg_capacity": 0,
                "max_capacity": 0,
                "min_capacity": 0,
            }

        # Count by floor
        rooms_by_floor = {}
        for room in all_rooms:
            floor = room.andar
            rooms_by_floor[floor] = rooms_by_floor.get(floor, 0) + 1

        # Count by capacity
        rooms_by_capacity = {}
        capacities = []
        for room in all_rooms:
            cap = room.capacidade
            rooms_by_capacity[cap] = rooms_by_capacity.get(cap, 0) + 1
            capacities.append(cap)

        return {
            "total_rooms": len(all_rooms),
            "rooms_by_floor": rooms_by_floor,
            "rooms_by_capacity": rooms_by_capacity,
            "avg_capacity": sum(capacities) / len(capacities) if capacities else 0,
            "max_capacity": max(capacities) if capacities else 0,
            "min_capacity": min(capacities) if capacities else 0,
        }

    def get_available_for_allocation(self) -> List[SalaRead]:
        """Get all rooms available for allocation (active rooms).

        Returns:
            List of all SalaRead DTOs
        """
        return self.get_all()

    def get_with_predio_info(self) -> List[dict]:
        """Get all rooms with their building information included.

        Returns:
            List of dictionaries with 'sala' and 'predio' keys
        """
        from src.models.inventory import Predio
        from src.schemas.inventory import PredioRead

        # Query rooms with eager loading of predio
        orm_objs = (
            self.session.query(Sala).join(Predio).order_by(Predio.nome, Sala.nome).all()
        )

        result = []
        for sala in orm_objs:
            predio_dto = PredioRead(
                id=sala.predio.id,
                nome=sala.predio.nome,
                descricao=sala.predio.descricao,
                campus_id=sala.predio.campus_id,
                created_at=sala.predio.created_at,
                updated_at=sala.predio.updated_at,
            )

            result.append({"sala": self.orm_to_dto(sala), "predio": predio_dto})

        return result

    # ========================================================================
    # CHARACTERISTICS MANAGEMENT METHODS
    # ========================================================================

    def get_sala_with_caracteristicas(self, sala_id: int) -> Optional[dict]:
        """Get room with its characteristics by ID.

        Returns:
            Dictionary with 'sala' and 'caracteristicas' keys, or None if not found
        """
        from src.models.inventory import Caracteristica
        from src.schemas.inventory import CaracteristicaRead

        orm_obj = self.session.query(Sala).filter(Sala.id == sala_id).first()

        if not orm_obj:
            return None

        # Get associated characteristics
        caracteristicas_orm = (
            self.session.query(Caracteristica)
            .join(Sala.caracteristicas)
            .filter(Sala.id == sala_id)
            .all()
        )

        # Convert to DTOs
        caracteristicas_dto = [
            CaracteristicaRead(
                id=c.id, nome=c.nome, created_at=c.created_at, updated_at=c.updated_at
            )
            for c in caracteristicas_orm
        ]

        return {
            "sala": self.orm_to_dto(orm_obj),
            "caracteristicas": caracteristicas_dto,
        }

    def add_caracteristica_to_sala(
        self, sala_id: int, caracteristica_ids: List[int]
    ) -> bool:
        """Add characteristics to a room (append to existing).

        Args:
            sala_id: Room ID
            caracteristica_ids: List of characteristic IDs to add

        Returns:
            True if successful, False otherwise
        """
        try:
            orm_obj = self.session.query(Sala).filter(Sala.id == sala_id).first()
            if not orm_obj:
                return False

            # Get current characteristics
            current_ids = [c.id for c in orm_obj.caracteristicas]

            # Add new IDs (avoid duplicates)
            new_ids = [cid for cid in caracteristica_ids if cid not in current_ids]

            if new_ids:
                # Get characteristic objects
                from src.models.inventory import Caracteristica

                new_caracteristicas = (
                    self.session.query(Caracteristica)
                    .filter(Caracteristica.id.in_(new_ids))
                    .all()
                )

                # Add to room
                orm_obj.caracteristicas.extend(new_caracteristicas)

            self.session.commit()
            return True
        except Exception:
            self.session.rollback()
            return False

    def set_caracteristicas_for_sala(
        self, sala_id: int, caracteristica_ids: List[int]
    ) -> bool:
        """Replace all characteristics for a room with new ones.

        Args:
            sala_id: Room ID
            caracteristica_ids: List of characteristic IDs (replaces existing)

        Returns:
            True if successful, False otherwise
        """
        try:
            orm_obj = self.session.query(Sala).filter(Sala.id == sala_id).first()
            if not orm_obj:
                return False

            # Get characteristic objects
            from src.models.inventory import Caracteristica

            new_caracteristicas = (
                self.session.query(Caracteristica)
                .filter(Caracteristica.id.in_(caracteristica_ids))
                .all()
            )

            # Replace all characteristics
            orm_obj.caracteristicas = new_caracteristicas

            self.session.commit()
            return True
        except Exception:
            self.session.rollback()
            return False

    def remove_caracteristica_from_sala(
        self, sala_id: int, caracteristica_ids: List[int]
    ) -> bool:
        """Remove specific characteristics from a room.

        Args:
            sala_id: Room ID
            caracteristica_ids: List of characteristic IDs to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            orm_obj = self.session.query(Sala).filter(Sala.id == sala_id).first()
            if not orm_obj:
                return False

            # Remove specific characteristics
            orm_obj.caracteristicas = [
                c for c in orm_obj.caracteristicas if c.id not in caracteristica_ids
            ]

            self.session.commit()
            return True
        except Exception:
            self.session.rollback()
            return False
