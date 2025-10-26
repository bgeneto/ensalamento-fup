"""Service for executing manual allocation operations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.schemas.manual_allocation import (
    AllocationResult,
    ConflictDetail,
    RoomSuggestion,
    AllocationSuggestions,
)
from src.repositories.alocacao import AlocacaoRepository
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.reserva import ReservaRepository
from src.repositories.semestre import SemestreRepository
from src.repositories.sala import SalaRepository
from src.repositories.regra import RegraRepository
from src.schemas.allocation import AlocacaoSemestralCreate
from src.utils.sigaa_parser import SigaaScheduleParser
from src.services.room_scoring_service import RoomScoringService
from sqlalchemy import text


class ManualAllocationService:
    """Service for manual allocation execution with conflict detection."""

    def __init__(self, session: Session):
        """Initialize service with repositories."""
        self.session = session
        self.alocacao_repo = AlocacaoRepository(session)
        self.demanda_repo = DisciplinaRepository(session)
        self.semestre_repo = SemestreRepository(session)
        self.reserva_repo = ReservaRepository(session)
        self.sala_repo = SalaRepository(session)
        self.regra_repo = RegraRepository(session)
        self.parser = SigaaScheduleParser()
        self.scoring_service = RoomScoringService(session)

    def allocate_demand(self, demanda_id: int, sala_id: int) -> AllocationResult:
        """
        Allocate a demand to a room.

        This method:
        1. Parses the demand's schedule into atomic blocks
        2. Checks for conflicts in alocacoes_semestrais table
        3. Creates allocation records for each block atomically
        4. Returns success/failure with detailed conflict information
        """
        # Get demand details
        demanda = self.demanda_repo.get_by_id(demanda_id)
        if not demanda:
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                error_message="Demanda não encontrada",
            )

        # Get semester (used for foreign key)
        semester = self.semestre_repo.get_by_id(demanda.semestre_id)
        if not semester:
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                error_message="Semestre da demanda não encontrado",
            )

        # Parse schedule into atomic blocks
        atomic_blocks = self.parser.split_to_atomic_tuples(demanda.horario_sigaa_bruto)
        if not atomic_blocks:
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                error_message="Não foi possível parsear o horário da demanda",
            )

        # Create atomic blocks preview for result
        atomic_preview = [f"{dia}{bloco}" for bloco, dia in atomic_blocks]

        # Check for conflicts before attempting allocation
        conflicts = self._check_allocation_conflicts(
            sala_id, atomic_blocks, semester.id
        )
        if conflicts:
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                sala_id=sala_id,
                conflicts=conflicts,
                allocated_blocks_count=len(atomic_blocks),
                atomic_blocks_preview=atomic_preview,
                error_message=f"Encontrados {len(conflicts)} conflitos de horário",
            )

        # Execute allocation atomically
        try:
            created_allocation_ids = []

            for bloco_codigo, dia_sigaa in atomic_blocks:
                allocation_dto = AlocacaoSemestralCreate(
                    semestre_id=semester.id,
                    demanda_id=demanda_id,
                    sala_id=sala_id,
                    dia_semana_id=dia_sigaa,
                    codigo_bloco=bloco_codigo,
                )

                new_allocation = self.alocacao_repo.create(allocation_dto)
                created_allocation_ids.append(new_allocation.id)

            return AllocationResult(
                success=True,
                demanda_id=demanda_id,
                sala_id=sala_id,
                created_allocation_ids=created_allocation_ids,
                allocated_blocks_count=len(atomic_blocks),
                atomic_blocks_preview=atomic_preview,
            )

        except IntegrityError as e:
            # This shouldn't happen due to conflict checking, but handle it gracefully
            self.session.rollback()
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                sala_id=sala_id,
                error_message=f"Erro de integridade ao alocar: {str(e)}",
            )
        except Exception as e:
            self.session.rollback()
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                sala_id=sala_id,
                error_message=f"Erro inesperado na alocação: {str(e)}",
            )

    def _check_allocation_conflicts(
        self, sala_id: int, atomic_blocks: List[tuple], semester_id: int
    ) -> List[ConflictDetail]:
        """
        Check for conflicts when allocating these blocks to this room.

        Note: In a complete implementation, this would also check against
        ad-hoc reservations, but that requires complex date-to-weekday conversion.
        For now, we only check semester allocations.
        """
        conflicts = []

        for bloco_codigo, dia_sigaa in atomic_blocks:
            # Check if there's already an allocation for this time slot in CURRENT semester
            has_conflict = self.alocacao_repo.check_conflict(
                sala_id, dia_sigaa, bloco_codigo, semestre_id=semester_id
            )

            if has_conflict:
                # Find the conflicting allocation for detailed error message
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

        return conflicts

    def get_allocation_progress(self, semester_id: int) -> dict:
        """Get allocation progress summary for a semester."""
        # Get total demands for semester
        demandas = self.demanda_repo.get_by_semestre(semester_id)
        total_demands = len(demandas)

        # Get allocated demands (demands that have at least one allocation)
        allocations = self.alocacao_repo.get_by_semestre(semester_id)
        allocated_demand_ids = set(alloc.demanda_id for alloc in allocations)
        allocated_demands = len(allocated_demand_ids)

        # Calculate percentage
        allocation_percent = (
            (allocated_demands / total_demands * 100) if total_demands > 0 else 0
        )

        return {
            "semester_id": semester_id,
            "total_demands": total_demands,
            "allocated_demands": allocated_demands,
            "unallocated_demands": total_demands - allocated_demands,
            "allocation_percent": allocation_percent,
        }

    def get_unallocated_demands(self, semester_id: int) -> List[dict]:
        """Get all demands in a semester that haven't been allocated yet."""
        # Get all demands for semester
        demandas = self.demanda_repo.get_by_semestre(semester_id)

        # Get allocated demand IDs
        allocations = self.alocacao_repo.get_by_semestre(semester_id)
        allocated_ids = set(alloc.demanda_id for alloc in allocations)

        # Filter out allocated demands
        unallocated = [d for d in demandas if d.id not in allocated_ids]

        return [self.demanda_repo.orm_to_dto(d) for d in unallocated]

    def get_allocated_demands(self, semester_id: int) -> List[dict]:
        """Get all demands in a semester that have been allocated."""
        # Get all demands for semester
        demandas = self.demanda_repo.get_by_semestre(semester_id)

        # Get allocated demand IDs
        allocations = self.alocacao_repo.get_by_semestre(semester_id)
        allocated_ids = set(alloc.demanda_id for alloc in allocations)

        # Filter to only allocated demands
        allocated = [d for d in demandas if d.id in allocated_ids]

        return [self.demanda_repo.orm_to_dto(d) for d in allocated]

    def get_all_demands(self, semester_id: int) -> List[dict]:
        """Get all demands in a semester regardless of allocation status."""
        demandas = self.demanda_repo.get_by_semestre(semester_id)
        return [self.demanda_repo.orm_to_dto(d) for d in demandas]

    def deallocate_demand(self, demanda_id: int) -> AllocationResult:
        """
        Deallocate a demand by removing all its allocations.

        This method:
        1. Finds all allocations for the demand
        2. Deletes them atomically
        3. Returns success/failure with details

        Args:
            demanda_id: The demand ID to deallocate

        Returns:
            AllocationResult with deallocation details
        """
        # Check if demand exists
        demanda = self.demanda_repo.get_by_id(demanda_id)
        if not demanda:
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                error_message="Demanda não encontrada",
            )

        # Get all allocations for this demand
        allocations = self.alocacao_repo.get_by_demanda(demanda_id)
        if not allocations:
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                error_message="Demanda não possui alocações para remover",
            )

        try:
            # Delete all allocations for this demand
            deleted_count = 0
            deleted_allocation_ids = []

            for alloc in allocations:
                self.alocacao_repo.delete(alloc.id)
                deleted_allocation_ids.append(alloc.id)
                deleted_count += 1

            return AllocationResult(
                success=True,
                demanda_id=demanda_id,
                sala_id=None,  # Deallocation doesn't target a specific room
                error_message=f"Removidas {deleted_count} alocação{'ões' if deleted_count > 1 else ''}",
            )

        except Exception as e:
            self.session.rollback()
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                error_message=f"Erro ao remover alocações: {str(e)}",
            )

    def get_suggestions_for_demand(
        self, demanda_id: int, semester_id: int
    ) -> AllocationSuggestions:
        """
        Get room suggestions for a specific demand using unified advanced scoring.

        Returns AllocationSuggestions with top suggestions, other available, and conflicting rooms.
        Now uses the same advanced scoring as autonomous allocation with:
        - Historical frequency bonus (RF-006.6)
        - Semester-isolated conflict detection
        """
        # Use the shared advanced scoring service
        candidates = self.scoring_service.score_room_candidates_for_demand(
            demanda_id, semester_id
        )

        # Convert candidates to RoomSuggestion format for compatibility
        top_suggestions = []
        other_available = []
        conflicting_rooms = []

        for candidate in candidates:
            # Calculate additional compatibility metrics for RoomSuggestion format
            demanda = self.demanda_repo.get_by_id(demanda_id)
            if not demanda:
                continue

            # Get hard rules compliance (for RoomSuggestion format)
            hard_rules = self.regra_repo.find_rules_by_disciplina(
                demanda.codigo_disciplina
            )
            hard_rules = [r for r in hard_rules if r.prioridade == 0]

            hard_compliant = True
            rule_violations = []

            for rule in hard_rules:
                if not self._manual_check_rule_compliance(
                    demanda, candidate.sala, rule
                ):
                    hard_compliant = False
                    rule_violations.append(f"Regra dura violada: {rule.descricao}")

            # Generate detailed scoring breakdown for UI display
            breakdown_data = None
            if candidate.scoring_breakdown:
                breakdown_data = {
                    "capacity_points": candidate.scoring_breakdown.capacity_points,
                    "hard_rules_points": candidate.scoring_breakdown.hard_rules_points,
                    "soft_preference_points": candidate.scoring_breakdown.soft_preference_points,
                    "historical_frequency_points": candidate.scoring_breakdown.historical_frequency_points,
                    "capacity_satisfied": candidate.scoring_breakdown.capacity_satisfied,
                    "hard_rules_satisfied": candidate.scoring_breakdown.hard_rules_satisfied,
                    "soft_preferences_satisfied": candidate.scoring_breakdown.soft_preferences_satisfied,
                    "historical_allocations": candidate.scoring_breakdown.historical_allocations,
                }

            # Create RoomSuggestion object
            suggestion = RoomSuggestion(
                sala_id=candidate.sala.id,
                nome_sala=self._get_room_full_name(candidate.sala),
                tipo_sala_nome=self._get_room_type_name(candidate.sala.tipo_sala_id),
                capacidade=candidate.sala.capacidade or 0,
                andar=candidate.sala.andar,
                predio_nome=self._get_building_name(candidate.sala.predio_id),
                compatibility_score=candidate.score,
                hard_rules_compliant=hard_compliant,
                soft_preferences_compliant=(
                    bool(
                        candidate.scoring_breakdown
                        and candidate.scoring_breakdown.soft_preferences_satisfied
                    )
                    if candidate.scoring_breakdown
                    else True
                ),
                meets_capacity=(candidate.sala.capacidade or 0)
                >= demanda.vagas_disciplina,
                has_conflicts=candidate.has_conflicts,
                conflict_details=(
                    [
                        # Note: conflict_details need to be provided by RoomScoringService with more formatting
                        # For now, just indicate there are conflicts
                        "Conflito detectado neste horário"
                    ]
                    if candidate.has_conflicts
                    else []
                ),
                rule_violations=rule_violations,
                motivation_reason=(
                    self._generate_detailed_motivation_reason(
                        candidate.scoring_breakdown
                    )
                    if candidate.scoring_breakdown
                    else self._generate_motivation_reason(
                        hard_compliant,
                        True,  # soft preferences assumed
                        (candidate.sala.capacidade or 0) >= demanda.vagas_disciplina,
                        candidate.has_conflicts,
                    )
                ),
                scoring_breakdown=breakdown_data,
            )

            # Categorize based on conflicts and scoring
            if candidate.has_conflicts:
                conflicting_rooms.append(suggestion)
            else:
                # Prioritize top suggestions (highest scores first)
                if candidate.score >= 5:  # Good hard rule + soft rule match
                    top_suggestions.append(suggestion)
                else:
                    other_available.append(suggestion)

        # Sort by score (highest first) within each category
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

    def _manual_check_rule_compliance(self, demanda, room, rule) -> bool:
        """Check rule compliance for RoomSuggestion creation."""
        import json

        try:
            config = json.loads(rule.config_json)

            if rule.tipo_regra == "DISCIPLINA_TIPO_SALA":
                required_type_id = config.get("tipo_sala_id")
                return room.tipo_sala_id == required_type_id

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

    def _get_room_full_name(self, room) -> str:
        """Get room full name (building-room)."""
        building_name = self._get_building_name(room.predio_id)
        return f"{building_name}: {room.nome}"

    def _get_building_name(self, predio_id: int) -> str:
        """Get building name by ID."""
        if not predio_id:
            return "N/A"
        # Use direct query since we need to access predios table
        stmt = text("SELECT nome FROM predios WHERE id = :pid")
        row = self.session.execute(stmt, {"pid": predio_id}).fetchone()
        return row[0] if row else "N/A"

    def _get_room_type_name(self, tipo_sala_id: int) -> str:
        """Get room type name by ID."""
        if not tipo_sala_id:
            return "N/A"
        stmt = text("SELECT nome FROM tipos_sala WHERE id = :tid")
        row = self.session.execute(stmt, {"tid": tipo_sala_id}).fetchone()
        return row[0] if row else "N/A"

    def _get_characteristic_name(self, caracteristica_id: int) -> str:
        """Get characteristic name by ID."""
        stmt = text("SELECT nome FROM caracteristicas WHERE id = :cid")
        row = self.session.execute(stmt, {"cid": caracteristica_id}).fetchone()
        return row[0] if row else ""

    def _get_room_characteristics(self, sala_id: int):
        """Get characteristic IDs for a room."""
        stmt = text(
            "SELECT caracteristica_id FROM sala_caracteristicas WHERE sala_id = :sala_id"
        )
        rows = self.session.execute(stmt, {"sala_id": sala_id}).fetchall()
        return {row[0] for row in rows}

    def _generate_motivation_reason(
        self, hard_compliant, soft_compliant, meets_capacity, has_conflicts
    ) -> str:
        """Generate human-readable motivation for suggestion."""
        reasons = []

        if hard_compliant:
            reasons.append("Atende requisitos obrigatórios")
        else:
            reasons.append("Não atende todos os requisitos obrigatórios")

        if soft_compliant:
            reasons.append("Atende preferências do professor")

        if meets_capacity:
            reasons.append("Capacidade adequada")
        else:
            reasons.append("Capacidade insuficiente")

        if has_conflicts:
            reasons.append("Tem conflitos")

        return "; ".join(reasons) if reasons else "Avaliação neutra"

    def _generate_detailed_motivation_reason(self, breakdown) -> str:
        """
        Generate detailed, human-readable explanation of scoring breakdown.

        Shows exactly how each point was earned for maximum transparency.
        """
        if not breakdown:
            return "Avaliação padrão"

        parts = []

        # Capacity
        if breakdown.capacity_points > 0:
            parts.append("✅ Capacidade adequada (+1)")
        else:
            parts.append("❌ Capacidade insuficiente (+0)")

        # Hard rules
        if (
            isinstance(breakdown.hard_rules_satisfied, list)
            and breakdown.hard_rules_satisfied
        ):
            rules_text = "; ".join(breakdown.hard_rules_satisfied)
            parts.append(
                f"✅ Regras obrigatórias (+{breakdown.hard_rules_points}): {rules_text}"
            )
        elif breakdown.hard_rules_points == 0:
            parts.append("❌ Regras obrigatórias não atendidas (+0)")

        # Soft preferences (only if hard rules pass)
        if (
            breakdown.hard_rules_points > 0
            and isinstance(breakdown.soft_preferences_satisfied, list)
            and breakdown.soft_preferences_satisfied
        ):
            prefs_text = "; ".join(breakdown.soft_preferences_satisfied)
            parts.append(
                f"✅ Preferências do professor (+{breakdown.soft_preference_points}): {prefs_text}"
            )
        elif breakdown.hard_rules_points == 0:
            parts.append(
                "⏸️ Preferências não verificadas (regras obrigatórias falharam)"
            )

        # Historical frequency
        if breakdown.historical_frequency_points > 0:
            parts.append(
                f"📈 Disciplina já alocada aqui {breakdown.historical_allocations}x (+{breakdown.historical_frequency_points})"
            )
        else:
            parts.append("📉 Disciplina nunca alocada aqui (+0)")

        return " | ".join(parts)
