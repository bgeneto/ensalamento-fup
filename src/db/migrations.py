"""
Database initialization and migrations.
"""

import csv
from pathlib import Path
from sqlalchemy import text

from src.config.database import _engine
from src.models.base import Base
from src.models.inventory import Campus, Predio, TipoSala, Sala, Caracteristica
from src.models.horario import DiaSemana, HorarioBloco
from src.models.academic import Semestre, Demanda, Professor, Usuario
from src.models.allocation import Regra, AlocacaoSemestral, ReservaEsporadica


def init_db():
    """
    Initialize database - create all tables.
    """
    print("Creating database tables...")
    Base.metadata.create_all(bind=_engine)
    print("✅ Database tables created successfully")


def drop_db():
    """
    Drop all tables (useful for development/testing).
    """
    print("Dropping all database tables...")
    Base.metadata.drop_all(bind=_engine)
    print("✅ All tables dropped")


def load_professors_from_csv(session):
    """
    Load professors from CSV file: docs/professores-fup.csv

    CSV format:
        username_login;nome_completo

    Args:
        session: SQLAlchemy database session
    """
    csv_path = Path(__file__).parent.parent.parent / "docs" / "professores-fup.csv"

    if not csv_path.exists():
        print(f"  ⚠️  CSV file not found: {csv_path}")
        return

    print(f"\n  Loading professors from {csv_path.name}...")

    count = 0
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            username = row.get("username_login", "").strip()
            nome_completo = row.get("nome_completo", "").strip()

            # Skip empty rows
            if not username or not nome_completo:
                continue

            # Check if professor already exists
            existing = (
                session.query(Professor)
                .filter(Professor.username_login == username)
                .first()
            )

            if not existing:
                professor = Professor(
                    nome_completo=nome_completo,
                    username_login=username,
                    tem_baixa_mobilidade=False,
                )
                session.add(professor)
                count += 1

    if count > 0:
        session.flush()
        print(f"  ✓ Added {count} professors from CSV")


def seed_db():
    """
    Seed database with initial data (time blocks, weekdays).
    """
    from src.config.database import get_db_session

    print("Seeding database with initial data...")

    with get_db_session() as session:
        # Seed dias_semana (weekdays)
        dias_data = [
            {"id_sigaa": 2, "nome": "SEG"},  # Monday
            {"id_sigaa": 3, "nome": "TER"},  # Tuesday
            {"id_sigaa": 4, "nome": "QUA"},  # Wednesday
            {"id_sigaa": 5, "nome": "QUI"},  # Thursday
            {"id_sigaa": 6, "nome": "SEX"},  # Friday
            {"id_sigaa": 7, "nome": "SAB"},  # Saturday
        ]

        for dia_data in dias_data:
            existing = (
                session.query(DiaSemana)
                .filter(DiaSemana.id_sigaa == dia_data["id_sigaa"])
                .first()
            )
            if not existing:
                dia = DiaSemana(**dia_data)
                session.add(dia)
                print(f"  ✓ Added {dia_data['nome']} (id_sigaa={dia_data['id_sigaa']})")

        # Seed horarios_bloco (time blocks)
        horarios_data = [
            # Morning (M1-M5)
            {
                "codigo_bloco": "M1",
                "turno": "M",
                "horario_inicio": "08:00",
                "horario_fim": "08:55",
            },
            {
                "codigo_bloco": "M2",
                "turno": "M",
                "horario_inicio": "08:55",
                "horario_fim": "09:50",
            },
            {
                "codigo_bloco": "M3",
                "turno": "M",
                "horario_inicio": "10:00",
                "horario_fim": "10:55",
            },
            {
                "codigo_bloco": "M4",
                "turno": "M",
                "horario_inicio": "10:55",
                "horario_fim": "11:50",
            },
            {
                "codigo_bloco": "M5",
                "turno": "M",
                "horario_inicio": "12:00",
                "horario_fim": "12:55",
            },
            # Afternoon (T1-T6)
            {
                "codigo_bloco": "T1",
                "turno": "T",
                "horario_inicio": "12:55",
                "horario_fim": "13:50",
            },
            {
                "codigo_bloco": "T2",
                "turno": "T",
                "horario_inicio": "14:00",
                "horario_fim": "14:55",
            },
            {
                "codigo_bloco": "T3",
                "turno": "T",
                "horario_inicio": "14:55",
                "horario_fim": "15:50",
            },
            {
                "codigo_bloco": "T4",
                "turno": "T",
                "horario_inicio": "16:00",
                "horario_fim": "16:55",
            },
            {
                "codigo_bloco": "T5",
                "turno": "T",
                "horario_inicio": "16:55",
                "horario_fim": "17:50",
            },
            {
                "codigo_bloco": "T6",
                "turno": "T",
                "horario_inicio": "18:00",
                "horario_fim": "18:55",
            },         
            # Night (N1-N4)
            {
                "codigo_bloco": "N1",
                "turno": "N",
                "horario_inicio": "19:00",
                "horario_fim": "19:50",
            },
            {
                "codigo_bloco": "N2",
                "turno": "N",
                "horario_inicio": "19:50",
                "horario_fim": "20:40",
            },
            {
                "codigo_bloco": "N3",
                "turno": "N",
                "horario_inicio": "20:50",
                "horario_fim": "21:40",
            },
            {
                "codigo_bloco": "N4",
                "turno": "N",
                "horario_inicio": "21:40",
                "horario_fim": "22:30",
            },
        ]

        for horario_data in horarios_data:
            existing = (
                session.query(HorarioBloco)
                .filter(HorarioBloco.codigo_bloco == horario_data["codigo_bloco"])
                .first()
            )
            if not existing:
                horario = HorarioBloco(**horario_data)
                session.add(horario)
                print(
                    f"  ✓ Added time block {horario_data['codigo_bloco']} "
                    f"({horario_data['horario_inicio']}-{horario_data['horario_fim']})"
                )

        # Seed semestres (academic terms)
        semestres_data = [
            {"nome": "2024-1", "status": "Encerrado"},
            {"nome": "2024-2", "status": "Encerrado"},
            {"nome": "2025-1", "status": "Encerrado"},
            {"nome": "2025-2", "status": "Ativo"},
            {"nome": "2026-1", "status": "Planejamento"},
        ]

        for semestre_data in semestres_data:
            existing = (
                session.query(Semestre)
                .filter(Semestre.nome == semestre_data["nome"])
                .first()
            )
            if not existing:
                semestre = Semestre(**semestre_data)
                session.add(semestre)
                print(
                    f"  ✓ Added semester: {semestre_data['nome']} (status={semestre_data['status']})"
                )

        # Seed campuses
        campus_data = {"nome": "FUP", "descricao": "Faculdade UnB Planaltina"}

        campus = session.query(Campus).filter(Campus.nome == "FUP").first()
        if not campus:
            campus = Campus(**campus_data)
            session.add(campus)
            session.flush()
            print(f"  ✓ Added campus: {campus_data['nome']}")

        # Seed buildings (predios)
        predio_data = {"nome": "UAC", "campus_id": campus.id}

        predio = (
            session.query(Predio)
            .filter(Predio.campus_id == campus.id, Predio.nome == "UAC")
            .first()
        )
        if not predio:
            predio = Predio(**predio_data)
            session.add(predio)
            session.flush()
            print(f"  ✓ Added building: {predio_data['nome']}")

        # Seed room types
        tipos_sala_data = [
            {"nome": "Auditório", "descricao": "Auditório"},
            {"nome": "Sala de Aula", "descricao": "Sala de aula regular"},
            {"nome": "Laboratório de Física", "descricao": "Laboratório de Física"},
            {"nome": "Laboratório de Química", "descricao": "Laboratório de Química"},
            {"nome": "Laboratório de Biologia", "descricao": "Laboratório de Biologia"},
            {"nome": "Laboratório de Informática", "descricao": "Laboratório de Informática"},
            {"nome": "Sala de Seminário", "descricao": "Sala de Seminário"},
        ]

        tipo_sala_ref = None
        for tipo_data in tipos_sala_data:
            existing = (
                session.query(TipoSala)
                .filter(TipoSala.nome == tipo_data["nome"])
                .first()
            )
            if not existing:
                tipo = TipoSala(**tipo_data)
                session.add(tipo)
                session.flush()
                if tipo_data["nome"] == "Sala de Aula":
                    tipo_sala_ref = tipo
                print(f"  ✓ Added room type: {tipo_data['nome']}")
            elif tipo_data["nome"] == "Sala de Aula":
                tipo_sala_ref = existing

        # Seed rooms (salas)
        salas_data = [
            "A1-09/9",
            "AT-22/7",
            "AT-09/09",
            "AT-48/10",
            "A1-48/10",
            "A1-19/63",
            "A1-42/62",
            "A1-42/60",
            "A1-48/52",
            "A1-48/50",
            "A1-42/42",
            "A1-48/40",
            "A1-42/34",
            "A1-48/32",
            "A1-42/30",
            "A1-48/22",
            "A1-48/20",
            "A1-42/12",
            "A1-42/8",
            "AT-42/30",
            "AT-48/22",
            "AT-48/20",
            "AT-42/12",
        ]

        for sala_nome in salas_data:
            existing = session.query(Sala).filter(Sala.nome == sala_nome).first()
            if not existing:
                # Parse floor from prefix (A1 = 1st floor, AT = ground floor)
                andar = "1" if sala_nome.startswith("A1") else "0"
                sala = Sala(
                    nome=sala_nome,
                    predio_id=predio.id,
                    tipo_sala_id=tipo_sala_ref.id if tipo_sala_ref else 1,
                    capacidade=50,
                    andar=andar,
                    tipo_assento="carteira",
                )
                session.add(sala)
                print(f"  ✓ Added sala: {sala_nome} (andar={andar}, capacidade=50)")

        session.flush()

        # Seed room characteristics
        caracteristicas_data = [
            {"nome": "Projetor"},
            {"nome": "Quadro Branco"},
            {"nome": "Quadro de Giz"},
            {"nome": "Acesso para Cadeirantes"},
            {"nome": "Ar Condicionado"},
            {"nome": "Ventilador"},
            {"nome": "Computadores"},
            {"nome": "Equipamento de Som"},
        ]

        for carac_data in caracteristicas_data:
            existing = (
                session.query(Caracteristica)
                .filter(Caracteristica.nome == carac_data["nome"])
                .first()
            )
            if not existing:
                carac = Caracteristica(**carac_data)
                session.add(carac)
                print(f"  ✓ Added characteristic: {carac_data['nome']}")

        # Seed admin users
        admin_users_data = [
            {
                "username": "admin",
                "nome_completo": "Administrador do Sistema",
                "role": "admin",
            },
            {
                "username": "gestor",
                "nome_completo": "Gestor de Alocação",
                "role": "admin",
            },
        ]

        for admin_data in admin_users_data:
            existing = (
                session.query(Usuario)
                .filter(Usuario.username == admin_data["username"])
                .first()
            )
            if not existing:
                usuario = Usuario(**admin_data)
                session.add(usuario)
                print(f"  ✓ Added admin user: {admin_data['username']}")

        # Seed professors from CSV file
        load_professors_from_csv(session)

        session.commit()
        print("✅ Database seeding completed successfully")
