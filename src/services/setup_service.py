"""
Setup service for Sistema de Ensalamento FUP/UnB
Handles database initialization and seeding with initial data
"""

import json
import os
from datetime import time
from typing import List, Dict, Any
from database import (
    init_database,
    Campus,
    Predio,
    TipoSala,
    Caracteristica,
    DiaSemana,
    HorarioBloco,
    Semestre,
    DatabaseSession,
)
from models import SemestreStatusEnum
from config import (
    SIGAA_DAYS_MAPPING,
    SIGAA_TIME_BLOCKS,
    CAPACITY_TIERS,
    DEFAULT_ADMIN_USERNAME,
    DEFAULT_ADMIN_PASSWORD,
)


class SetupService:
    """Service class for database setup and initialization"""

    @staticmethod
    def initialize_database() -> bool:
        """Initialize database schema"""
        try:
            db_manager = init_database()
            return True
        except Exception as e:
            print(f"Error initializing database: {e}")
            return False

    @staticmethod
    def check_database_initialized() -> bool:
        """Check if database is properly initialized"""
        from src.services.database_service import DatabaseService

        return DatabaseService.check_database_exists()

    @staticmethod
    def seed_all_data() -> bool:
        """Seed all initial data into database"""
        try:
            success = True

            # Seed basic data
            success &= SetupService.seed_dias_semana()
            success &= SetupService.seed_horarios_bloco()
            success &= SetupService.seed_tipos_sala()
            success &= SetupService.seed_caracteristicas()
            success &= SetupService.seed_campus_e_predios()
            success &= SetupService.seed_semestre_inicial()

            return success
        except Exception as e:
            print(f"Error seeding database: {e}")
            return False

    @staticmethod
    def seed_dias_semana() -> bool:
        """Seed days of the week"""
        try:
            with DatabaseSession() as session:
                # Check if already seeded
                existing_count = session.query(DiaSemana).count()
                if existing_count > 0:
                    print("Days of week already seeded")
                    return True

                # Insert days according to SIGAA mapping
                for sigaa_id, nome in SIGAA_DAYS_MAPPING.items():
                    dia = DiaSemana(id_sigaa=sigaa_id, nome=nome)
                    session.add(dia)

                print(f"Seeded {len(SIGAA_DAYS_MAPPING)} days of week")
                return True
        except Exception as e:
            print(f"Error seeding days of week: {e}")
            return False

    @staticmethod
    def seed_horarios_bloco() -> bool:
        """Seed time blocks according to SIGAA schedule"""
        try:
            with DatabaseSession() as session:
                # Check if already seeded
                existing_count = session.query(HorarioBloco).count()
                if existing_count > 0:
                    print("Time blocks already seeded")
                    return True

                # Define time blocks with actual times
                time_blocks = [
                    # Morning blocks (M)
                    ("M1", "M", time(7, 0), time(7, 50)),
                    ("M2", "M", time(7, 50), time(8, 40)),
                    ("M3", "M", time(8, 50), time(9, 40)),
                    ("M4", "M", time(9, 40), time(10, 30)),
                    ("M5", "M", time(10, 40), time(11, 30)),
                    ("M6", "M", time(11, 30), time(12, 20)),
                    # Afternoon blocks (T)
                    ("T1", "T", time(13, 0), time(13, 50)),
                    ("T2", "T", time(13, 50), time(14, 40)),
                    ("T3", "T", time(14, 50), time(15, 40)),
                    ("T4", "T", time(15, 40), time(16, 30)),
                    ("T5", "T", time(16, 40), time(17, 30)),
                    ("T6", "T", time(17, 30), time(18, 20)),
                    # Night blocks (N)
                    ("N1", "N", time(18, 30), time(19, 20)),
                    ("N2", "N", time(19, 20), time(20, 10)),
                    ("N3", "N", time(20, 20), time(21, 10)),
                    ("N4", "N", time(21, 10), time(22, 0)),
                    ("N5", "N", time(22, 0), time(22, 50)),
                    ("N6", "N", time(22, 50), time(23, 40)),
                ]

                for codigo, turno, inicio, fim in time_blocks:
                    horario = HorarioBloco(
                        codigo_bloco=codigo,
                        turno=turno,
                        horario_inicio=inicio,
                        horario_fim=fim,
                    )
                    session.add(horario)

                print(f"Seeded {len(time_blocks)} time blocks")
                return True
        except Exception as e:
            print(f"Error seeding time blocks: {e}")
            return False

    @staticmethod
    def seed_tipos_sala() -> bool:
        """Seed room types"""
        try:
            with DatabaseSession() as session:
                # Check if already seeded
                existing_count = session.query(TipoSala).count()
                if existing_count > 0:
                    print("Room types already seeded")
                    return True

                # Define room types
                tipos_sala = [
                    ("Sala de Aula", "Sala tradicional para aulas teóricas"),
                    ("Laboratório", "Laboratório para aulas práticas"),
                    ("Auditório", "Grande auditório para palestras e eventos"),
                    ("Sala de Reunião", "Sala pequena para reuniões"),
                    (
                        "Sala de Videoconferência",
                        "Sala equipada para videoconferências",
                    ),
                    ("Laboratório de Informática", "Laboratório com computadores"),
                    ("Oficina", "Espaço para aulas práticas de engenharia/arquitetura"),
                    ("Estúdio", "Estúdio para aulas de artes/design"),
                    ("Biblioteca", "Espaço de estudo e pesquisa"),
                    ("Ginásio", "Espaço para aulas de educação física"),
                ]

                for nome, descricao in tipos_sala:
                    tipo = TipoSala(nome=nome, descricao=descricao)
                    session.add(tipo)

                print(f"Seeded {len(tipos_sala)} room types")
                return True
        except Exception as e:
            print(f"Error seeding room types: {e}")
            return False

    @staticmethod
    def seed_caracteristicas() -> bool:
        """Seed room characteristics"""
        try:
            with DatabaseSession() as session:
                # Check if already seeded
                existing_count = session.query(Caracteristica).count()
                if existing_count > 0:
                    print("Room characteristics already seeded")
                    return True

                # Define room characteristics
                caracteristicas = [
                    "Projetor",
                    "Ar Condicionado",
                    "Computador",
                    "Internet Wi-Fi",
                    "Quadro Branco",
                    "Quadro Negro",
                    "Acessibilidade",
                    "Cadeiras Fixas",
                    "Cadeiras Móveis",
                    "Mesa Professor",
                    "Armários",
                    "Tomadas Elétricas",
                    "Iluminação Natural",
                    "Ventilação Natural",
                    "Sistema de Som",
                    "Câmera",
                    "Microfone",
                    "Kit Multimídia",
                    "Lousa Digital",
                    "Extintor de Incêndio",
                ]

                for nome in caracteristicas:
                    caract = Caracteristica(nome=nome)
                    session.add(caract)

                print(f"Seeded {len(caracteristicas)} room characteristics")
                return True
        except Exception as e:
            print(f"Error seeding room characteristics: {e}")
            return False

    @staticmethod
    def seed_campus_e_predios() -> bool:
        """Seed campus and buildings"""
        try:
            with DatabaseSession() as session:
                # Check if already seeded
                existing_campus = session.query(Campus).count()
                if existing_campus > 0:
                    print("Campus and buildings already seeded")
                    return True

                # Create FUP Campus
                campus_fup = Campus(
                    nome="FUP - Faculdade UnB Planaltina",
                    descricao="Campus da Faculdade UnB Planaltina",
                )
                session.add(campus_fup)
                session.flush()  # Get the ID

                # Create buildings for FUP
                predios_fup = [
                    ("Bloco A", "Bloco principal de salas de aula"),
                    ("Bloco B", "Bloco de laboratórios"),
                    ("Bloco C", "Bloco administrativo"),
                    ("Bloco D", "Bloco de salas de aula e auditórios"),
                    ("Biblioteca", "Prédio da biblioteca"),
                    ("Ginásio", "Ginásio poliesportivo"),
                    ("Restaurante Universitário", "Restaurante universitário"),
                ]

                for nome, descricao in predios_fup:
                    predio = Predio(
                        nome=nome, descricao=descricao, campus_id=campus_fup.id
                    )
                    session.add(predio)

                # Create Darcy Ribeiro Campus (main UnB campus)
                campus_darcy = Campus(
                    nome="UnB Darcy Ribeiro",
                    descricao="Campus principal da Universidade de Brasília",
                )
                session.add(campus_darcy)
                session.flush()

                # Create some main buildings for Darcy Ribeiro
                predios_darcy = [
                    ("Pavilhão Anísio Teixeira", "Pavilhão de aulas"),
                    ("Pavilhão João Calmon", "Pavilhão de aulas"),
                    ("Instituto Central de Ciências", "Bloco de laboratórios"),
                    ("Faculdade de Educação", "Faculdade de Educação"),
                    ("Faculdade de Direito", "Faculdade de Direito"),
                ]

                for nome, descricao in predios_darcy:
                    predio = Predio(
                        nome=nome, descricao=descricao, campus_id=campus_darcy.id
                    )
                    session.add(predio)

                total_campus = 2
                total_predios = len(predios_fup) + len(predios_darcy)

                print(f"Seeded {total_campus} campuses and {total_predios} buildings")
                return True
        except Exception as e:
            print(f"Error seeding campus and buildings: {e}")
            return False

    @staticmethod
    def seed_semestre_inicial() -> bool:
        """Seed initial semester"""
        try:
            with DatabaseSession() as session:
                # Check if already seeded
                existing_count = session.query(Semestre).count()
                if existing_count > 0:
                    print("Semesters already seeded")
                    return True

                # Create current year semesters
                from datetime import datetime

                current_year = datetime.now().year

                # Check if we're in first or second half of year
                current_month = datetime.now().month
                if current_month <= 6:
                    # We're in first semester, create both current and next
                    semestres = [
                        (f"{current_year}.1", SemestreStatusEnum.EXECUCAO),
                        (f"{current_year}.2", SemestreStatusEnum.PLANEJAMENTO),
                        (f"{current_year + 1}.1", SemestreStatusEnum.PLANEJAMENTO),
                    ]
                else:
                    # We're in second semester, create current and next
                    semestres = [
                        (f"{current_year}.2", SemestreStatusEnum.EXECUCAO),
                        (f"{current_year + 1}.1", SemestreStatusEnum.PLANEJAMENTO),
                        (f"{current_year + 1}.2", SemestreStatusEnum.PLANEJAMENTO),
                    ]

                for nome, status in semestres:
                    semestre = Semestre(nome=nome, status=status)
                    session.add(semestre)

                print(f"Seeded {len(semestres)} semesters")
                return True
        except Exception as e:
            print(f"Error seeding semesters: {e}")
            return False

    @staticmethod
    def create_initial_admin() -> bool:
        """Create initial admin user"""
        try:
            # Import here to avoid circular imports
            from src.services.auth_service import AuthService

            # Check if admin already exists
            existing_admin = AuthService.get_user_by_username(DEFAULT_ADMIN_USERNAME)
            if existing_admin:
                print("Admin user already exists")
                return True

            # Create admin user
            admin_user = AuthService.create_user(
                username=DEFAULT_ADMIN_USERNAME,
                password=DEFAULT_ADMIN_PASSWORD,
                nome_completo="Administrador do Sistema",
                role="admin",
            )

            if admin_user:
                print(f"Created admin user: {DEFAULT_ADMIN_USERNAME}")
                return True
            else:
                print("Failed to create admin user")
                return False

        except Exception as e:
            print(f"Error creating initial admin: {e}")
            return False

    @staticmethod
    def reset_database() -> bool:
        """Reset entire database (use with caution!)"""
        try:
            # Drop all tables
            db_manager = init_database()
            db_manager.drop_tables()

            # Recreate tables
            db_manager.create_tables()

            # Seed all data
            return SetupService.seed_all_data()

        except Exception as e:
            print(f"Error resetting database: {e}")
            return False

    @staticmethod
    def get_setup_status() -> Dict[str, Any]:
        """Get current setup status"""
        try:
            from src.services.database_service import DatabaseService

            stats = DatabaseService.get_database_stats()

            # Calculate completion percentage
            total_items = 11  # Total number of items to check
            completed_items = 0

            # Check each essential item
            if stats.get("dias_semana", 0) >= 7:  # All 7 days seeded
                completed_items += 1

            if stats.get("horarios_bloco", 0) >= 18:  # All time blocks seeded
                completed_items += 1

            if stats.get("tipos_sala", 0) >= 5:  # At least 5 room types
                completed_items += 1

            if stats.get("caracteristicas", 0) >= 10:  # At least 10 characteristics
                completed_items += 1

            if stats.get("campus", 0) >= 1:  # At least 1 campus
                completed_items += 1

            if stats.get("predios", 0) >= 1:  # At least 1 building
                completed_items += 1

            if stats.get("semestres", 0) >= 1:  # At least 1 semester
                completed_items += 1

            if stats.get("usuarios", 0) >= 1:  # At least 1 user
                completed_items += 1

            # Basic functionality items
            if stats.get("salas", 0) >= 1:  # At least 1 room
                completed_items += 1

            if stats.get("regras", 0) >= 1:  # At least 1 rule
                completed_items += 1

            completion_percentage = (completed_items / total_items) * 100

            return {
                "is_initialized": SetupService.check_database_initialized(),
                "database_stats": stats,
                "completion_percentage": completion_percentage,
                "completed_items": completed_items,
                "total_items": total_items,
                "ready_for_use": completion_percentage >= 80,
            }

        except Exception as e:
            return {
                "is_initialized": False,
                "error": str(e),
                "completion_percentage": 0,
                "ready_for_use": False,
            }
