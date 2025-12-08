"""
Repository for AlocacaoSemestral (Semester Allocation) operations.

Provides data access methods for course-room allocation queries with
conflict detection and availability checking.
"""

from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from src.models.allocation import AlocacaoSemestral
from src.repositories.base import BaseRepository
from src.schemas.academic import DemandaRead
from src.schemas.allocation import AlocacaoSemestralCreate, AlocacaoSemestralRead


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
        demanda_dto = None
        if hasattr(orm_obj, "demanda") and orm_obj.demanda:
            demanda_dto = DemandaRead.from_orm(orm_obj.demanda)

        return AlocacaoSemestralRead(
            id=orm_obj.id,
            semestre_id=orm_obj.semestre_id,
            demanda_id=orm_obj.demanda_id,
            sala_id=orm_obj.sala_id,
            dia_semana_id=orm_obj.dia_semana_id,
            codigo_bloco=orm_obj.codigo_bloco,
            demanda=demanda_dto,
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

    def get_by_sala_and_semestre(
        self, sala_id: int, semestre_id: int
    ) -> List[AlocacaoSemestralRead]:
        """Get all allocations in a specific room for a specific semester.

        Args:
            sala_id: Room ID
            semestre_id: Semester ID

        Returns:
            List of AlocacaoSemestralRead DTOs sorted by day and time
        """
        orm_objs = (
            self.session.query(AlocacaoSemestral)
            .filter(
                and_(
                    AlocacaoSemestral.sala_id == sala_id,
                    AlocacaoSemestral.semestre_id == semestre_id,
                )
            )
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
        semestre_id: Optional[int] = None,
    ) -> bool:
        """Check if there's a conflict (double-booking) at a specific time slot.

        Args:
            sala_id: Room ID
            dia_semana_id: Weekday ID
            codigo_bloco: Time block code
            exclude_alocacao_id: Allocation ID to exclude (for updates)
            semestre_id: Semester ID to check conflicts within (optional - if not provided, checks across all semesters)

        Returns:
            True if conflict exists, False otherwise
        """
        conditions = [
            AlocacaoSemestral.sala_id == sala_id,
            AlocacaoSemestral.dia_semana_id == dia_semana_id,
            AlocacaoSemestral.codigo_bloco == codigo_bloco,
        ]

        if semestre_id is not None:
            conditions.append(AlocacaoSemestral.semestre_id == semestre_id)

        query = self.session.query(AlocacaoSemestral).filter(and_(*conditions))

        if exclude_alocacao_id:
            query = query.filter(AlocacaoSemestral.id != exclude_alocacao_id)

        return query.first() is not None

    def get_conflicts_in_room(
        self, sala_id: int, semestre_id: Optional[int] = None
    ) -> List[Tuple[int, str]]:
        """Get all conflicting time slots in a room (multiple courses at same time).

        Args:
            sala_id: Room ID
            semestre_id: Optional semester ID to filter conflicts within a specific semester.
                        If None, checks ALL semesters (for historical analysis).

        Returns:
            List of (dia_semana_id, codigo_bloco) tuples with conflicts
        """
        # Get all allocations in room (optionally filtered by semester)
        if semestre_id is not None:
            # Get allocations only for the specified semester
            allocations = self.get_by_semestre_filtered(sala_id, semestre_id)
        else:
            # Get all allocations (backward compatibility)
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
            .options(joinedload(AlocacaoSemestral.demanda))
            .filter(AlocacaoSemestral.semestre_id == semestre_id)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_semestre_filtered(
        self, sala_id: int, semestre_id: int
    ) -> List[AlocacaoSemestralRead]:
        """Get all allocations in a specific room for a specific semester.

        Args:
            sala_id: Room ID
            semestre_id: Semester ID

        Returns:
            List of AlocacaoSemestralRead DTOs sorted by day and time
        """
        orm_objs = (
            self.session.query(AlocacaoSemestral)
            .filter(
                and_(
                    AlocacaoSemestral.sala_id == sala_id,
                    AlocacaoSemestral.semestre_id == semestre_id,
                )
            )
            .order_by(AlocacaoSemestral.dia_semana_id, AlocacaoSemestral.codigo_bloco)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_allocation_summary(self, semester_id: Optional[int] = None) -> dict:
        """Get allocation statistics and summary for a specific semester.

        Args:
            semester_id: Optional semester ID to filter statistics. If None, gets stats for ALL semesters.

        Returns:
            Dictionary with statistics:
            - total_allocations: Total number of allocations
            - total_demands_allocated: Total unique demands with allocations
            - total_rooms_allocated: Total unique rooms allocated
            - total_conflicts: Total number of conflicting time slots
            - rooms_with_conflicts: List of room IDs with conflicts
        """
        all_allocs = (
            self.get_by_semestre(semester_id)
            if semester_id is not None
            else self.get_all()
        )

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

    def get_discipline_room_frequency(
        self,
        disciplina_codigo: str,
        sala_id: int,
        exclude_semester_id: Optional[int] = None,
    ) -> int:
        """Get historical frequency count of discipline-room allocations.

        RF-006.6: Count how many times a discipline code has been allocated
        to a specific room across all semesters except the current one.

        Args:
            disciplina_codigo: Discipline code to count
            sala_id: Room ID to count allocations for
            exclude_semester_id: Semester ID to exclude from count (current semester)

        Returns:
            int: Number of historical allocations of this discipline to this room
        """
        from src.models.academic import Demanda

        # Build query to join alocacao_semestral with disciplina
        query = (
            self.session.query(AlocacaoSemestral)
            .join(Demanda, AlocacaoSemestral.demanda_id == Demanda.id)
            .filter(
                and_(
                    Demanda.codigo_disciplina == disciplina_codigo,
                    AlocacaoSemestral.sala_id == sala_id,
                )
            )
        )

        # Exclude current semester if provided
        if exclude_semester_id is not None:
            query = query.filter(AlocacaoSemestral.semestre_id != exclude_semester_id)

        # Count the results
        count = query.count()
        return count

    def get_discipline_room_day_frequency(
        self,
        disciplina_codigo: str,
        sala_id: int,
        dia_semana_id: int,
        exclude_semester_id: Optional[int] = None,
    ) -> int:
        """Get historical frequency count of discipline-room-day allocations.

        Enhanced RF-006.6: Count how many times a discipline code has been allocated
        to a specific room ON A SPECIFIC DAY across all semesters except the current one.

        This enables per-day historical scoring for hybrid disciplines that may
        use different rooms on different days (e.g., lab on Monday, lecture hall on Wednesday).

        Args:
            disciplina_codigo: Discipline code to count
            sala_id: Room ID to count allocations for
            dia_semana_id: Day of week ID (2=MON, 3=TUE, ..., 7=SAT)
            exclude_semester_id: Semester ID to exclude from count (current semester)

        Returns:
            int: Number of historical allocations of this discipline to this room on this day
        """
        from src.models.academic import Demanda

        # Build query to join alocacao_semestral with disciplina
        query = (
            self.session.query(AlocacaoSemestral)
            .join(Demanda, AlocacaoSemestral.demanda_id == Demanda.id)
            .filter(
                and_(
                    Demanda.codigo_disciplina == disciplina_codigo,
                    AlocacaoSemestral.sala_id == sala_id,
                    AlocacaoSemestral.dia_semana_id == dia_semana_id,
                )
            )
        )

        # Exclude current semester if provided
        if exclude_semester_id is not None:
            query = query.filter(AlocacaoSemestral.semestre_id != exclude_semester_id)

        # Count the results
        count = query.count()
        return count

    def get_discipline_room_day_frequencies_bulk(
        self,
        disciplina_codigo: str,
        sala_ids: List[int],
        dia_semana_ids: List[int],
        exclude_semester_id: Optional[int] = None,
    ) -> Dict[Tuple[int, int], int]:
        """Bulk fetch historical frequencies for multiple room-day combinations.

        Performance optimization: Fetches all (room, day) frequencies in a single query
        instead of N queries for N combinations.

        Args:
            disciplina_codigo: Discipline code to count
            sala_ids: List of room IDs to check
            dia_semana_ids: List of day IDs to check (2=MON, 3=TUE, ..., 7=SAT)
            exclude_semester_id: Semester ID to exclude from count (current semester)

        Returns:
            Dict[(sala_id, dia_semana_id), count]: Historical frequency for each combination
        """
        from sqlalchemy import func

        from src.models.academic import Demanda

        # Build query with GROUP BY
        query = (
            self.session.query(
                AlocacaoSemestral.sala_id,
                AlocacaoSemestral.dia_semana_id,
                func.count(AlocacaoSemestral.id).label("count"),
            )
            .join(Demanda, AlocacaoSemestral.demanda_id == Demanda.id)
            .filter(
                and_(
                    Demanda.codigo_disciplina == disciplina_codigo,
                    AlocacaoSemestral.sala_id.in_(sala_ids),
                    AlocacaoSemestral.dia_semana_id.in_(dia_semana_ids),
                )
            )
            .group_by(AlocacaoSemestral.sala_id, AlocacaoSemestral.dia_semana_id)
        )

        # Exclude current semester if provided
        if exclude_semester_id is not None:
            query = query.filter(AlocacaoSemestral.semestre_id != exclude_semester_id)

        # Execute and build result dict
        results = {}
        for row in query.all():
            results[(row.sala_id, row.dia_semana_id)] = row.count

        return results

    # ========================================================================
    # HYBRID DISCIPLINE DETECTION (Phase 0)
    # ========================================================================

    def detect_hybrid_disciplines(
        self, semester_id: int, regular_classroom_type_id: int = 2
    ) -> List[str]:
        """
        Detect hybrid disciplines from historical allocations.

        A hybrid discipline is one that:
        1. Has allocations in 2+ different rooms in the same semester
        2. At least one of those rooms is NOT a regular classroom (tipo_sala_id != 2)

        This indicates the discipline uses both classrooms and specialized rooms
        (labs, auditoriums, etc.) on different days.

        Args:
            semester_id: Semester to analyze for detection
            regular_classroom_type_id: tipo_sala_id for regular classrooms (default: 2)

        Returns:
            List of discipline codes (codigo_disciplina) classified as hybrid
        """
        from sqlalchemy import case, func

        from src.models.academic import Demanda
        from src.models.inventory import Sala

        # Query to find disciplines with:
        # 1. 2+ different rooms in the semester
        # 2. At least one room that is NOT a regular classroom
        query = (
            self.session.query(Demanda.codigo_disciplina)
            .join(AlocacaoSemestral, AlocacaoSemestral.demanda_id == Demanda.id)
            .join(Sala, AlocacaoSemestral.sala_id == Sala.id)
            .filter(AlocacaoSemestral.semestre_id == semester_id)
            .group_by(Demanda.codigo_disciplina)
            .having(
                and_(
                    # At least 2 different rooms
                    func.count(func.distinct(AlocacaoSemestral.sala_id)) >= 2,
                    # At least one non-classroom room
                    func.max(
                        case(
                            (Sala.tipo_sala_id != regular_classroom_type_id, 1),
                            else_=0,
                        )
                    )
                    == 1,
                )
            )
        )

        results = [row[0] for row in query.all()]
        return results

    def get_hybrid_discipline_day_room_types(
        self,
        codigo_disciplina: str,
        semester_id: int,
        regular_classroom_type_id: int = 2,
    ) -> Dict[int, Dict[str, any]]:
        """
        Get room type usage per day for a hybrid discipline.

        For each day of the week, returns which room types were used
        and whether it's primarily a lab day or classroom day.

        Args:
            codigo_disciplina: Discipline code
            semester_id: Semester to analyze
            regular_classroom_type_id: tipo_sala_id for regular classrooms (default: 2)

        Returns:
            Dict[day_id, {
                'room_types': [tipo_sala_ids used],
                'room_ids': [sala_ids used],
                'is_lab_day': bool,  # True if any non-classroom room used
                'lab_room_ids': [sala_ids that are labs/specialized]
            }]
        """
        from src.models.academic import Demanda
        from src.models.inventory import Sala

        # Get all allocations for this discipline in the semester
        query = (
            self.session.query(
                AlocacaoSemestral.dia_semana_id,
                Sala.id.label("sala_id"),
                Sala.tipo_sala_id,
            )
            .join(Demanda, AlocacaoSemestral.demanda_id == Demanda.id)
            .join(Sala, AlocacaoSemestral.sala_id == Sala.id)
            .filter(
                and_(
                    Demanda.codigo_disciplina == codigo_disciplina,
                    AlocacaoSemestral.semestre_id == semester_id,
                )
            )
            .distinct()
        )

        # Organize by day
        day_info: Dict[int, Dict[str, any]] = {}
        for row in query.all():
            day_id = row.dia_semana_id
            sala_id = row.sala_id
            tipo_sala_id = row.tipo_sala_id

            if day_id not in day_info:
                day_info[day_id] = {
                    "room_types": set(),
                    "room_ids": set(),
                    "lab_room_ids": set(),
                }

            day_info[day_id]["room_types"].add(tipo_sala_id)
            day_info[day_id]["room_ids"].add(sala_id)

            # Track non-classroom rooms as "lab" rooms
            if tipo_sala_id != regular_classroom_type_id:
                day_info[day_id]["lab_room_ids"].add(sala_id)

        # Convert sets to lists and add is_lab_day flag
        result = {}
        for day_id, info in day_info.items():
            result[day_id] = {
                "room_types": list(info["room_types"]),
                "room_ids": list(info["room_ids"]),
                "lab_room_ids": list(info["lab_room_ids"]),
                "is_lab_day": len(info["lab_room_ids"]) > 0,
            }

        return result

    def get_most_recent_semester_id(self) -> Optional[int]:
        """
        Get the most recent semester ID (highest ID value).

        Returns:
            Most recent semester_id, or None if no semesters exist
        """
        from sqlalchemy import func

        from src.models.academic import Semestre

        result = self.session.query(func.max(Semestre.id)).scalar()
        return result

    def get_most_recent_semester_with_allocations(
        self, exclude_semester_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Get the most recent semester ID that has actual allocations.

        This is important for hybrid detection because we need a semester
        with existing allocation data, not an empty semester we're about to allocate.

        Args:
            exclude_semester_id: Optional semester to exclude (e.g., current semester)

        Returns:
            Most recent semester_id with allocations, or None if none exist
        """
        from sqlalchemy import func

        # Find semesters that have allocations
        query = (
            self.session.query(AlocacaoSemestral.semestre_id)
            .group_by(AlocacaoSemestral.semestre_id)
            .having(func.count(AlocacaoSemestral.id) > 0)
        )

        if exclude_semester_id:
            query = query.filter(AlocacaoSemestral.semestre_id != exclude_semester_id)

        # Get all semesters with allocations, then return the max
        semester_ids = [row[0] for row in query.all()]

        if not semester_ids:
            return None

        return max(semester_ids)

