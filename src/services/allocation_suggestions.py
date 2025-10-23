"""Core service for room suggestion algorithm in manual allocation."""

import json
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.schemas.manual_allocation import (
    RoomSuggestion,
    AllocationSuggestions,
    ConflictDetail,
)
from src.repositories.sala import SalaRepository
from src.repositories.regra import RegraRepository
from src.repositories.professor import ProfessorRepository
from src.repositories.alocacao import AlocacaoRepository
from src.repositories.reserva import ReservaRepository
from src.repositories.disciplina import DisciplinaRepository
from src.models.inventory import Sala
from src.models.academic import Professor
from src.models.allocation import Regra
from src.utils.sigaa_parser import SigaaScheduleParser


@dataclass
class CompatibilityScore:
    """Internal scoring structure for room compatibility."""

    total_score: int = 0
    hard_rules_compliant: bool = False
    soft_preferences_compliant: bool = False
    meets_capacity: bool = False
    rule_violations: List[str] = None

    def __post_init__(self):
        if self.rule_violations is None:
            self.rule_violations = []


class AllocationSuggestionsService:
    """Service for calculating room suggestions for manual allocation."""

    def __init__(self, session: Session):
        """Initialize service with repositories."""
        self.session = session
        self.sala_repo = SalaRepository(session)
        self.regra_repo = RegraRepository(session)
        self.prof_repo = ProfessorRepository(session)
        self.alocacao_repo = AlocacaoRepository(session)
        self.reserva_repo = ReservaRepository(session)
        self.demanda_repo = DisciplinaRepository(session)
        self.parser = SigaaScheduleParser()

    def calculate_suggestions(
        self, demanda_id: int, semester_id: int
    ) -> AllocationSuggestions:
        """
        Calculate room suggestions for a demand.
        Returns categorized suggestions: top, others, and conflicting.
        """
        # Get demand details
        demanda = self.demanda_repo.get_by_id(demanda_id)
        if not demanda:
            return AllocationSuggestions(demanda_id=demanda_id)

        # Parse atomic blocks from schedule
        atomic_blocks = self._parse_atomic_blocks(demanda.horario_sigaa_bruto)
        if not atomic_blocks:
            return AllocationSuggestions(demanda_id=demanda_id)

        # Get professor preferences if available
        professor_prefs = self._get_professor_preferences(
            demanda.professores_disciplina
        )

        # Get hard rules for this demand
        hard_rules = self.regra_repo.find_rules_by_disciplina(demanda.codigo_disciplina)

        # Get all available rooms
        all_rooms = self.sala_repo.get_all()

        top_suggestions = []
        other_available = []
        conflicting_rooms = []

        for room in all_rooms:
            suggestion = self._evaluate_room(
                room, demanda, atomic_blocks, hard_rules, professor_prefs, semester_id
            )

            if suggestion.has_conflicts:
                conflicting_rooms.append(suggestion)
            else:
                # Prioritize top suggestions (highest scores first)
                if (
                    suggestion.compatibility_score >= 5
                ):  # Good hard rule + soft rule match
                    top_suggestions.append(suggestion)
                else:
                    other_available.append(suggestion)

        # Sort suggestions by score (highest first)
        top_suggestions.sort(key=lambda s: s.compatibility_score, reverse=True)
        other_available.sort(key=lambda s: s.compatibility_score, reverse=True)

        return AllocationSuggestions(
            demanda_id=demanda_id,
            top_suggestions=top_suggestions[:3],  # Limit to top 3
            other_available=other_available,
            conflicting_rooms=conflicting_rooms[
                :10
            ],  # Limit conflicting to avoid overload
        )

    def _evaluate_room(
        self,
        room: Sala,
        demanda,
        atomic_blocks: List[Tuple[str, int]],
        hard_rules: List[Regra],
        professor_prefs: Dict,
        semester_id: int,
    ) -> RoomSuggestion:
        """Evaluate a room's suitability for the demand."""
        score = self._calculate_compatibility_score(
            room, demanda, hard_rules, professor_prefs
        )

        # Check for conflicts
        conflicts = self._check_for_conflicts(room.id, atomic_blocks)

        suggestion = RoomSuggestion(
            sala_id=room.id,
            nome_sala=f"{self._get_predio_name(room.predio_id)}/{room.nome}",
            tipo_sala_nome=self._get_tipo_sala_name(room.tipo_sala_id),
            capacidade=room.capacidade or 0,
            andar=room.andar,
            predio_nome=self._get_predio_name(room.predio_id),
            compatibility_score=score.total_score,
            hard_rules_compliant=score.hard_rules_compliant,
            soft_preferences_compliant=score.soft_preferences_compliant,
            meets_capacity=score.meets_capacity,
            has_conflicts=len(conflicts) > 0,
            conflict_details=[
                f"{c.dia_sigaa}-{c.codigo_bloco}: {c.entidade_conflitante}"
                for c in conflicts
            ],
            rule_violations=score.rule_violations,
            motivation_reason=self._generate_motivation(score, conflicts),
        )

        return suggestion

    def _calculate_compatibility_score(
        self,
        room: Sala,
        demanda,
        hard_rules: List[Regra],
        professor_prefs: Dict,
    ) -> CompatibilityScore:
        """Calculate compatibility score for room-demand pair."""
        score = CompatibilityScore()
        violations = []

        # 1. Capacity check (basic requirement)
        if room.capacidade and room.capacidade >= demanda.vagas_disciplina:
            score.meets_capacity = True
            score.total_score += 1

        # 2. Hard rules compliance (highest priority: 4 points each)
        hard_compliant = True
        for rule in hard_rules:
            if rule.prioridade == 0:  # Hard rule
                compliance = self._check_rule_compliance(room, demanda, rule)
                if not compliance:
                    hard_compliant = False
                    violations.append(f"Regra dura violada: {rule.descricao}")
                else:
                    score.total_score += 4

        score.hard_rules_compliant = hard_compliant

        # No need to check soft rules if hard rules fail
        if not hard_compliant:
            score.rule_violations = violations
            return score

        # 3. Soft preferences (lower priority: 2 points each)
        soft_score = 0

        # Professor room preferences
        prof_room_prefs = professor_prefs.get("preferred_rooms", [])
        if room.id in prof_room_prefs:
            soft_score += 2
            score.soft_preferences_compliant = True

        # Professor characteristic preferences
        prof_char_prefs = professor_prefs.get("preferred_characteristics", [])
        room_chars = self._get_room_characteristics(room.id)
        for char_id in prof_char_prefs:
            if char_id in room_chars:
                soft_score += 2
                score.soft_preferences_compliant = True
                break

        score.total_score += soft_score
        score.rule_violations = violations

        return score

    def _check_rule_compliance(self, room: Sala, demanda, rule: Regra) -> bool:
        """Check if room complies with a specific rule."""
        try:
            config = json.loads(rule.config_json)

            if rule.tipo_regra == "DISCIPLINA_TIPO_SALA":
                required_type = config.get("tipo_sala_nome")
                return room.tipo_sala and room.tipo_sala.nome == required_type

            elif rule.tipo_regra == "DISCIPLINA_SALA":
                required_room_id = config.get("sala_id")
                return room.id == required_room_id

            elif rule.tipo_regra == "DISCIPLINA_CARACTERISTICA":
                required_char = config.get("caracteristica_nome")
                room_chars = self._get_room_characteristics(room.id)
                char_names = [self._get_characteristic_name(cid) for cid in room_chars]
                return required_char in char_names

        except (json.JSONDecodeError, KeyError):
            return False

        return True

    def _check_for_conflicts(
        self, sala_id: int, atomic_blocks: List[Tuple[str, int]]
    ) -> List[ConflictDetail]:
        """Check for conflicts in semester allocations and ad-hoc reservations."""
        conflicts = []

        for bloco_codigo, dia_sigaa in atomic_blocks:
            # Check semester allocations
            has_semester_conflict = self.alocacao_repo.check_conflict(
                sala_id, dia_sigaa, bloco_codigo
            )
            if has_semester_conflict:
                # Find the conflicting allocation
                allocs = self.alocacao_repo.get_by_horario(dia_sigaa, bloco_codigo)
                for alloc in allocs:
                    if alloc.sala_id == sala_id:
                        conflicts.append(
                            ConflictDetail(
                                tipo_conflito="semester_allocation",
                                dia_sigaa=dia_sigaa,
                                codigo_bloco=bloco_codigo,
                                entidade_conflitante=alloc.demanda.nome_disciplina,
                                identificador_conflitante=alloc.demanda.codigo_disciplina,
                            )
                        )
                        break

            # Check ad-hoc reservations (this is a simplified check - in practice
            # we'd need to convert reservation dates to weekdays, but that's complex)
            # For now, we'll skip this as it requires date-to-weekday conversion
            # and is not critical for the first version

        return conflicts

    def _get_professor_preferences(self, professores_text: str) -> Dict:
        """Extract professor preferences from the demand's professor text."""
        prefs = {"preferred_rooms": [], "preferred_characteristics": []}

        if not professores_text:
            return prefs

        # Split by comma and find professor matches
        prof_names = [name.strip() for name in professores_text.split(",")]

        for prof_name in prof_names:
            prof = self.prof_repo.get_by_nome_completo(prof_name)
            if prof:
                # Get room preferences
                stmt = text(
                    """
                SELECT sala_id FROM professor_prefere_sala WHERE professor_id = :prof_id
                """
                )
                room_prefs = [
                    row[0]
                    for row in self.session.execute(
                        stmt, {"prof_id": prof.id}
                    ).fetchall()
                ]
                prefs["preferred_rooms"].extend(room_prefs)

                # Get characteristic preferences
                stmt = text(
                    """
                SELECT caracteristica_id FROM professor_prefere_caracteristica
                WHERE professor_id = :prof_id
                """
                )
                char_prefs = [
                    row[0]
                    for row in self.session.execute(
                        stmt, {"prof_id": prof.id}
                    ).fetchall()
                ]
                prefs["preferred_characteristics"].extend(char_prefs)

        return prefs

    def _parse_atomic_blocks(self, horario_bruto: str) -> List[Tuple[str, int]]:
        """Parse horario_sigaa_bruto into atomic (bloco, dia) pairs."""
        return self.parser.split_to_atomic_tuples(horario_bruto)

    def _get_room_characteristics(self, sala_id: int) -> Set[int]:
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

    def _get_predio_name(self, predio_id: int) -> str:
        """Get building name by ID."""
        stmt = text("SELECT nome FROM predios WHERE id = :pid")
        row = self.session.execute(stmt, {"pid": predio_id}).fetchone()
        return row[0] if row else "N/A"

    def _get_tipo_sala_name(self, tipo_sala_id: int) -> str:
        """Get room type name by ID."""
        stmt = text("SELECT nome FROM tipos_sala WHERE id = :tid")
        row = self.session.execute(stmt, {"tid": tipo_sala_id}).fetchone()
        return row[0] if row else "N/A"

    def _generate_motivation(self, score: CompatibilityScore, conflicts: List) -> str:
        """Generate human-readable motivation for suggestion."""
        reasons = []

        if score.hard_rules_compliant:
            reasons.append("Atende requisitos obrigatórios")
        else:
            reasons.append("Não atende todos os requisitos obrigatórios")

        if score.soft_preferences_compliant:
            reasons.append("Atende preferências do professor")

        if score.meets_capacity:
            reasons.append("Capacidade adequada")
        else:
            reasons.append("Capacidade insuficiente")

        if conflicts:
            reasons.append(f"Tem {len(conflicts)} conflitos")

        return "; ".join(reasons) if reasons else "Avaliação neutra"
