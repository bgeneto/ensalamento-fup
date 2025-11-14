"""
Room Scoring Service - Advanced Scoring for Manual & Autonomous Allocation

Provides unified scoring algorithm for room-demand compatibility with:
- Historical frequency bonus (RF-006.6)
- Hard rules compliance
- Professor preferences
- Semester-isolated conflict detection

Used by both ManualAllocationService and AutonomousAllocationService for consistency.
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.config.scoring_config import (
    SCORING_WEIGHTS,
    SCORING_RULES,
    get_scoring_breakdown_template,
)

from src.repositories.alocacao import AlocacaoRepository
from src.repositories.disciplina import DisciplinaRepository

logger = logging.getLogger(__name__)
from src.repositories.regra import RegraRepository
from src.repositories.professor import ProfessorRepository
from src.repositories.sala import SalaRepository
from src.schemas.manual_allocation import CompatibilityScore
from src.models.inventory import Sala
from src.models.academic import Professor
from src.utils.sigaa_parser import SigaaScheduleParser
from src.utils.room_utils import get_room_occupancy


@dataclass
class ScoringBreakdown:
    """Detailed breakdown of how a room scored."""

    total_score: int = 0
    capacity_points: int = 0
    hard_rules_points: int = 0
    soft_preference_points: int = 0
    historical_frequency_points: int = 0

    # Details for each category
    capacity_satisfied: bool = False
    hard_rules_satisfied: List[str] = None  # Names of satisfied rules
    soft_preferences_satisfied: List[str] = None  # Names of satisfied preferences
    historical_allocations: int = (
        0  # How many times this discipline was allocated to this room
    )

    def __post_init__(self):
        if self.hard_rules_satisfied is None:
            self.hard_rules_satisfied = []
        if self.soft_preferences_satisfied is None:
            self.soft_preferences_satisfied = []


@dataclass
class RoomCandidate:
    """Internal structure for room-demand candidate scoring."""

    sala: Sala
    score: int = 0
    has_conflicts: bool = False
    rule_violations: List[str] = None
    scoring_breakdown: ScoringBreakdown = None

    def __post_init__(self):
        if self.rule_violations is None:
            self.rule_violations = []
        if self.scoring_breakdown is None:
            self.scoring_breakdown = ScoringBreakdown()


class RoomScoringService:
    """
    Unified service for advanced room-demand compatibility scoring.

    Provides consistent scoring across manual and autonomous allocation systems.
    """

    def __init__(self, session: Session):
        """Initialize with required repositories."""
        self.session = session
        self.alocacao_repo = AlocacaoRepository(session)
        self.demanda_repo = DisciplinaRepository(session)
        self.regra_repo = RegraRepository(session)
        self.prof_repo = ProfessorRepository(session)
        self.sala_repo = SalaRepository(session)
        self.parser = SigaaScheduleParser()

    def score_room_candidates_for_demand(
        self,
        demanda_id: int,
        semester_id: int,
        professor_override: Optional[Professor] = None,
    ) -> List[RoomCandidate]:
        """
        Score all room candidates for a demand using advanced algorithm.

        Includes:
        - Historical frequency bonus (RF-006.6)
        - Hard rules compliance
        - Professor preferences
        - Conflict detection within specified semester

        Args:
            demanda_id: Demand to score rooms for
            semester_id: Semester to check conflicts within
            professor_override: Optional professor object (if known)

        Returns:
            List of RoomCandidate objects, sorted by score descending
        """
        # Get demand details
        demanda = self.demanda_repo.get_by_id(demanda_id)
        if not demanda:
            return []

        # Lookup professor if not provided
        professor = professor_override
        if not professor:
            professor_map = self._lookup_professors_for_demands_from_objects([demanda])
            professor = professor_map.get(demanda_id)

        # Get professor preferences
        professor_prefs = self._get_professor_preferences_for_professor(professor)

        # Get hard rules for this demand
        hard_rules = self.regra_repo.find_rules_by_disciplina(demanda.codigo_disciplina)

        # Get all rooms
        all_rooms = self.sala_repo.get_all()

        candidates = []
        for room in all_rooms:
            candidate = RoomCandidate(sala=room)

            # Parse atomic blocks for this demand
            candidate.atomic_blocks = self.parser.split_to_atomic_tuples(
                demanda.horario_sigaa_bruto
            )

            # Calculate detailed scoring breakdown
            scoring_breakdown = self._calculate_detailed_scoring_breakdown(
                room, demanda, hard_rules, professor_prefs, semester_id
            )

            candidate.score = scoring_breakdown.total_score
            candidate.scoring_breakdown = scoring_breakdown

            # Extract rule violations for compatibility
            candidate.rule_violations = []
            if (
                not scoring_breakdown.capacity_satisfied
                or not scoring_breakdown.hard_rules_satisfied
            ):
                # Build violations from what was missing
                if not scoring_breakdown.capacity_satisfied:
                    candidate.rule_violations.append("Capacidade insuficiente")
                if not scoring_breakdown.hard_rules_satisfied:
                    candidate.rule_violations.append("Regras rígidas não atendidas")

            # Check for conflicts within the specified semester
            conflicts = self._check_allocation_conflicts_semester_isolated(
                candidate, semester_id
            )
            candidate.has_conflicts = len(conflicts) > 0

            candidates.append(candidate)

        # Sort by score (highest first), then by conflict status, then by room occupancy (highest first for optimization)
        candidates.sort(
            key=lambda c: (
                c.score,
                not c.has_conflicts,
                get_room_occupancy(self.alocacao_repo, c.sala.id, semester_id),
            ),
            reverse=True,
        )

        # Debug: Log when room occupancy optimization affects sorting
        if len(candidates) >= 2:
            top_score = candidates[0].score
            second_score = candidates[1].score
            if top_score == second_score:
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(
                    f"Room occupancy optimization applied for demand {candidates[0].sala.id}: "
                    f"Room {candidates[0].sala.nome} (occupancy: {get_room_occupancy(self.alocacao_repo, candidates[0].sala.id, semester_id)}) "
                    f"vs Room {candidates[1].sala.nome} (occupancy: {get_room_occupancy(self.alocacao_repo, candidates[1].sala.id, semester_id)})"
                )

        return candidates

    def _calculate_advanced_compatibility_score(
        self, room: Sala, demanda, hard_rules: List, professor_prefs: Dict
    ) -> CompatibilityScore:
        """
        Calculate advanced compatibility score (extracted from autonomous allocation).

        Includes capacity, hard rules, and professor preferences.
        """
        score = CompatibilityScore()
        violations = []

        # 1. Capacity check (basic requirement)
        if room.capacidade and room.capacidade >= demanda.vagas_disciplina:
            score.meets_capacity = True
            score.total_score += SCORING_WEIGHTS.CAPACITY_ADEQUATE

        # 2. Hard rules compliance (highest priority: 4 points each)
        hard_compliant = True
        for rule in hard_rules:
            if rule.prioridade == 0:  # Hard rule
                compliance = self._check_rule_compliance(room, demanda, rule)
                if not compliance:
                    hard_compliant = False
                    violations.append(f"Regra rígida violada: {rule.descricao}")
                else:
                    score.total_score += SCORING_WEIGHTS.HARD_RULE_COMPLIANCE

        score.hard_rules_compliant = hard_compliant

        # No need to check soft rules if hard rules fail
        if not hard_compliant:
            score.rule_violations = violations
            return score

        # 3. Professor preferences (2 points each category)
        soft_score = 0

        # Room preferences
        prof_room_prefs = professor_prefs.get("preferred_rooms", [])
        if room.id in prof_room_prefs:
            soft_score += SCORING_WEIGHTS.PREFERRED_ROOM
            score.soft_preferences_compliant = True

        # Characteristic preferences
        prof_char_prefs = professor_prefs.get("preferred_characteristics", [])
        room_chars = self._get_room_characteristics(room.id)
        for char_id in prof_char_prefs:
            if char_id in room_chars:
                soft_score += SCORING_WEIGHTS.PREFERRED_CHARACTERISTIC
                score.soft_preferences_compliant = True
                break

        score.total_score += soft_score
        score.rule_violations = violations

        return score

    def _calculate_detailed_scoring_breakdown(
        self,
        room: Sala,
        demanda,
        hard_rules: List,
        professor_prefs: Dict,
        semester_id: int,
    ) -> ScoringBreakdown:
        """
        Calculate detailed scoring breakdown with full transparency.

        This provides a complete explanation of how each room scored,
        suitable for display in the UI.
        """
        breakdown = ScoringBreakdown()

        # 1. Capacity check (+1 point)
        if room.capacidade and room.capacidade >= demanda.vagas_disciplina:
            breakdown.capacity_points = SCORING_WEIGHTS.CAPACITY_ADEQUATE
            breakdown.capacity_satisfied = True
        else:
            breakdown.capacity_points = 0
            breakdown.capacity_satisfied = False

        # 2. Hard rules compliance (+4 points each)
        hard_point_total = 0
        hard_rules_satisfied_list = []

        for rule in hard_rules:
            if rule.prioridade == 0:  # Hard rule
                compliance = self._check_rule_compliance(room, demanda, rule)

                # Debug logging
                logger.debug(
                    f"Hard rule check: {rule.descricao} | "
                    f"Room: {room.nome} (tipo_sala_id={room.tipo_sala_id}) | "
                    f"Compliant: {compliance}"
                )

                if compliance:
                    hard_point_total += SCORING_WEIGHTS.HARD_RULE_COMPLIANCE
                    # Add descriptive rule name for UI
                    hard_rules_satisfied_list.append(self._get_rule_description(rule))
                else:
                    # For hard rules, if any fails, no points and no soft preferences checked
                    hard_point_total = 0
                    hard_rules_satisfied_list = []
                    # Don't set to False here - let it be set after loop
                    break

        breakdown.hard_rules_points = hard_point_total
        # Store list of satisfied rule names (empty list means failed, non-empty means satisfied)
        breakdown.hard_rules_satisfied = hard_rules_satisfied_list

        # 3. Professor preferences (+2 points each category, but only if hard rules pass)
        soft_point_total = 0
        soft_preferences_satisfied_list = []

        if breakdown.hard_rules_satisfied:  # Only check soft prefs if hard rules pass
            # Room preferences
            prof_room_prefs = professor_prefs.get("preferred_rooms", [])
            if room.id in prof_room_prefs:
                soft_point_total += SCORING_WEIGHTS.PREFERRED_ROOM
                soft_preferences_satisfied_list.append("Sala preferida pelo professor")

            # Characteristic preferences
            prof_char_prefs = professor_prefs.get("preferred_characteristics", [])
            room_chars = self._get_room_characteristics(room.id)
            for char_id in prof_char_prefs:
                if char_id in room_chars:
                    char_name = self._get_characteristic_name(char_id)
                    soft_point_total += SCORING_WEIGHTS.PREFERRED_CHARACTERISTIC
                    soft_preferences_satisfied_list.append(
                        f"Característica preferida: {char_name}"
                    )
                    break  # Only one characteristic match needed

        breakdown.soft_preference_points = soft_point_total
        breakdown.soft_preferences_satisfied = soft_preferences_satisfied_list

        # 4. Historical frequency bonus (capped to prevent overwhelming other factors)
        historical_freq = self._calculate_historical_frequency_bonus(
            demanda.codigo_disciplina, room.id, semester_id
        )
        # Cap historical frequency points at maximum configured value
        # Note: historical_freq is already in POINTS (frequency × weight), not count
        breakdown.historical_frequency_points = min(
            historical_freq, SCORING_WEIGHTS.HISTORICAL_FREQUENCY_MAX_CAP
        )
        # Store actual frequency count for display (divide by weight to get count)
        breakdown.historical_allocations = (
            historical_freq // SCORING_WEIGHTS.HISTORICAL_FREQUENCY_PER_ALLOCATION
            if SCORING_WEIGHTS.HISTORICAL_FREQUENCY_PER_ALLOCATION > 0
            else 0
        )

        # Calculate total
        breakdown.total_score = (
            breakdown.capacity_points
            + breakdown.hard_rules_points
            + breakdown.soft_preference_points
            + breakdown.historical_frequency_points
        )

        return breakdown

    def _check_rule_compliance(self, room, demanda, rule) -> bool:
        """Check if room complies with a specific rule."""
        import json

        try:
            config = json.loads(rule.config_json)

            if rule.tipo_regra == "DISCIPLINA_TIPO_SALA":
                required_type_id = config.get("tipo_sala_id")
                result = room.tipo_sala_id == required_type_id
                logger.debug(
                    f"Rule check DISCIPLINA_TIPO_SALA: {rule.descricao} | "
                    f"Room {room.nome} tipo_sala_id={room.tipo_sala_id} | "
                    f"Required tipo_sala_id={required_type_id} | "
                    f"Match: {result}"
                )
                return result

            elif rule.tipo_regra == "DISCIPLINA_SALA":
                required_room_id = config.get("sala_id")
                result = room.id == required_room_id
                logger.debug(
                    f"Rule check DISCIPLINA_SALA: {rule.descricao} | "
                    f"Room id={room.id} | Required room_id={required_room_id} | "
                    f"Match: {result}"
                )
                return result

            elif rule.tipo_regra == "DISCIPLINA_CARACTERISTICA":
                required_char = config.get("caracteristica_nome")
                room_chars = self._get_room_characteristics(room.id)
                char_names = [self._get_characteristic_name(cid) for cid in room_chars]
                result = required_char in char_names
                logger.debug(
                    f"Rule check DISCIPLINA_CARACTERISTICA: {rule.descricao} | "
                    f"Room {room.nome} chars={char_names} | "
                    f"Required char={required_char} | "
                    f"Match: {result}"
                )
                return result

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(
                f"Rule compliance check failed for {rule.descricao}: {e} | "
                f"config_json={rule.config_json}"
            )
            return False

        logger.warning(
            f"Unknown rule type: {rule.tipo_regra} for rule {rule.descricao}"
        )
        return False

    def _check_allocation_conflicts_semester_isolated(
        self, candidate: RoomCandidate, semester_id: int
    ) -> List[Dict]:
        """
        Check for conflicts within a specific semester only (not cross-semester).
        """
        conflicts = []

        for bloco_codigo, dia_sigaa in candidate.atomic_blocks:
            # Check for conflicts IN THE SPECIFIED SEMESTER only
            has_conflict = self.alocacao_repo.check_conflict(
                candidate.sala.id, dia_sigaa, bloco_codigo, semestre_id=semester_id
            )

            if has_conflict:
                conflicts.append(
                    {
                        "dia_sigaa": dia_sigaa,
                        "codigo_bloco": bloco_codigo,
                        "sala_id": candidate.sala.id,
                    }
                )

        return conflicts

    def _get_professor_preferences_for_professor(
        self, professor: Optional[Professor]
    ) -> Dict:
        """Get professor preferences dict from Professor object."""
        prefs = {"preferred_rooms": [], "preferred_characteristics": []}

        if not professor:
            return prefs

        # Get room preferences
        stmt = text(
            "SELECT sala_id FROM professor_prefere_sala WHERE professor_id = :prof_id"
        )
        room_prefs = [
            row[0]
            for row in self.session.execute(stmt, {"prof_id": professor.id}).fetchall()
        ]
        prefs["preferred_rooms"].extend(room_prefs)

        # Get characteristic preferences
        stmt = text(
            "SELECT caracteristica_id FROM professor_prefere_caracteristica WHERE professor_id = :prof_id"
        )
        char_prefs = [
            row[0]
            for row in self.session.execute(stmt, {"prof_id": professor.id}).fetchall()
        ]
        prefs["preferred_characteristics"].extend(char_prefs)

        return prefs

    def _calculate_historical_frequency_bonus(
        self, disciplina_codigo: str, sala_id: int, exclude_semester_id: int
    ) -> int:
        """
        Calculate historical frequency bonus (RF-006.6).

        Returns bonus points based on how many times this discipline has been
        allocated to this room in previous semesters.

        The result is capped at HISTORICAL_FREQUENCY_MAX_CAP points (not allocations).

        Returns:
            Historical frequency points (already capped at MAX_CAP value)
        """
        # Use existing repository method to get frequency count
        frequency = self.alocacao_repo.get_discipline_room_frequency(
            disciplina_codigo, sala_id, exclude_semester_id
        )

        # Calculate points: frequency (count) × weight (points per allocation)
        historical_points = (
            frequency * SCORING_WEIGHTS.HISTORICAL_FREQUENCY_PER_ALLOCATION
        )

        # Cap at maximum POINTS (not maximum allocations)
        return min(historical_points, SCORING_WEIGHTS.HISTORICAL_FREQUENCY_MAX_CAP)

    def _lookup_professors_for_demands_from_objects(
        self, demands
    ) -> Dict[int, Optional[Professor]]:
        """Lookup professors for demand objects."""
        professor_map = {}

        for demanda in demands:
            demanda_id = demanda.id
            prof_text = demanda.professores_disciplina.strip()

            if prof_text:
                # Support multiple professors (take first match)
                prof_names = [name.strip() for name in prof_text.split(",")]
                professor = None

                for prof_name in prof_names:
                    professor = self.prof_repo.get_by_nome_completo(prof_name)
                    if professor:
                        break

                professor_map[demanda_id] = professor

        return professor_map

    def _get_room_characteristics(self, sala_id: int):
        """Get characteristic IDs for a room."""
        stmt = text(
            "SELECT caracteristica_id FROM sala_caracteristicas WHERE sala_id = :sala_id"
        )
        rows = self.session.execute(stmt, {"sala_id": sala_id}).fetchall()
        return {row[0] for row in rows}

    def _get_characteristic_name(self, caracteristica_id: int) -> str:
        """Get characteristic name by ID."""
        stmt = text("SELECT nome FROM caracteristicas WHERE id = :cid")
        row = self.session.execute(stmt, {"cid": caracteristica_id}).fetchone()
        return row[0] if row else ""

    def _get_rule_description(self, rule) -> str:
        """Get human-readable description of a rule for UI display."""
        import json

        try:
            config = json.loads(rule.config_json)

            if rule.tipo_regra == "DISCIPLINA_TIPO_SALA":
                tipo_sala_name = self._get_room_type_name_by_id(
                    config.get("tipo_sala_id")
                )
                return f"Tipo de sala: {tipo_sala_name}"

            elif rule.tipo_regra == "DISCIPLINA_SALA":
                sala_id = config.get("sala_id")
                sala_name = self._get_room_name_by_id(sala_id)
                return f"Sala específica: {sala_name}"

            elif rule.tipo_regra == "DISCIPLINA_CARACTERISTICA":
                char_name = config.get("caracteristica_nome")
                return f"Característica: {char_name}"

            else:
                return f"Regra: {rule.descricao}"

        except (json.JSONDecodeError, KeyError):
            return f"Regra: {rule.descricao}"

    def _get_room_type_name_by_id(self, tipo_sala_id: int) -> str:
        """Get room type name by ID."""
        if not tipo_sala_id:
            return "N/A"
        stmt = text("SELECT nome FROM tipos_sala WHERE id = :tid")
        row = self.session.execute(stmt, {"tid": tipo_sala_id}).fetchone()
        return row[0] if row else "N/A"

    def _get_room_name_by_id(self, sala_id: int) -> str:
        """Get room name by ID."""
        if not sala_id:
            return "N/A"
        stmt = text("SELECT nome FROM salas WHERE id = :sid")
        row = self.session.execute(stmt, {"sid": sala_id}).fetchone()
        return row[0] if row else "N/A"
