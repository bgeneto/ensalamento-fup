"""
Repository for Sala (Classroom) operations.

Provides data access methods for room queries with domain-specific filters
and availability checks.
"""

from typing import Dict, List, Optional, Set

from sqlalchemy.orm import Session
from sqlalchemy import and_, distinct, func

from src.models.horario import HorarioBloco
from src.models.inventory import Sala, SalaDisponibilidadeBloco
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
            active=orm_obj.active,
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
            active=dto.active,
            descricao=dto.descricao,
        )

    def create(self, dto: SalaCreate) -> SalaRead:
        """Create room and initialize block availability entries."""
        orm_obj = self.dto_to_orm_create(dto)
        self.session.add(orm_obj)
        self.session.flush()  # generate ID for related availability rows

        self._ensure_room_block_availability_entries(orm_obj.id)

        self.session.commit()
        self.session.refresh(orm_obj)
        return self.orm_to_dto(orm_obj)

    # ========================================================================
    # ROOM AVAILABILITY HELPERS
    # ========================================================================

    def _ensure_room_block_availability_entries(self, sala_id: int) -> None:
        """Ensure the room has availability rows for all known atomic blocks."""
        all_block_codes = [
            row[0] for row in self.session.query(HorarioBloco.codigo_bloco).all()
        ]
        if not all_block_codes:
            return

        existing_block_codes = {
            row[0]
            for row in self.session.query(SalaDisponibilidadeBloco.codigo_bloco)
            .filter(SalaDisponibilidadeBloco.sala_id == sala_id)
            .all()
        }

        missing_block_codes = [
            code for code in all_block_codes if code not in existing_block_codes
        ]
        for code in missing_block_codes:
            self.session.add(
                SalaDisponibilidadeBloco(
                    sala_id=sala_id,
                    codigo_bloco=code,
                    enabled=True,
                )
            )

    def get_allowed_turnos(self, sala_id: int) -> Set[str]:
        """Get allowed shifts (M/T/N) for a room."""
        total_rows = (
            self.session.query(func.count(SalaDisponibilidadeBloco.id))
            .filter(SalaDisponibilidadeBloco.sala_id == sala_id)
            .scalar()
            or 0
        )

        rows = (
            self.session.query(distinct(HorarioBloco.turno))
            .join(
                SalaDisponibilidadeBloco,
                SalaDisponibilidadeBloco.codigo_bloco == HorarioBloco.codigo_bloco,
            )
            .filter(
                SalaDisponibilidadeBloco.sala_id == sala_id,
                SalaDisponibilidadeBloco.enabled.is_(True),
            )
            .all()
        )
        enabled_turnos = {row[0] for row in rows}

        # Legacy fallback: if room has no explicit rows yet, consider all shifts enabled.
        if total_rows == 0:
            return {"M", "T", "N"}

        return enabled_turnos

    def get_allowed_turnos_map(self, sala_ids: List[int]) -> Dict[int, Set[str]]:
        """Get allowed shifts map for a list of rooms."""
        if not sala_ids:
            return {}

        result: Dict[int, Set[str]] = {sala_id: set() for sala_id in sala_ids}

        total_rows = dict(
            self.session.query(
                SalaDisponibilidadeBloco.sala_id,
                func.count(SalaDisponibilidadeBloco.id),
            )
            .filter(SalaDisponibilidadeBloco.sala_id.in_(sala_ids))
            .group_by(SalaDisponibilidadeBloco.sala_id)
            .all()
        )

        rows = (
            self.session.query(
                SalaDisponibilidadeBloco.sala_id,
                HorarioBloco.turno,
            )
            .join(
                HorarioBloco,
                HorarioBloco.codigo_bloco == SalaDisponibilidadeBloco.codigo_bloco,
            )
            .filter(
                SalaDisponibilidadeBloco.sala_id.in_(sala_ids),
                SalaDisponibilidadeBloco.enabled.is_(True),
            )
            .distinct()
            .all()
        )

        for sala_id, turno in rows:
            result.setdefault(sala_id, set()).add(turno)

        # Legacy fallback for rooms without availability rows.
        for sala_id in sala_ids:
            if total_rows.get(sala_id, 0) == 0:
                result[sala_id] = {"M", "T", "N"}

        return result

    def get_allowed_blocks(self, sala_id: int) -> List[str]:
        """Get enabled atomic block codes for a room."""
        total_rows = (
            self.session.query(func.count(SalaDisponibilidadeBloco.id))
            .filter(SalaDisponibilidadeBloco.sala_id == sala_id)
            .scalar()
            or 0
        )

        if total_rows == 0:
            # Legacy fallback: no explicit rows means all blocks are enabled.
            rows = (
                self.session.query(HorarioBloco.codigo_bloco)
                .order_by(HorarioBloco.codigo_bloco)
                .all()
            )
            return [row[0] for row in rows]

        rows = (
            self.session.query(SalaDisponibilidadeBloco.codigo_bloco)
            .filter(
                SalaDisponibilidadeBloco.sala_id == sala_id,
                SalaDisponibilidadeBloco.enabled.is_(True),
            )
            .all()
        )
        return sorted([row[0] for row in rows])

    def set_room_allowed_turnos(self, sala_id: int, allowed_turnos: Set[str]) -> bool:
        """Enable/disable room availability by shift (M/T/N)."""
        valid_turnos = {"M", "T", "N"}
        allowed_turnos = {
            t.upper() for t in allowed_turnos if t and t.upper() in valid_turnos
        }

        try:
            room_exists = (
                self.session.query(Sala.id).filter(Sala.id == sala_id).first()
                is not None
            )
            if not room_exists:
                return False

            self._ensure_room_block_availability_entries(sala_id)
            self.session.flush()

            turno_blocks: Dict[str, List[str]] = {"M": [], "T": [], "N": []}
            for codigo_bloco, turno in self.session.query(
                HorarioBloco.codigo_bloco, HorarioBloco.turno
            ).all():
                if turno in turno_blocks:
                    turno_blocks[turno].append(codigo_bloco)

            for turno, block_codes in turno_blocks.items():
                if not block_codes:
                    continue
                self.session.query(SalaDisponibilidadeBloco).filter(
                    SalaDisponibilidadeBloco.sala_id == sala_id,
                    SalaDisponibilidadeBloco.codigo_bloco.in_(block_codes),
                ).update(
                    {"enabled": turno in allowed_turnos},
                    synchronize_session=False,
                )

            self.session.commit()
            return True
        except Exception:
            self.session.rollback()
            return False

    def is_room_enabled_for_blocks(self, sala_id: int, block_codes: List[str]) -> bool:
        """Check if room is enabled for all required atomic blocks."""
        required = sorted({code for code in block_codes if code})
        if not required:
            return True

        total_rows = (
            self.session.query(func.count(SalaDisponibilidadeBloco.id))
            .filter(SalaDisponibilidadeBloco.sala_id == sala_id)
            .scalar()
            or 0
        )
        if total_rows == 0:
            return True

        enabled_count = (
            self.session.query(
                func.count(distinct(SalaDisponibilidadeBloco.codigo_bloco))
            )
            .filter(
                SalaDisponibilidadeBloco.sala_id == sala_id,
                SalaDisponibilidadeBloco.enabled.is_(True),
                SalaDisponibilidadeBloco.codigo_bloco.in_(required),
            )
            .scalar()
            or 0
        )
        return enabled_count == len(required)

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

    def get_available_for_allocation(
        self, required_blocks: Optional[List[str]] = None
    ) -> List[SalaRead]:
        """Get active rooms available for allocation, optionally filtered by blocks."""
        query = self.session.query(Sala).filter(Sala.active.is_(True))

        block_codes = sorted({code for code in (required_blocks or []) if code})
        if block_codes:
            query = (
                query.join(
                    SalaDisponibilidadeBloco,
                    SalaDisponibilidadeBloco.sala_id == Sala.id,
                )
                .filter(
                    SalaDisponibilidadeBloco.enabled.is_(True),
                    SalaDisponibilidadeBloco.codigo_bloco.in_(block_codes),
                )
                .group_by(Sala.id)
                .having(
                    func.count(distinct(SalaDisponibilidadeBloco.codigo_bloco))
                    == len(block_codes)
                )
            )

        orm_objs = query.order_by(Sala.nome).all()
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_with_predio_info(
        self,
        active_only: bool = False,
        required_blocks: Optional[List[str]] = None,
    ) -> List[dict]:
        """Get all rooms with their building information included.

        Args:
            active_only: If True, return only active rooms.
            required_blocks: Optional list of required atomic blocks.

        Returns:
            List of dictionaries with 'sala' and 'predio' keys
        """
        from src.models.inventory import Predio
        from src.schemas.inventory import PredioRead

        # Query rooms with eager loading of predio
        query = self.session.query(Sala).join(Predio)
        if active_only:
            query = query.filter(Sala.active.is_(True))

        block_codes = sorted({code for code in (required_blocks or []) if code})
        if block_codes:
            query = (
                query.join(
                    SalaDisponibilidadeBloco,
                    SalaDisponibilidadeBloco.sala_id == Sala.id,
                )
                .filter(
                    SalaDisponibilidadeBloco.enabled.is_(True),
                    SalaDisponibilidadeBloco.codigo_bloco.in_(block_codes),
                )
                .group_by(Sala.id, Predio.id)
                .having(
                    func.count(distinct(SalaDisponibilidadeBloco.codigo_bloco))
                    == len(block_codes)
                )
            )

        orm_objs = query.order_by(Predio.nome, Sala.nome).all()

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
