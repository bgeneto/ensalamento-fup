"""
Mock API service for Sistema de Ensalamento FUP/UnB
Simulates external data sources for development and testing
"""

import random
from typing import List, Dict, Any, Optional
from datetime import datetime, date, time
from models import Demanda, UsuarioCreate
from src.services.inventory_service import InventoryService
from src.services.auth_service import AuthService
from utils import parse_sigaa_schedule, validate_sigaa_schedule
from models import RoleEnum


class MockApiService:
    """Mock API service for simulating external data sources"""

    @staticmethod
    def generate_mock_disciplines() -> List[Dict[str, Any]]:
        """Generate mock discipline data for testing"""
        disciplines = [
            {
                "codigo": "FUP0001",
                "nome": "Fundamentos de Programação",
                "nivel": "Graduação",
                "vagas_recomendadas": 40,
                "tipo_sala_preferida": "Sala de Aula",
                "professores": ["João Silva", "Maria Santos"],
            },
            {
                "codigo": "FUP0002",
                "nome": "Cálculo I",
                "nivel": "Graduação",
                "vagas_recomendadas": 60,
                "tipo_sala_preferida": "Sala de Aula",
                "professores": ["Carlos Oliveira", "Ana Costa"],
            },
            {
                "codigo": "FUP0003",
                "nome": "Física Experimental",
                "nivel": "Graduação",
                "vagas_recomendadas": 30,
                "tipo_sala_preferida": "Laboratório",
                "professores": ["Roberto Mendes", "Laura Lima"],
            },
            {
                "codigo": "FUP0004",
                "nome": "Álgebra Linear",
                "nivel": "Graduação",
                "vagas_recomendadas": 50,
                "tipo_sala_preferida": "Sala de Aula",
                "professores": ["Pedro Alves", "Clara Gomes"],
            },
            {
                "codigo": "FUP0005",
                "nome": "Design de Interfaces",
                "nivel": "Graduação",
                "vagas_recomendadas": 25,
                "tipo_sala_preferida": "Laboratório de Informática",
                "professores": ["Thiago Silva", "Beatriz Costa"],
            },
            {
                "codigo": "FUP0006",
                "nome": "Química Orgânica",
                "nivel": "Graduação",
                "vagas_recomendadas": 35,
                "tipo_sala_preferida": "Laboratório",
                "professores": ["Fernanda Rocha", "Marcio Pereira"],
            },
        ]
        return disciplines

    @staticmethod
    def generate_mock_schedule_patterns() -> List[Dict[str, Any]]:
        """Generate mock SIGAA schedule patterns"""
        patterns = [
            {
                "descricao": "Aulas de segunda e quarta manhã",
                "horarios": ["24M12", "44M34", "24T12", "44T34"],
                "disciplinas_tipo": ["Teóricas"],
            },
            {
                "descricao": "Aulas de terça e quinta tarde",
                "horarios": ["35T23", "55T45", "35T56", "55T56"],
                "disciplinas_tipo": ["Teóricas", "Práticas"],
            },
            {
                "descricao": "Aulas de sexta noite",
                "horarios": ["65N12", "65N34"],
                "disciplinas_tipo": ["Teóricas"],
            },
            {
                "descricao": "Aulas laboratoriais segunda e quarta",
                "horarios": ["24M34", "44M56", "24T34", "44T56"],
                "disciplinas_tipo": ["Práticas", "Laboratoriais"],
            },
            {
                "descricao": "Aulas compactas sexta",
                "horarios": ["65M12", "65M23", "65M34", "65M45"],
                "disciplinas_tipo": ["Workshops", "Intensivas"],
            },
        ]
        return patterns

    @staticmethod
    def generate_mock_turmas() -> List[str]:
        """Generate mock class/turma names"""
        base_turmas = ["A", "B", "C", "D", "E"]
        return base_turmas

    @staticmethod
    def create_mock_demands(semestre_id: int, num_demands: int = 20) -> List[Demanda]:
        """Create mock demands for testing"""
        try:
            from database import DatabaseSession, Semestre

            with DatabaseSession() as session:
                # Verify semester exists
                semestre = (
                    session.query(Semestre).filter(Semestre.id == semestre_id).first()
                )
                if not semestre:
                    return []

                disciplines = MockApiService.generate_mock_disciplines()
                patterns = MockApiService.generate_mock_schedule_patterns()
                turmas = MockApiService.generate_mock_turmas()

                created_demands = []

                for i in range(min(num_demands, len(disciplines))):
                    discipline = disciplines[i]
                    pattern = random.choice(patterns)
                    turma = random.choice(turmas)
                    professor = random.choice(discipline["professores"])

                    # Create demand data - simplified without DemandaCreate for now
                    demanda_data = {
                        "semestre_id": semestre_id,
                        "codigo_disciplina": discipline["codigo"],
                        "nome_disciplina": discipline["nome"],
                        "professores_disciplina": professor,
                        "turma_disciplina": turma,
                        "vagas_disciplina": discipline["vagas_recomendadas"],
                        "horario_sigaa_bruto": " ".join(pattern["horarios"]),
                        "nivel_disciplina": discipline["nivel"],
                    }

                    # For now, return as mock data since we don't have Demanda model in database
                    created_demands.append(
                        Demanda(
                            id=i + 1,
                            semestre_id=semestre_id,
                            codigo_disciplina=discipline["codigo"],
                            nome_disciplina=discipline["nome"],
                            professores_disciplina=professor,
                            turma_disciplina=turma,
                            vagas_disciplina=discipline["vagas_recomendadas"],
                            horario_sigaa_bruto=" ".join(pattern["horarios"]),
                            nivel_disciplina=discipline["nivel"],
                            semestre=semestre,
                        )
                    )

                return created_demands

        except Exception as e:
            print(f"Error creating mock demands: {e}")
            return []

    @staticmethod
    def generate_mock_professors(num_professors: int = 10) -> List[UsuarioCreate]:
        """Generate mock professor users for testing"""
        first_names = [
            "João",
            "Maria",
            "Carlos",
            "Ana",
            "Pedro",
            "Clara",
            "Roberto",
            "Laura",
            "Thiago",
            "Beatriz",
        ]
        last_names = [
            "Silva",
            "Santos",
            "Oliveira",
            "Costa",
            "Alves",
            "Gomes",
            "Mendes",
            "Lima",
            "Rocha",
            "Pereira",
        ]

        professors = []

        for i in range(num_professors):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            username = f"{first_name.lower()}.{last_name.lower()}"

            professor = UsuarioCreate(
                username=username,
                password=f"temp{i:03d}",  # Temporary password
                nome_completo=f"{first_name} {last_name}",
                role=RoleEnum.PROFESSOR,
            )
            professors.append(professor)

        return professors

    @staticmethod
    def create_mock_professors() -> List[Dict[str, Any]]:
        """Create mock professors in the database"""
        try:
            professors_data = MockApiService.generate_mock_professors(8)
            created_professors = []

            for professor_data in professors_data:
                # Check if user already exists
                existing_user = AuthService.get_user_by_username(
                    professor_data.username
                )
                if not existing_user:
                    new_user = AuthService.create_user(
                        username=professor_data.username,
                        password=professor_data.password,
                        nome_completo=professor_data.nome_completo,
                        role=professor_data.role,
                    )
                    if new_user:
                        created_professors.append(
                            {
                                "username": professor_data.username,
                                "nome_completo": professor_data.nome_completo,
                                "senha_temp": professor_data.password,
                            }
                        )

            return created_professors

        except Exception as e:
            print(f"Error creating mock professors: {e}")
            return []

    @staticmethod
    def validate_sigaa_schedules(demands: List[Demanda]) -> Dict[str, Any]:
        """Validate SIGAA schedules in mock demands"""
        validation_results = {
            "total": len(demands),
            "valid": 0,
            "invalid": 0,
            "invalid_examples": [],
        }

        for demanda in demands:
            if validate_sigaa_schedule(demanda.horario_sigaa_bruto):
                validation_results["valid"] += 1
            else:
                validation_results["invalid"] += 1
                if len(validation_results["invalid_examples"]) < 3:
                    validation_results["invalid_examples"].append(
                        {
                            "disciplina": demanda.nome_disciplina,
                            "horario": demanda.horario_sigaa_bruto,
                        }
                    )

        return validation_results

    @staticmethod
    def generate_mock_allocation_report(semestre_id: int) -> Dict[str, Any]:
        """Generate a mock allocation report"""
        try:
            from database import DatabaseSession, Semestre

            with DatabaseSession() as session:
                semestre = (
                    session.query(Semestre).filter(Semestre.id == semestre_id).first()
                )
                if not semestre:
                    return {"error": "Semestre não encontrado"}

                # Get inventory stats
                stats = InventoryService.get_inventory_stats()

                # Generate mock allocation data
                total_demands = random.randint(15, 30)
                allocated_demands = random.randint(10, total_demands)
                allocation_rate = (
                    (allocated_demands / total_demands) * 100
                    if total_demands > 0
                    else 0
                )

                report = {
                    "semestre": semestre.nome,
                    "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "estatisticas": {
                        "total_salas": stats["salas"],
                        "total_predios": stats["predios"],
                        "total_campus": stats["campus"],
                        "capacidade_total": stats.get("capacidade_total", 0),
                    },
                    "alocacoes": {
                        "total_demandas": total_demands,
                        "alocadas": allocated_demands,
                        "nao_alocadas": total_demands - allocated_demands,
                        "taxa_alocacao": round(allocation_rate, 2),
                    },
                    "utilizacao": {
                        "salas_utilizadas": random.randint(5, stats["salas"]),
                        "horarios_utilizados": random.randint(20, 60),
                        "taxa_ocupacao": round(random.uniform(60, 85), 2),
                    },
                }

                return report

        except Exception as e:
            print(f"Error generating allocation report: {e}")
            return {"error": str(e)}

    @staticmethod
    def export_mock_data(format_type: str = "json") -> Dict[str, Any]:
        """Export mock data in specified format"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "disciplinas": MockApiService.generate_mock_disciplines(),
                "padroes_horario": MockApiService.generate_mock_schedule_patterns(),
                "turmas": MockApiService.generate_mock_turmas(),
            }

            if format_type.lower() == "json":
                return data
            elif format_type.lower() == "csv":
                # Convert to CSV-like format
                return {
                    "disciplines": [
                        {
                            "codigo": d["codigo"],
                            "nome": d["nome"],
                            "nivel": d["nivel"],
                            "vagas_recomendadas": d["vagas_recomendadas"],
                            "tipo_sala_preferida": d["tipo_sala_preferida"],
                        }
                        for d in data["disciplines"]
                    ]
                }
            else:
                return {"error": "Formato não suportado. Use 'json' ou 'csv'."}

        except Exception as e:
            print(f"Error exporting mock data: {e}")
            return {"error": str(e)}

    @staticmethod
    def simulate_room_availability(
        campus_id: Optional[int] = None, predio_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Simulate room availability for testing"""
        try:
            # Get rooms based on filters
            filters = {}
            if campus_id:
                filters["campus_id"] = campus_id
            if predio_id:
                filters["predio_id"] = predio_id

            rooms = (
                InventoryService.search_salas(filters)
                if filters
                else InventoryService.get_all_salas()
            )

            availability_data = []

            for room in rooms:
                # Generate random availability for current week
                availability = {
                    "sala_id": room.id,
                    "sala_nome": room.nome,
                    "sala_codigo": room.codigo,
                    "predio": room.predio.nome if room.predio else "Desconhecido",
                    "campus": (
                        room.predio.campus.nome
                        if room.predio and room.predio.campus
                        else "Desconhecido"
                    ),
                    "disponibilidade_semanal": {},
                }

                # Generate availability for each day and time block
                days = ["SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM"]
                time_blocks = [
                    "M1",
                    "M2",
                    "M3",
                    "M4",
                    "M5",
                    "M6",
                    "T1",
                    "T2",
                    "T3",
                    "T4",
                    "T5",
                    "T6",
                    "N1",
                    "N2",
                    "N3",
                    "N4",
                    "N5",
                    "N6",
                ]

                for day in days:
                    for time_block in time_blocks:
                        # Random availability (70% available)
                        is_available = random.random() > 0.3
                        availability["disponibilidade_semanal"][
                            f"{day}_{time_block}"
                        ] = is_available

                availability_data.append(availability)

            return {
                "data_geracao": datetime.now().isoformat(),
                "total_salas": len(availability_data),
                "disponibilidade": availability_data,
            }

        except Exception as e:
            print(f"Error simulating room availability: {e}")
            return {"error": str(e)}
