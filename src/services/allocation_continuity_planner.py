"""Planning utilities for continuity-aware partial allocation.

This module prepares demand-level continuity metadata without changing the
current allocation behavior by itself. It is designed to be consumed by the
optimized autonomous allocation service in later phases.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from src.models.academic import Demanda
from src.models.allocation import AlocacaoSemestral
from src.repositories.alocacao import AlocacaoRepository
from src.repositories.optimized_allocation_repo import OptimizedAllocationRepository
from src.repositories.professor import ProfessorRepository
from src.repositories.regra import RegraRepository
from src.repositories.sala import SalaRepository
from src.services.room_scoring_service import RoomScoringService
from src.utils.sigaa_parser import SigaaScheduleParser


@dataclass
class ProfessorAnchor:
    """Preferred spatial anchor for a professor within a semester context."""

    professor_id: int
    semester_id: int
    room_id: Optional[int] = None
    building_id: Optional[int] = None
    room_type_id: Optional[int] = None
    source: str = "inferred"
    allocation_count: int = 0


@dataclass
class DemandContinuityProfile:
    """Precomputed continuity metadata for a demand."""

    demanda_id: int
    codigo_disciplina: str
    is_hybrid: bool
    total_pending_blocks: int
    distinct_days: int
    compatible_full_room_ids: List[int] = field(default_factory=list)
    pending_blocks_by_day: Dict[Tuple[int, str], List[Tuple[str, int]]] = field(
        default_factory=dict
    )
    existing_room_ids: List[int] = field(default_factory=list)
    preferred_existing_room_id: Optional[int] = None
    professor_anchor_room_id: Optional[int] = None
    professor_anchor_building_id: Optional[int] = None
    professor_anchor_room_type_id: Optional[int] = None
    has_specific_room_constraint: bool = False


class AllocationContinuityPlanner:
    """Build continuity metadata for later continuity-aware allocation phases."""

    def __init__(self, session: Session, hybrid_service: Optional[Any] = None):
        self.session = session
        self.alocacao_repo = AlocacaoRepository(session)
        self.optimized_alocacao_repo = OptimizedAllocationRepository(session)
        self.prof_repo = ProfessorRepository(session)
        self.regra_repo = RegraRepository(session)
        self.sala_repo = SalaRepository(session)
        self.parser = SigaaScheduleParser()
        self.scoring_service = RoomScoringService(session)
        self.hybrid_service = hybrid_service
        self._professor_lookup_cache: Dict[str, Optional[Any]] = {}
        self._professor_anchor_cache: Dict[
            Tuple[int, int], Optional[ProfessorAnchor]
        ] = {}
        self._professor_room_usage_cache: Dict[
            Tuple[str, Optional[int], Optional[int]], Counter
        ] = {}
        self._existing_room_ids_cache: Dict[int, Tuple[List[int], Optional[int]]] = {}
        self._room_enabled_blocks_cache: Dict[Tuple[int, Tuple[str, ...]], bool] = {}
        self._specific_room_constraint_cache: Dict[str, bool] = {}
        self._room_cache: Dict[int, Any] = {}

    def clear_runtime_caches(self) -> None:
        """Clear caches that depend on current allocation state."""
        self._professor_anchor_cache.clear()
        self._professor_room_usage_cache.clear()
        self._existing_room_ids_cache.clear()
        self._room_enabled_blocks_cache.clear()

    def build_demand_profiles(
        self, demands: List[Any], semester_id: int
    ) -> Dict[int, DemandContinuityProfile]:
        """Build continuity profiles for a batch of pending demands."""
        self.clear_runtime_caches()
        profiles: Dict[int, DemandContinuityProfile] = {}

        for demanda in demands:
            demanda_id = demanda.id
            pending_blocks = self._get_pending_atomic_blocks_for_demand(
                demanda_id, demanda.horario_sigaa_bruto
            )
            pending_blocks_by_day = self._group_atomic_blocks_by_day(pending_blocks)
            compatible_full_rooms = self.get_full_compatible_rooms(
                demanda, pending_blocks, semester_id
            )
            existing_room_ids, preferred_existing_room_id = self._get_existing_room_ids(
                demanda_id
            )
            professor = self._resolve_primary_professor(demanda)
            professor_anchor = self.resolve_professor_anchor(professor, semester_id)
            has_specific_room_constraint = self._specific_room_constraint_cache.get(
                demanda.codigo_disciplina
            )
            if has_specific_room_constraint is None:
                hard_rules = self.regra_repo.find_rules_by_disciplina(
                    demanda.codigo_disciplina
                )
                has_specific_room_constraint = any(
                    rule.prioridade == 0 and rule.tipo_regra == "DISCIPLINA_SALA"
                    for rule in hard_rules
                )
                self._specific_room_constraint_cache[demanda.codigo_disciplina] = (
                    has_specific_room_constraint
                )

            profiles[demanda_id] = DemandContinuityProfile(
                demanda_id=demanda_id,
                codigo_disciplina=demanda.codigo_disciplina,
                is_hybrid=self._is_hybrid(demanda),
                total_pending_blocks=len(pending_blocks),
                distinct_days=len(pending_blocks_by_day),
                compatible_full_room_ids=[room.id for room in compatible_full_rooms],
                pending_blocks_by_day=pending_blocks_by_day,
                existing_room_ids=existing_room_ids,
                preferred_existing_room_id=preferred_existing_room_id,
                professor_anchor_room_id=(
                    professor_anchor.room_id if professor_anchor else None
                ),
                professor_anchor_building_id=(
                    professor_anchor.building_id if professor_anchor else None
                ),
                professor_anchor_room_type_id=(
                    professor_anchor.room_type_id if professor_anchor else None
                ),
                has_specific_room_constraint=has_specific_room_constraint,
            )

        return profiles

    def resolve_professor_anchor(
        self, professor: Optional[Any], semester_id: int
    ) -> Optional[ProfessorAnchor]:
        """Resolve the best current spatial anchor for a professor."""
        if professor is None or getattr(professor, "id", None) is None:
            return None

        cache_key = (professor.id, semester_id)
        if cache_key in self._professor_anchor_cache:
            return self._professor_anchor_cache[cache_key]

        professor_name = getattr(professor, "nome_completo", "") or ""
        if not professor_name.strip():
            return None

        current_counts = self._count_professor_room_usage(
            professor_name, semester_id=semester_id
        )
        if current_counts:
            room_id, allocation_count = self._select_anchor_room(current_counts)
            anchor = self._build_anchor(
                professor_id=professor.id,
                semester_id=semester_id,
                room_id=room_id,
                allocation_count=allocation_count,
                source="current_semester",
            )
            self._professor_anchor_cache[cache_key] = anchor
            return anchor

        historical_counts = self._count_professor_room_usage(
            professor_name, semester_id=None, exclude_semester_id=semester_id
        )
        if historical_counts:
            room_id, allocation_count = self._select_anchor_room(historical_counts)
            anchor = self._build_anchor(
                professor_id=professor.id,
                semester_id=semester_id,
                room_id=room_id,
                allocation_count=allocation_count,
                source="historical",
            )
            self._professor_anchor_cache[cache_key] = anchor
            return anchor

        self._professor_anchor_cache[cache_key] = None
        return None

    def get_full_compatible_rooms(
        self,
        demanda: Any,
        pending_blocks: List[Tuple[str, int]],
        semester_id: int,
    ) -> List[Any]:
        """Return rooms that can satisfy all pending blocks for the demand."""
        if not pending_blocks:
            return []

        candidates = self.scoring_service.score_room_candidates_for_full_continuity(
            demanda.id,
            pending_blocks,
            semester_id,
        )
        return [
            candidate.sala for candidate in candidates if not candidate.has_conflicts
        ]

    def prioritize_demands_for_continuity(
        self, profiles: Dict[int, DemandContinuityProfile]
    ) -> List[int]:
        """Return demand ids ordered by continuity restrictiveness."""

        def sort_key(profile: DemandContinuityProfile) -> Tuple[Any, ...]:
            viable_room_count = len(profile.compatible_full_room_ids)
            has_viable_solution = viable_room_count > 0

            return (
                not has_viable_solution,
                viable_room_count if has_viable_solution else float("inf"),
                profile.is_hybrid,
                -profile.distinct_days,
                -profile.total_pending_blocks,
                not profile.has_specific_room_constraint,
                profile.professor_anchor_room_id is None,
                profile.codigo_disciplina,
                profile.demanda_id,
            )

        return [
            profile.demanda_id for profile in sorted(profiles.values(), key=sort_key)
        ]

    def count_future_day_coverage(
        self,
        demanda: Any,
        room_id: int,
        pending_by_day: Dict[Tuple[int, str], List[Tuple[str, int]]],
        semester_id: int,
    ) -> int:
        """Count how many pending day-groups a room can still cover fully."""
        covered_days = 0
        room_time_slots = [
            (room_id, day_id, block_code)
            for blocks in pending_by_day.values()
            for block_code, day_id in blocks
        ]
        conflict_map = self.optimized_alocacao_repo.check_conflicts_batch(
            room_time_slots,
            semester_id,
        )

        for blocks in pending_by_day.values():
            block_codes = [block_code for block_code, _ in blocks]
            if not self._is_room_enabled_for_blocks_cached(room_id, block_codes):
                continue

            has_conflict = any(
                conflict_map.get((room_id, day_id, block_code), False)
                for block_code, day_id in blocks
            )
            if not has_conflict:
                covered_days += 1

        return covered_days

    def _get_pending_atomic_blocks_for_demand(
        self, demanda_id: int, horario_sigaa: str
    ) -> List[Tuple[str, int]]:
        atomic_blocks = self.parser.split_to_atomic_tuples(horario_sigaa)
        if not atomic_blocks:
            return []

        allocated_blocks = {
            (alloc.codigo_bloco, alloc.dia_semana_id)
            for alloc in self.alocacao_repo.get_by_demanda(demanda_id)
        }
        return [
            (block_code, day_id)
            for block_code, day_id in atomic_blocks
            if (block_code, day_id) not in allocated_blocks
        ]

    def _group_atomic_blocks_by_day(
        self, atomic_blocks: List[Tuple[str, int]]
    ) -> Dict[Tuple[int, str], List[Tuple[str, int]]]:
        grouped: Dict[Tuple[int, str], List[Tuple[str, int]]] = {}
        for block_code, day_id in atomic_blocks:
            grouped.setdefault((day_id, block_code[0]), []).append((block_code, day_id))
        return grouped

    def _get_existing_room_ids(
        self, demanda_id: int
    ) -> Tuple[List[int], Optional[int]]:
        cached = self._existing_room_ids_cache.get(demanda_id)
        if cached is not None:
            return cached

        allocations = self.alocacao_repo.get_by_demanda(demanda_id)
        room_counts = Counter(alloc.sala_id for alloc in allocations)
        ordered_room_ids = [room_id for room_id, _ in room_counts.most_common()]
        preferred_existing_room_id = ordered_room_ids[0] if ordered_room_ids else None
        result = (ordered_room_ids, preferred_existing_room_id)
        self._existing_room_ids_cache[demanda_id] = result
        return result

    def _resolve_primary_professor(self, demanda: Any) -> Optional[Any]:
        professor_text = (getattr(demanda, "professores_disciplina", "") or "").strip()
        if not professor_text:
            return None

        primary_name = self._extract_primary_professor_name(professor_text)
        if primary_name not in self._professor_lookup_cache:
            self._professor_lookup_cache[primary_name] = (
                self.prof_repo.get_by_nome_completo(primary_name)
            )
        return self._professor_lookup_cache[primary_name]

    def _extract_primary_professor_name(self, raw_text: str) -> str:
        normalized = raw_text.replace(";", ",").replace("\n", ",")
        parts = [part.strip() for part in normalized.split(",") if part.strip()]
        return parts[0] if parts else raw_text.strip()

    def _count_professor_room_usage(
        self,
        professor_name: str,
        semester_id: Optional[int],
        exclude_semester_id: Optional[int] = None,
    ) -> Counter:
        cache_key = (professor_name, semester_id, exclude_semester_id)
        cached = self._professor_room_usage_cache.get(cache_key)
        if cached is not None:
            return cached.copy()

        query = self.session.query(
            AlocacaoSemestral.sala_id,
            Demanda.professores_disciplina,
        ).join(Demanda, AlocacaoSemestral.demanda_id == Demanda.id)
        if semester_id is not None:
            query = query.filter(AlocacaoSemestral.semestre_id == semester_id)
        if exclude_semester_id is not None:
            query = query.filter(AlocacaoSemestral.semestre_id != exclude_semester_id)

        counts: Counter = Counter()
        for sala_id, professor_text in query.all():
            if self._demand_mentions_professor(professor_text, professor_name):
                counts[sala_id] += 1

        self._professor_room_usage_cache[cache_key] = counts.copy()
        return counts

    def _demand_mentions_professor(
        self, professor_text: Optional[str], professor_name: str
    ) -> bool:
        if not professor_text or not professor_name:
            return False

        normalized = professor_text.replace(";", ",").replace("\n", ",")
        parts = {part.strip() for part in normalized.split(",") if part.strip()}
        return professor_name in parts

    def _select_anchor_room(self, counts: Counter) -> Tuple[int, int]:
        room_id, allocation_count = sorted(
            counts.items(), key=lambda item: (-item[1], item[0])
        )[0]
        return room_id, allocation_count

    def _build_anchor(
        self,
        professor_id: int,
        semester_id: int,
        room_id: int,
        allocation_count: int,
        source: str,
    ) -> Optional[ProfessorAnchor]:
        room = self._room_cache.get(room_id)
        if room is None:
            room = self.sala_repo.get_by_id(room_id)
            if room is not None:
                self._room_cache[room_id] = room
        if room is None:
            return None

        return ProfessorAnchor(
            professor_id=professor_id,
            semester_id=semester_id,
            room_id=room_id,
            building_id=room.predio_id,
            room_type_id=room.tipo_sala_id,
            source=source,
            allocation_count=allocation_count,
        )

    def _is_hybrid(self, demanda: Any) -> bool:
        if self.hybrid_service is None:
            return False
        if not getattr(self.hybrid_service, "_is_initialized", False):
            return False
        if hasattr(self.hybrid_service, "is_hybrid_demand"):
            return bool(self.hybrid_service.is_hybrid_demand(demanda))
        return bool(
            self.hybrid_service.is_hybrid(getattr(demanda, "codigo_disciplina", ""))
        )

    def _is_room_enabled_for_blocks_cached(
        self, sala_id: int, block_codes: List[str]
    ) -> bool:
        required = tuple(sorted({code for code in block_codes if code}))
        cache_key = (sala_id, required)
        cached = self._room_enabled_blocks_cache.get(cache_key)
        if cached is not None:
            return cached

        result = self.sala_repo.is_room_enabled_for_blocks(sala_id, list(required))
        self._room_enabled_blocks_cache[cache_key] = result
        return result
