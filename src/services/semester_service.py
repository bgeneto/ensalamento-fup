"""
Semester management service for Sistema de Ensalamento FUP/UnB
Handles semester operations, demand management, and scheduling
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, date
from database import DatabaseSession, Semestre, Demanda, DiaSemana, HorarioBloco
from models import SemestreStatusEnum, DemandaCreate, DemandaUpdate
from src.services.inventory_service import InventoryService
from utils import parse_sigaa_schedule, validate_sigaa_schedule


class SemesterService:
    """Service class for semester management operations"""

    # SEMESTER MANAGEMENT
    @classmethod
    def create_semestre(
        cls, nome: str, status: SemestreStatusEnum = SemestreStatusEnum.PLANEJAMENTO
    ) -> Optional[Semestre]:
        """Create a new semester"""
        try:
            with DatabaseSession() as session:
                # Check if semester already exists
                existing = session.query(Semestre).filter(Semestre.nome == nome).first()
                if existing:
                    return None

                new_semestre = Semestre(nome=nome, status=status)
                session.add(new_semestre)
                session.flush()
                return new_semestre
        except Exception as e:
            print(f"Error creating semester: {e}")
            return None

    @classmethod
    def get_all_semestres(cls) -> List[Semestre]:
        """Get all semesters"""
        try:
            with DatabaseSession() as session:
                return session.query(Semestre).order_by(Semestre.nome.desc()).all()
        except Exception as e:
            print(f"Error getting semesters: {e}")
            return []

    @classmethod
    def get_semestre_by_id(cls, semestre_id: int) -> Optional[Semestre]:
        """Get semester by ID"""
        try:
            with DatabaseSession() as session:
                return (
                    session.query(Semestre).filter(Semestre.id == semestre_id).first()
                )
        except Exception as e:
            print(f"Error getting semester: {e}")
            return None

    @classmethod
    def get_current_semestre(cls) -> Optional[Semestre]:
        """Get the current/active semester"""
        try:
            with DatabaseSession() as session:
                # First try to find semester in EXECUCAO status
                semestre = (
                    session.query(Semestre)
                    .filter(Semestre.status == SemestreStatusEnum.EXECUCAO)
                    .first()
                )

                if semestre:
                    return semestre

                # If no EXECUCAO semester, find latest PLANEJAMENTO
                semestre = (
                    session.query(Semestre)
                    .filter(Semestre.status == SemestreStatusEnum.PLANEJAMENTO)
                    .order_by(Semestre.nome.desc())
                    .first()
                )

                return semestre
        except Exception as e:
            print(f"Error getting current semester: {e}")
            return None

    @classmethod
    def update_semestre_status(
        cls, semestre_id: int, status: SemestreStatusEnum
    ) -> Optional[Semestre]:
        """Update semester status"""
        try:
            with DatabaseSession() as session:
                semestre = (
                    session.query(Semestre).filter(Semestre.id == semestre_id).first()
                )
                if not semestre:
                    return None

                semestre.status = status
                return semestre
        except Exception as e:
            print(f"Error updating semester status: {e}")
            return None

    # DEMAND MANAGEMENT
    @classmethod
    def create_demanda(cls, demanda_data: DemandaCreate) -> Optional[Demanda]:
        """Create a new demand"""
        try:
            with DatabaseSession() as session:
                # Verify semester exists
                semestre = (
                    session.query(Semestre)
                    .filter(Semestre.id == demanda_data.semestre_id)
                    .first()
                )
                if not semestre:
                    return None

                # Validate SIGAA schedule
                if not validate_sigaa_schedule(demanda_data.horario_sigaa_bruto):
                    return None

                new_demanda = Demanda(
                    semestre_id=demanda_data.semestre_id,
                    codigo_disciplina=demanda_data.codigo_disciplina,
                    nome_disciplina=demanda_data.nome_disciplina,
                    professores_disciplina=demanda_data.professores_disciplina,
                    turma_disciplina=demanda_data.turma_disciplina,
                    vagas_disciplina=demanda_data.vagas_disciplina,
                    horario_sigaa_bruto=demanda_data.horario_sigaa_bruto,
                    nivel_disciplina=demanda_data.nivel_disciplina,
                )
                session.add(new_demanda)
                session.flush()
                return new_demanda
        except Exception as e:
            print(f"Error creating demand: {e}")
            return None

    @classmethod
    def get_demandas_by_semestre(cls, semestre_id: int) -> List[Demanda]:
        """Get all demands for a specific semester"""
        try:
            with DatabaseSession() as session:
                return (
                    session.query(Demanda)
                    .filter(Demanda.semestre_id == semestre_id)
                    .all()
                )
        except Exception as e:
            print(f"Error getting demands: {e}")
            return []

    @classmethod
    def get_demanda_by_id(cls, demanda_id: int) -> Optional[Demanda]:
        """Get demand by ID"""
        try:
            with DatabaseSession() as session:
                return session.query(Demanda).filter(Demanda.id == demanda_id).first()
        except Exception as e:
            print(f"Error getting demand: {e}")
            return None

    @classmethod
    def update_demanda(
        cls, demanda_id: int, demanda_data: DemandaUpdate
    ) -> Optional[Demanda]:
        """Update demand information"""
        try:
            with DatabaseSession() as session:
                demanda = (
                    session.query(Demanda).filter(Demanda.id == demanda_id).first()
                )
                if not demanda:
                    return None

                # Update fields if provided
                if demanda_data.nome_disciplina is not None:
                    demanda.nome_disciplina = demanda_data.nome_disciplina
                if demanda_data.professores_disciplina is not None:
                    demanda.professores_disciplina = demanda_data.professores_disciplina
                if demanda_data.turma_disciplina is not None:
                    demanda.turma_disciplina = demanda_data.turma_disciplina
                if demanda_data.vagas_disciplina is not None:
                    demanda.vagas_disciplina = demanda_data.vagas_disciplina
                if demanda_data.horario_sigaa_bruto is not None:
                    # Validate new schedule
                    if validate_sigaa_schedule(demanda_data.horario_sigaa_bruto):
                        demanda.horario_sigaa_bruto = demanda_data.horario_sigaa_bruto
                    else:
                        return None
                if demanda_data.nivel_disciplina is not None:
                    demanda.nivel_disciplina = demanda_data.nivel_disciplina

                return demanda
        except Exception as e:
            print(f"Error updating demand: {e}")
            return None

    @classmethod
    def delete_demanda(cls, demanda_id: int) -> bool:
        """Delete a demand"""
        try:
            with DatabaseSession() as session:
                demanda = (
                    session.query(Demanda).filter(Demanda.id == demanda_id).first()
                )
                if not demanda:
                    return False

                session.delete(demanda)
                return True
        except Exception as e:
            print(f"Error deleting demand: {e}")
            return False

    @classmethod
    def delete_semestre(cls, semestre_id: int) -> bool:
        """Delete a semester"""
        try:
            with DatabaseSession() as session:
                semestre = (
                    session.query(Semestre).filter(Semestre.id == semestre_id).first()
                )
                if not semestre:
                    return False

                # Check if semester has demands
                demandas_count = (
                    session.query(Demanda)
                    .filter(Demanda.semestre_id == semestre_id)
                    .count()
                )
                if demandas_count > 0:
                    return False

                session.delete(semestre)
                return True
        except Exception as e:
            print(f"Error deleting semester: {e}")
            return False

    # SCHEDULE PARSING AND ANALYSIS
    @classmethod
    def parse_demand_schedule(cls, demanda: Demanda) -> Dict[str, Any]:
        """Parse SIGAA schedule from a demand"""
        try:
            parsed_schedule = parse_sigaa_schedule(demanda.horario_sigaa_bruto)

            # Get day names for readability
            with DatabaseSession() as session:
                dias_semana = {
                    dia.id_sigaa: dia.nome for dia in session.query(DiaSemana).all()
                }

                # Enhance schedule with day names
                for item in parsed_schedule:
                    if "dia_semana_id" in item:
                        dia_id = item["dia_semana_id"]
                        item["dia_semana_nome"] = dias_semana.get(
                            dia_id, f"Dia {dia_id}"
                        )

            return {
                "demanda_id": demanda.id,
                "codigo_disciplina": demanda.codigo_disciplina,
                "nome_disciplina": demanda.nome_disciplina,
                "horario_original": demanda.horario_sigaa_bruto,
                "horario_parseado": parsed_schedule,
                "vagas": demanda.vagas_disciplina,
                "nivel": demanda.nivel_disciplina,
            }
        except Exception as e:
            print(f"Error parsing demand schedule: {e}")
            return {}

    @classmethod
    def get_schedule_conflicts(cls, semestre_id: int) -> List[Dict[str, Any]]:
        """Check for schedule conflicts in semester demands"""
        try:
            with DatabaseSession() as session:
                demandas = (
                    session.query(Demanda)
                    .filter(Demanda.semestre_id == semestre_id)
                    .all()
                )

                conflicts = []
                schedule_map = {}  # Map day_time -> list of demands

                for demanda in demandas:
                    try:
                        parsed = parse_sigaa_schedule(demanda.horario_sigaa_bruto)

                        for item in parsed:
                            key = f"{item['dia_semana_id']}_{item['codigo_bloco']}"

                            if key not in schedule_map:
                                schedule_map[key] = []

                            schedule_map[key].append(
                                {
                                    "demanda_id": demanda.id,
                                    "disciplina": demanda.codigo_disciplina,
                                    "nome_disciplina": demanda.nome_disciplina,
                                    "turma": demanda.turma_disciplina,
                                    "professor": demanda.professores_disciplina,
                                }
                            )
                    except Exception as e:
                        print(f"Error parsing schedule for demand {demanda.id}: {e}")

                # Find conflicts (same day_time for multiple demands)
                for key, items in schedule_map.items():
                    if len(items) > 1:
                        conflicts.append(
                            {
                                "dia_semana_id": key.split("_")[0],
                                "codigo_bloco": key.split("_")[1],
                                "conflitos": items,
                            }
                        )

                return conflicts
        except Exception as e:
            print(f"Error checking schedule conflicts: {e}")
            return []

    # STATISTICS AND REPORTING
    @classmethod
    def get_semester_statistics(cls, semestre_id: int) -> Dict[str, Any]:
        """Get comprehensive statistics for a semester"""
        try:
            with DatabaseSession() as session:
                # Get semester info
                semestre = (
                    session.query(Semestre).filter(Semestre.id == semestre_id).first()
                )
                if not semestre:
                    return {}

                # Get demands
                demandas = (
                    session.query(Demanda)
                    .filter(Demanda.semestre_id == semestre_id)
                    .all()
                )

                # Calculate statistics
                total_demandas = len(demandas)

                # Count by discipline level
                niveis = {}
                # Count by vacancy ranges
                vagas_ranges = {"0-20": 0, "21-40": 0, "41-60": 0, "61+": 0}
                # Count unique disciplines
                disciplinas_unicas = set()

                for demanda in demandas:
                    # Discipline level
                    nivel = demanda.nivel_disciplina or "Não especificado"
                    niveis[nivel] = niveis.get(nivel, 0) + 1

                    # Vacancy ranges
                    vagas = demanda.vagas_disciplina or 0
                    if vagas <= 20:
                        vagas_ranges["0-20"] += 1
                    elif vagas <= 40:
                        vagas_ranges["21-40"] += 1
                    elif vagas <= 60:
                        vagas_ranges["41-60"] += 1
                    else:
                        vagas_ranges["61+"] += 1

                    # Unique disciplines
                    if demanda.codigo_disciplina:
                        disciplinas_unicas.add(demanda.codigo_disciplina)

                # Get schedule conflicts
                conflicts = cls.get_schedule_conflicts(semestre_id)

                return {
                    "semestre": {
                        "id": semestre.id,
                        "nome": semestre.nome,
                        "status": semestre.status,
                    },
                    "demandas": {
                        "total": total_demandas,
                        "disciplinas_unicas": len(disciplinas_unicas),
                        "conflitos_horario": len(conflicts),
                    },
                    "distribuicao": {
                        "por_nivel": niveis,
                        "por_faixa_vagas": vagas_ranges,
                    },
                    "conflitos": conflicts[:5],  # Show first 5 conflicts
                }
        except Exception as e:
            print(f"Error getting semester statistics: {e}")
            return {}

    @classmethod
    def get_demandas_by_professor(cls, semestre_id: int) -> Dict[str, List[Demanda]]:
        """Group demands by professor for a semester"""
        try:
            with DatabaseSession() as session:
                demandas = (
                    session.query(Demanda)
                    .filter(Demanda.semestre_id == semestre_id)
                    .all()
                )

                professor_demandas = {}

                for demanda in demandas:
                    professors = demanda.professores_disciplina or "Não especificado"

                    # Handle multiple professors (comma separated)
                    professor_list = [p.strip() for p in professors.split(",")]

                    for professor in professor_list:
                        if professor not in professor_demandas:
                            professor_demandas[professor] = []
                        professor_demandas[professor].append(demanda)

                return professor_demandas
        except Exception as e:
            print(f"Error getting demands by professor: {e}")
            return {}

    @classmethod
    def get_capacity_requirements(cls, semestre_id: int) -> Dict[str, int]:
        """Get capacity requirements for all demands in a semester"""
        try:
            with DatabaseSession() as session:
                demandas = (
                    session.query(Demanda)
                    .filter(Demanda.semestre_id == semestre_id)
                    .all()
                )

                capacity_stats = {
                    "min_capacidade": 0,
                    "max_capacidade": 0,
                    "capacidade_total": 0,
                    "capacidade_media": 0,
                }

                if demandas:
                    capacities = [d.vagas_disciplina or 0 for d in demandas]
                    capacity_stats["min_capacidade"] = min(capacities)
                    capacity_stats["max_capacidade"] = max(capacities)
                    capacity_stats["capacidade_total"] = sum(capacities)
                    capacity_stats["capacidade_media"] = capacity_stats[
                        "capacidade_total"
                    ] // len(capacities)

                return capacity_stats
        except Exception as e:
            print(f"Error getting capacity requirements: {e}")
            return {}
