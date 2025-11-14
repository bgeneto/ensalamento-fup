"""
Service layer for ReservaEvento business logic.

Handles the creation, management, and conflict detection for recurring
room reservations using the Parent/Instance design pattern.
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from src.repositories.reserva_evento import ReservaEventoRepository
from src.repositories.reserva_ocorrencia import ReservaOcorrenciaRepository
from src.repositories.alocacao import AlocacaoRepository
from src.repositories.reserva import ReservaRepository
from src.schemas.allocation import (
    ReservaEventoCreate,
    ReservaEventoRead,
    ReservaOcorrenciaCreate,
    ReservaOcorrenciaRead,
    RegraRecorrencia,
    RegraUnica,
)
from src.utils.recurrence_calculator import RecurrenceCalculator
from src.utils.ui_feedback import set_session_feedback

logger = logging.getLogger(__name__)


class ReservaEventoService:
    """
    Service layer for managing recurring room reservations.

    This service orchestrates the creation and management of recurring
    reservations, handling conflict detection, date expansion,
    and database transactions across multiple tables.
    """

    def __init__(self, session: Session):
        """
        Initialize the service with a database session.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.evento_repo = ReservaEventoRepository(session)
        self.ocorrencia_repo = ReservaOcorrenciaRepository(session)
        self.alocacao_repo = AlocacaoRepository(session)
        self.reserva_repo = ReservaRepository(session)

    def criar_reserva_recorrente(
        self,
        evento_dto: ReservaEventoCreate,
        blocos_selecionados: List[str],
        data_inicio: date,
    ) -> Tuple[Optional[ReservaEventoRead], List[str]]:
        """
        Create a new recurring reservation with all its occurrences.

        Args:
            evento_dto: Event data for the parent reservation
            blocos_selecionados: List of time block codes (e.g., ["M1", "M2"])
            data_inicio: Start date for the recurrence

        Returns:
            Tuple of (created event, list of error messages)
        """
        errors = []

        try:
            # Parse and validate recurrence rule
            import json

            rule_dict = json.loads(evento_dto.regra_recorrencia_json)

            if not RecurrenceCalculator.validate_recurrence_rule(rule_dict):
                errors.append("Regra de recorrência inválida")
                return None, errors

            # Check past date restriction
            if data_inicio < date.today():
                errors.append("Data de início não pode ser no passado")
                return None, errors

            # Check one-year limit
            one_year_later = date.today() + timedelta(days=365)
            if "fim" in rule_dict:
                end_date = RecurrenceCalculator._parse_date(rule_dict["fim"])
                if end_date > one_year_later:
                    errors.append(
                        "Reservas não podem ultrapassar um ano a partir da data atual"
                    )
                    return None, errors

            # Generate all occurrences with dates and blocks
            occurrences_with_blocks = self._generate_occurrences(
                rule_dict, data_inicio, blocos_selecionados
            )

            if not occurrences_with_blocks:
                errors.append("Nenhuma ocorrência gerada para a regra especificada")
                return None, errors

            # Check for conflicts across all occurrences
            conflict_errors = self._check_conflicts_for_occurrences(
                evento_dto.sala_id, occurrences_with_blocks
            )

            if conflict_errors:
                errors.extend(conflict_errors)
                return None, errors

            # Create the event and all occurrences in a transaction
            logger.info(f"Starting event creation for: {evento_dto.titulo_evento}")
            created_event = self._create_event_with_occurrences(
                evento_dto, occurrences_with_blocks
            )

            if created_event:
                logger.info(f"Event creation successful: {created_event.id}")
                return created_event, []
            else:
                logger.error("Event creation failed - see logs above for details")
                errors.append(
                    "Erro ao salvar a reserva no banco de dados (Verifique o log para detalhes)"
                )
                return None, errors

        except json.JSONDecodeError:
            errors.append("Formato JSON inválido na regra de recorrência")
            return None, errors
        except Exception as e:
            import traceback

            logger.error(f"Erro inesperado ao criar reserva: {str(e)}")
            logger.error(traceback.format_exc())
            errors.append(f"Erro inesperado: {str(e)}")
            return None, errors

    def _generate_occurrences(
        self, rule_dict: Dict[str, Any], start_date: date, time_blocks: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Generate all occurrence dates and blocks from a recurrence rule.

        Args:
            rule_dict: Recurrence rule dictionary
            start_date: Start date
            time_blocks: List of time block codes

        Returns:
            List of occurrence dictionaries with data_reserva and codigo_bloco
        """
        # Import here to avoid circular imports
        from src.schemas.allocation import (
            RegraUnica,
            RegraDiaria,
            RegraSemanal,
            RegraMensalDia,
            RegraMensalPosicao,
        )
        import json

        # Create appropriate rule object based on type
        tipo = rule_dict.get("tipo")

        if tipo == "unica":
            rule = RegraUnica()
        elif tipo == "diaria":
            rule = RegraDiaria(
                intervalo=rule_dict.get("intervalo", 1), fim=rule_dict["fim"]
            )
        elif tipo == "semanal":
            rule = RegraSemanal(dias=rule_dict["dias"], fim=rule_dict["fim"])
        elif tipo == "mensal" and "dia_mes" in rule_dict:
            rule = RegraMensalDia(dia_mes=rule_dict["dia_mes"], fim=rule_dict["fim"])
        elif tipo == "mensal" and "posicao" in rule_dict:
            rule = RegraMensalPosicao(
                posicao=rule_dict["posicao"],
                dia_semana=rule_dict["dia_semana"],
                fim=rule_dict["fim"],
            )
        else:
            logger.error(f"Unknown recurrence type: {tipo}")
            return []

        occurrences = RecurrenceCalculator.expand_dates_with_blocks(
            rule, start_date, time_blocks
        )
        logger.info(f"Generated {len(occurrences)} occurrences from rule: {rule_dict}")
        if occurrences:
            logger.debug(f"First occurrence: {occurrences[0]}")
            logger.debug(f"Last occurrence: {occurrences[-1]}")
        return occurrences

    def _check_conflicts_for_occurrences(
        self, room_id: int, occurrences_with_blocks: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Check for conflicts in all occurrences against semester allocations and other reservations.

        Args:
            room_id: Room ID
            occurrences_with_blocks: List of occurrence dictionaries

        Returns:
            List of conflict error messages
        """
        errors = []
        conflict_count = 0
        logger.info(
            f"Checking conflicts for room {room_id} with {len(occurrences_with_blocks)} occurrences"
        )

        for occurrence in occurrences_with_blocks:
            data_reserva = occurrence["data_reserva"]
            codigo_bloco = occurrence["codigo_bloco"]

            # Check conflicts with semester allocations
            weekday = (
                datetime.strptime(data_reserva, "%Y-%m-%d").weekday() + 2
            )  # SIGAA format
            semester_conflict = self.alocacao_repo.check_conflict(
                room_id, weekday, codigo_bloco
            )

            if semester_conflict:
                conflict_count += 1
                logger.warning(
                    f"Conflict found: semester allocation on {data_reserva} {codigo_bloco}"
                )
                continue  # Don't add individual error messages, just count

            # Check conflicts with existing reservations (both legacy and recurring)
            reserva_conflict = self.reserva_repo.check_conflict(
                room_id, codigo_bloco, data_reserva
            )

            if reserva_conflict:
                conflict_count += 1
                logger.warning(
                    f"Conflict found: existing reservation on {data_reserva} {codigo_bloco}"
                )

        if conflict_count > 0:
            errors.append(
                f"Encontrados {conflict_count} conflito(s) com alocações existentes. Por favor, verifique os horários e datas selecionadas."
            )

        return errors

    def _create_event_with_occurrences(
        self,
        evento_dto: ReservaEventoCreate,
        occurrences_with_blocks: List[Dict[str, Any]],
    ) -> Optional[ReservaEventoRead]:
        """
        Create the parent event and all its occurrences in a transaction.

        Args:
            evento_dto: Event data
            occurrences_with_blocks: List of occurrence data

        Returns:
            Created event or None if failed
        """
        try:
            # Create the parent event
            logger.info(
                f"Creating event: {evento_dto.titulo_evento} in room {evento_dto.sala_id}"
            )
            created_event = self.evento_repo.create(evento_dto)

            if not created_event:
                logger.error("Failed to create parent event - repository returned None")
                return None

            logger.info(f"Event created successfully with ID: {created_event.id}")

            # Create all occurrences
            ocorrencia_dtos = []
            for occurrence in occurrences_with_blocks:
                ocorrencia_dto = ReservaOcorrenciaCreate(
                    evento_id=created_event.id,
                    data_reserva=occurrence["data_reserva"],
                    codigo_bloco=occurrence["codigo_bloco"],
                )
                ocorrencia_dtos.append(ocorrencia_dto)

            logger.info(
                f"Creating {len(ocorrencia_dtos)} occurrences for event {created_event.id}"
            )

            # Bulk create occurrences
            created_ocorrencias = self.ocorrencia_repo.create_bulk(ocorrencia_dtos)

            if not created_ocorrencias:
                # Rollback event creation if occurrences failed
                logger.error(
                    f"Failed to create occurrences - rolling back event {created_event.id}"
                )
                self.evento_repo.delete(created_event.id)
                return None

            logger.info(f"Successfully created {len(created_ocorrencias)} occurrences")
            return created_event

        except Exception as e:
            # Transaction should be rolled back automatically
            import traceback

            logger.error(f"Error creating event with occurrences: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(traceback.format_exc())
            return None

    def excluir_serie_recorrente(
        self, evento_id: int, username: str
    ) -> Tuple[bool, str]:
        """
        Delete an entire recurring reservation series.

        Args:
            evento_id: Event ID
            username: Username of the user attempting deletion

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get the event
            evento = self.evento_repo.get_by_id(evento_id)
            if not evento:
                return False, "Reserva não encontrada"

            # Check permissions (users can only delete their own events, admins can delete any)
            from st.session_state import get as ss_get

            current_user = ss_get("username", "")
            is_admin = ss_get("authentication_status") and ss_get("role") == "admin"

            if not is_admin and evento.username_criador != current_user:
                return False, "Você não tem permissão para excluir esta reserva"

            # Delete all occurrences first (cascade should handle this, but let's be explicit)
            self.ocorrencia_repo.delete_by_evento(evento_id)

            # Delete the parent event
            success = self.evento_repo.delete(evento_id)

            if success:
                return True, "Série de reservas excluída com sucesso"
            else:
                return False, "Erro ao excluir a reserva"

        except Exception as e:
            return False, f"Erro ao excluir reserva: {str(e)}"

    def atualizar_serie_recorrente(
        self, evento_id: int, novos_dados: Dict[str, Any], username: str
    ) -> Tuple[bool, str]:
        """
        Update a recurring reservation series.

        Note: This is a simplified implementation that only updates
        basic event details. For full functionality, this would need
        to handle date/block changes, which would require recreating
        occurrences.

        Args:
            evento_id: Event ID
            novos_dados: New data for the event
            username: Username making the update

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get the event
            evento = self.evento_repo.get_by_id(evento_id)
            if not evento:
                return False, "Reserva não encontrada"

            # Check permissions
            current_user = ss_get("username", "")
            is_admin = ss_get("authentication_status") and ss_get("role") == "admin"

            if not is_admin and evento.username_criador != current_user:
                return False, "Você não tem permissão para atualizar esta reserva"

            # For now, only allow updating basic fields (not recurrence rules)
            update_data = {}

            if "titulo_evento" in novos_dados:
                update_data["titulo_evento"] = novos_dados["titulo_evento"]

            if "nome_solicitante" in novos_dados:
                update_data["nome_solicitante"] = novos_dados["nome_solicitante"]

            if "nome_responsavel" in novos_dados:
                update_data["nome_responsavel"] = novos_dados["nome_responsavel"]

            if not update_data:
                return False, "Nenhum campo para atualizar"

            # Update the event
            from pydantic import BaseModel

            class UpdateDTO(BaseModel):
                titulo_evento: Optional[str] = None
                nome_solicitante: Optional[str] = None
                nome_responsavel: Optional[str] = None

            update_dto = UpdateDTO(**update_data)
            updated_event = self.evento_repo.update(evento_id, update_dto)

            if updated_event:
                return True, "Reserva atualizada com sucesso"
            else:
                return False, "Erro ao atualizar a reserva"

        except Exception as e:
            return False, f"Erro ao atualizar reserva: {str(e)}"

    def buscar_reservas_do_usuario(
        self, username: str, include_past: bool = False
    ) -> List[ReservaEventoRead]:
        """
        Get all recurring reservations for a user.

        Args:
            username: Username to search for
            include_past: Whether to include past reservations

        Returns:
            List of user's recurring reservations
        """
        eventos = self.evento_repo.get_by_creator(username)

        if not include_past:
            # Filter out events that only have past occurrences
            today = date.today()
            eventos_filtrados = []

            for evento in eventos:
                evento_with_occurrences = self.evento_repo.get_with_occurrences(
                    evento.id
                )
                if evento_with_occurrences and evento_with_occurrences.ocorrencias:
                    # Check if any occurrence is today or in the future
                    has_future_occurrence = any(
                        datetime.strptime(occ.data_reserva, "%Y-%m-%d").date() >= today
                        for occ in evento_with_occurrences.ocorrencias
                        if occ.is_ativa()
                    )

                    if has_future_occurrence:
                        eventos_filtrados.append(evento)

            return eventos_filtrados

        return eventos

    def buscar_reservas_por_sala_e_data(
        self, room_id: int, data_reserva: str
    ) -> List[ReservaOcorrenciaRead]:
        """
        Get all active reservations for a room on a specific date.

        Args:
            room_id: Room ID
            data_reserva: Date in YYYY-MM-DD format

        Returns:
            List of active occurrences for the room and date
        """
        return self.ocorrencia_repo.get_active_occurrences(room_id, data_reserva)

    def validar_regra_recurrence(self, rule_json: str) -> Tuple[bool, str]:
        """
        Validate a recurrence rule JSON string.

        Args:
            rule_json: JSON string containing the recurrence rule

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            import json

            rule_dict = json.loads(rule_json)

            if RecurrenceCalculator.validate_recurrence_rule(rule_dict):
                return True, ""
            else:
                return False, "Regra de recorrência inválida ou incompleta"

        except json.JSONDecodeError as e:
            return False, f"JSON inválido: {str(e)}"
        except Exception as e:
            return False, f"Erro ao validar regra: {str(e)}"
