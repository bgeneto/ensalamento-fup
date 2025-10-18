"""
Room allocation service for Sistema de Ensalamento FUP/UnB
Handles rule-based room allocation algorithms and optimization
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from database import (
    DatabaseSession,
    AlocacaoSemestral,
    Demanda,
    Sala,
    Semestre,
    DiaSemana,
    HorarioBloco,
    TipoSala,
    Regra,
)
from src.services.semester_service import SemesterService
from src.services.inventory_service import InventoryService
from utils import parse_sigaa_schedule
from models import AlocacaoSemestralCreate
import random


class AllocationService:
    """Service class for room allocation operations"""

    # ALLOCATION RULES ENGINE
    @classmethod
    def get_allocation_rules(cls) -> List[Regra]:
        """Get all allocation rules"""
        try:
            with DatabaseSession() as session:
                return session.query(Regra).order_by(Regra.prioridade.desc()).all()
        except Exception as e:
            print(f"Error getting allocation rules: {e}")
            return []

    @classmethod
    def create_allocation_rule(
        cls, descricao: str, tipo_regra: str, config_json: str, prioridade: int = 1
    ) -> Optional[Regra]:
        """Create a new allocation rule"""
        try:
            with DatabaseSession() as session:
                new_rule = Regra(
                    descricao=descricao,
                    tipo_regra=tipo_regra,
                    config_json=config_json,
                    prioridade=prioridade,
                )
                session.add(new_rule)
                session.flush()
                return new_rule
        except Exception as e:
            print(f"Error creating allocation rule: {e}")
            return None

    # ROOM MATCHING ALGORITHM
    @classmethod
    def find_suitable_rooms(
        cls, demanda: Demanda, exclude_allocated: bool = True
    ) -> List[Dict[str, Any]]:
        """Find suitable rooms for a specific demand"""
        try:
            with DatabaseSession() as session:
                # Get demand schedule
                parsed_schedule = parse_sigaa_schedule(demanda.horario_sigaa_bruto)
                if not parsed_schedule:
                    return []

                # Base room query
                query = session.query(Sala).join(TipoSala)

                # Filter by capacity (rooms should accommodate at least the demand's vagas)
                query = query.filter(Sala.capacidade >= demanda.vagas_disciplina or 0)

                # Get all matching rooms
                rooms = query.all()

                suitable_rooms = []

                for room in rooms:
                    # Check availability for each time block in the demand's schedule
                    is_available = True
                    availability_details = []

                    for schedule_item in parsed_schedule:
                        dia_semana_id = schedule_item["dia_semana_id"]
                        codigo_bloco = schedule_item["codigo_bloco"]

                        # Check if room is available at this time
                        allocation_exists = (
                            session.query(AlocacaoSemestral)
                            .filter(
                                AlocacaoSemestral.sala_id == room.id,
                                AlocacaoSemestral.dia_semana_id == dia_semana_id,
                                AlocacaoSemestral.codigo_bloco == codigo_bloco,
                                AlocacaoSemestral.semestre_id == demanda.semestre_id,
                            )
                            .first()
                        )

                        if allocation_exists and exclude_allocated:
                            is_available = False
                            break

                        availability_details.append(
                            {
                                "dia_semana_id": dia_semana_id,
                                "codigo_bloco": codigo_bloco,
                                "available": not bool(allocation_exists),
                            }
                        )

                    if is_available:
                        # Calculate suitability score
                        score = cls.calculate_room_suitability_score(demanda, room)

                        suitable_rooms.append(
                            {
                                "room": room,
                                "score": score,
                                "availability": availability_details,
                                "capacity_match": room.capacidade
                                - (demanda.vagas_disciplina or 0),
                                "efficiency": cls.calculate_efficiency_score(
                                    demanda, room
                                ),
                            }
                        )

                # Sort by suitability score (descending)
                suitable_rooms.sort(key=lambda x: x["score"], reverse=True)

                return suitable_rooms
        except Exception as e:
            print(f"Error finding suitable rooms: {e}")
            return []

    @classmethod
    def calculate_room_suitability_score(cls, demanda: Demanda, room: Sala) -> float:
        """Calculate suitability score for room-demand match"""
        try:
            score = 0.0

            # Capacity efficiency (prefer rooms with minimal excess capacity)
            vagas = demanda.vagas_disciplina or 0
            if vagas > 0:
                excess_capacity = room.capacidade - vagas
                capacity_ratio = min(excess_capacity / vagas, 2.0)  # Cap at 200% excess
                score += max(0, 100 - (capacity_ratio * 30))  # Penalize excess capacity

            # Room type preferences (based on discipline characteristics)
            score += cls.get_room_type_score(demanda, room.tipo_sala)

            # Floor preference (prefer lower floors for general classrooms)
            if room.andar:
                try:
                    floor_num = int(room.andar) if room.andar.isdigit() else 1
                    score += max(0, 20 - (floor_num * 5))  # Penalty for higher floors
                except:
                    pass

            # Room characteristics bonus
            if room.caracteristicas:
                characteristics_bonus = cls.get_characteristics_bonus(
                    demanda, room.caracteristicas
                )
                score += characteristics_bonus

            return round(score, 2)
        except Exception as e:
            print(f"Error calculating suitability score: {e}")
            return 0.0

    @classmethod
    def get_room_type_score(cls, demanda: Demanda, room_type: TipoSala) -> float:
        """Get score based on room type and discipline characteristics"""
        try:
            discipline_name = (demanda.nome_disciplina or "").lower()
            discipline_code = (demanda.codigo_disciplina or "").lower()

            # Define room type preferences
            room_preferences = {
                "laboratório": [
                    "lab",
                    "prática",
                    "experimental",
                    "química",
                    "física",
                    "biologia",
                ],
                "laboratório de informática": [
                    "computação",
                    "programação",
                    "algoritmo",
                    "software",
                ],
                "sala de aula": ["teoria", "introdução", "fundamentos", "conceitos"],
                "auditório": ["palestra", "seminário", "apresentação", "conferência"],
            }

            room_type_name = (room_type.nome or "").lower()

            # Check for matches
            for pref_type, keywords in room_preferences.items():
                if pref_type in room_type_name:
                    for keyword in keywords:
                        if keyword in discipline_name or keyword in discipline_code:
                            return 30.0  # Strong match
                            break
                    return 15.0  # Type match but no keyword match

            return 5.0  # Default score
        except Exception as e:
            print(f"Error getting room type score: {e}")
            return 0.0

    @classmethod
    def get_characteristics_bonus(
        cls, demanda: Demanda, characteristics: List
    ) -> float:
        """Get bonus points based on room characteristics"""
        try:
            bonus = 0.0
            discipline_name = (demanda.nome_disciplina or "").lower()

            for characteristic in characteristics:
                char_name = (characteristic.nome or "").lower()

                # Audio/visual equipment bonus for presentation-heavy courses
                if any(
                    keyword in char_name
                    for keyword in ["projetor", "multimídia", "som"]
                ) and any(
                    keyword in discipline_name
                    for keyword in ["apresentação", "seminário", "debate"]
                ):
                    bonus += 10.0

                # Lab equipment bonus for practical courses
                if any(
                    keyword in char_name
                    for keyword in ["computador", "equipamento", "instrumento"]
                ) and any(
                    keyword in discipline_name
                    for keyword in ["prática", "laboratório", "experimental"]
                ):
                    bonus += 15.0

                # Accessibility bonus
                if "acessibilidade" in char_name:
                    bonus += 5.0

            return bonus
        except Exception as e:
            print(f"Error getting characteristics bonus: {e}")
            return 0.0

    @classmethod
    def calculate_efficiency_score(cls, demanda: Demanda, room: Sala) -> float:
        """Calculate efficiency score (how well the room is utilized)"""
        try:
            vagas = demanda.vagas_disciplina or 1
            capacity = room.capacidade or 1

            # Calculate utilization ratio
            utilization = vagas / capacity

            # Optimal utilization is around 80-90%
            if 0.8 <= utilization <= 0.9:
                return 100.0
            elif 0.7 <= utilization < 0.8:
                return 90.0
            elif 0.6 <= utilization < 0.7:
                return 75.0
            elif 0.5 <= utilization < 0.6:
                return 60.0
            elif 0.4 <= utilization < 0.5:
                return 40.0
            else:
                return 20.0  # Either too empty or overcrowded
        except Exception as e:
            print(f"Error calculating efficiency score: {e}")
            return 50.0

    # ALLOCATION OPERATIONS
    @classmethod
    def allocate_room(
        cls, demanda_id: int, sala_id: int, dia_semana_id: int, codigo_bloco: str
    ) -> Optional[AlocacaoSemestral]:
        """Allocate a room for a specific demand and time slot"""
        try:
            with DatabaseSession() as session:
                # Check if demand and room exist
                demanda = (
                    session.query(Demanda).filter(Demanda.id == demanda_id).first()
                )
                room = session.query(Sala).filter(Sala.id == sala_id).first()

                if not demanda or not room:
                    return None

                # Check if allocation already exists
                existing = (
                    session.query(AlocacaoSemestral)
                    .filter(
                        AlocacaoSemestral.demanda_id == demanda_id,
                        AlocacaoSemestral.sala_id == sala_id,
                        AlocacaoSemestral.dia_semana_id == dia_semana_id,
                        AlocacaoSemestral.codigo_bloco == codigo_bloco,
                    )
                    .first()
                )

                if existing:
                    return existing

                # Create new allocation
                new_allocation = AlocacaoSemestral(
                    demanda_id=demanda_id,
                    sala_id=sala_id,
                    dia_semana_id=dia_semana_id,
                    codigo_bloco=codigo_bloco,
                )

                session.add(new_allocation)
                session.flush()
                return new_allocation
        except Exception as e:
            print(f"Error allocating room: {e}")
            return None

    @classmethod
    def remove_allocation(cls, allocation_id: int) -> bool:
        """Remove an allocation"""
        try:
            with DatabaseSession() as session:
                allocation = (
                    session.query(AlocacaoSemestral)
                    .filter(AlocacaoSemestral.id == allocation_id)
                    .first()
                )

                if not allocation:
                    return False

                session.delete(allocation)
                return True
        except Exception as e:
            print(f"Error removing allocation: {e}")
            return False

    # AUTOMATIC ALLOCATION ENGINE
    @classmethod
    def auto_allocate_demanda(cls, demanda_id: int) -> Dict[str, Any]:
        """Automatically allocate the best available room for a demand"""
        try:
            with DatabaseSession() as session:
                demanda = (
                    session.query(Demanda).filter(Demanda.id == demanda_id).first()
                )
                if not demanda:
                    return {"success": False, "error": "Demanda não encontrada"}

                # Parse schedule
                parsed_schedule = parse_sigaa_schedule(demanda.horario_sigaa_bruto)
                if not parsed_schedule:
                    return {"success": False, "error": "Horário SIGAA inválido"}

                allocations = []
                failed_slots = []

                for schedule_item in parsed_schedule:
                    dia_semana_id = schedule_item["dia_semana_id"]
                    codigo_bloco = schedule_item["codigo_bloco"]

                    # Find suitable rooms for this time slot
                    suitable_rooms = cls.find_suitable_rooms(
                        demanda, exclude_allocated=True
                    )

                    # Filter rooms available at this specific time
                    available_rooms = [
                        room_info
                        for room_info in suitable_rooms
                        if any(
                            avail["dia_semana_id"] == dia_semana_id
                            and avail["codigo_bloco"] == codigo_bloco
                            and avail["available"]
                            for avail in room_info["availability"]
                        )
                    ]

                    if available_rooms:
                        # Select the best available room
                        best_room = available_rooms[0]["room"]

                        # Create allocation
                        allocation = cls.allocate_room(
                            demanda_id, best_room.id, dia_semana_id, codigo_bloco
                        )

                        if allocation:
                            allocations.append(
                                {
                                    "allocation_id": allocation.id,
                                    "sala_id": best_room.id,
                                    "sala_nome": best_room.nome,
                                    "dia_semana_id": dia_semana_id,
                                    "codigo_bloco": codigo_bloco,
                                    "score": available_rooms[0]["score"],
                                }
                            )
                        else:
                            failed_slots.append(f"{dia_semana_id}_{codigo_bloco}")
                    else:
                        failed_slots.append(f"{dia_semana_id}_{codigo_bloco}")

                success = len(failed_slots) == 0

                return {
                    "success": success,
                    "allocations": allocations,
                    "failed_slots": failed_slots,
                    "total_slots": len(parsed_schedule),
                    "allocated_slots": len(allocations),
                }
        except Exception as e:
            print(f"Error in auto allocation: {e}")
            return {"success": False, "error": str(e)}

    @classmethod
    def auto_allocate_semester(cls, semestre_id: int) -> Dict[str, Any]:
        """Automatically allocate rooms for all demands in a semester"""
        try:
            demandas = SemesterService.get_demandas_by_semestre(semestre_id)

            if not demandas:
                return {
                    "success": False,
                    "error": "Nenhuma demanda encontrada para este semestre",
                }

            results = []
            total_demandas = len(demandas)
            successful_allocations = 0
            partial_allocations = 0
            failed_allocations = 0

            for demanda in demandas:
                result = cls.auto_allocate_demanda(demanda.id)
                result["demanda_id"] = demanda.id
                result["demanda_codigo"] = demanda.codigo_disciplina
                result["demanda_nome"] = demanda.nome_disciplina

                results.append(result)

                if result["success"]:
                    successful_allocations += 1
                elif result.get("allocated_slots", 0) > 0:
                    partial_allocations += 1
                else:
                    failed_allocations += 1

            return {
                "success": True,
                "total_demandas": total_demandas,
                "successful_allocations": successful_allocations,
                "partial_allocations": partial_allocations,
                "failed_allocations": failed_allocations,
                "results": results,
            }
        except Exception as e:
            print(f"Error in semester auto allocation: {e}")
            return {"success": False, "error": str(e)}

    # ALLOCATION ANALYSIS
    @classmethod
    def get_allocation_statistics(cls, semestre_id: int) -> Dict[str, Any]:
        """Get comprehensive allocation statistics for a semester"""
        try:
            with DatabaseSession() as session:
                # Get semester info
                semestre = (
                    session.query(Semestre).filter(Semestre.id == semestre_id).first()
                )
                if not semestre:
                    return {}

                # Get all allocations for the semester
                allocations = (
                    session.query(AlocacaoSemestral)
                    .filter(AlocacaoSemestral.semestre_id == semestre_id)
                    .all()
                )

                # Get all demands for the semester
                demandas = (
                    session.query(Demanda)
                    .filter(Demanda.semestre_id == semestre_id)
                    .all()
                )

                # Calculate statistics
                total_demandas = len(demandas)
                total_allocations = len(allocations)
                allocated_demandas = len(set(alloc.demanda_id for alloc in allocations))

                # Room utilization
                room_usage = {}
                for allocation in allocations:
                    room_id = allocation.sala_id
                    room_usage[room_id] = room_usage.get(room_id, 0) + 1

                # Capacity utilization
                capacity_utilization = []
                for allocation in allocations:
                    demanda = (
                        session.query(Demanda)
                        .filter(Demanda.id == allocation.demanda_id)
                        .first()
                    )
                    room = (
                        session.query(Sala)
                        .filter(Sala.id == allocation.sala_id)
                        .first()
                    )

                    if demanda and room:
                        vagas = demanda.vagas_disciplina or 0
                        capacity = room.capacidade or 1
                        utilization = (vagas / capacity) * 100 if capacity > 0 else 0
                        capacity_utilization.append(utilization)

                avg_utilization = (
                    sum(capacity_utilization) / len(capacity_utilization)
                    if capacity_utilization
                    else 0
                )

                return {
                    "semestre": {
                        "id": semestre.id,
                        "nome": semestre.nome,
                        "status": semestre.status,
                    },
                    "demandas": {
                        "total": total_demandas,
                        "alocadas": allocated_demandas,
                        "taxa_alocacao": (
                            (allocated_demandas / total_demandas * 100)
                            if total_demandas > 0
                            else 0
                        ),
                    },
                    "alocacoes": {
                        "total": total_allocations,
                        "salas_utilizadas": len(room_usage),
                    },
                    "utilizacao": {
                        "media_capacidade": round(avg_utilization, 2),
                        "uso_salas": room_usage,
                    },
                }
        except Exception as e:
            print(f"Error getting allocation statistics: {e}")
            return {}

    @classmethod
    def get_room_schedule(cls, sala_id: int, semestre_id: int) -> List[Dict[str, Any]]:
        """Get the schedule for a specific room in a semester"""
        try:
            with DatabaseSession() as session:
                allocations = (
                    session.query(AlocacaoSemestral)
                    .filter(
                        AlocacaoSemestral.sala_id == sala_id,
                        AlocacaoSemestral.semestre_id == semestre_id,
                    )
                    .all()
                )

                schedule = []

                for allocation in allocations:
                    demanda = (
                        session.query(Demanda)
                        .filter(Demanda.id == allocation.demanda_id)
                        .first()
                    )
                    dia_semana = (
                        session.query(DiaSemana)
                        .filter(DiaSemana.id_sigaa == allocation.dia_semana_id)
                        .first()
                    )
                    horario_bloco = (
                        session.query(HorarioBloco)
                        .filter(HorarioBloco.codigo_bloco == allocation.codigo_bloco)
                        .first()
                    )

                    if demanda and dia_semana and horario_bloco:
                        schedule.append(
                            {
                                "dia_semana": dia_semana.nome,
                                "dia_semana_id": allocation.dia_semana_id,
                                "codigo_bloco": allocation.codigo_bloco,
                                "horario_inicio": horario_bloco.horario_inicio.strftime(
                                    "%H:%M"
                                ),
                                "horario_fim": horario_bloco.horario_fim.strftime(
                                    "%H:%M"
                                ),
                                "disciplina": demanda.codigo_disciplina,
                                "disciplina_nome": demanda.nome_disciplina,
                                "professor": demanda.professores_disciplina,
                                "turma": demanda.turma_disciplina,
                                "vagas": demanda.vagas_disciplina,
                                "allocation_id": allocation.id,
                            }
                        )

                # Sort by day and time
                schedule.sort(key=lambda x: (x["dia_semana_id"], x["codigo_bloco"]))

                return schedule
        except Exception as e:
            print(f"Error getting room schedule: {e}")
            return []

    @classmethod
    def clear_all_allocations(cls, semestre_id: int) -> bool:
        """Clear all allocations for a semester"""
        try:
            with DatabaseSession() as session:
                # Delete all allocations for the semester
                session.query(AlocacaoSemestral).filter(
                    AlocacaoSemestral.semestre_id == semestre_id
                ).delete()

                return True
        except Exception as e:
            print(f"Error clearing allocations: {e}")
            return False
