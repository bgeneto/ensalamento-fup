"""
Database initialization and migrations.
"""

import csv
from pathlib import Path
from sqlalchemy import text

from src.config.database import _engine
from src.models.base import Base
from src.models.inventory import (
    Campus,
    Predio,
    TipoSala,
    Sala,
    Caracteristica,
    sala_caracteristicas,
)
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
            {"nome": "2024-1", "status": 0},
            {"nome": "2024-2", "status": 0},
            {"nome": "2025-1", "status": 0},
            {"nome": "2025-2", "status": 0},
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
        campus_data = [
            {"nome": "FUP", "descricao": "Faculdade UnB Planaltina"},
            {"nome": "DARCY", "descricao": "Campus Darcy Ribeiro"},
        ]

        campus_map = {}
        for campus_info in campus_data:
            existing = (
                session.query(Campus).filter(Campus.nome == campus_info["nome"]).first()
            )
            if not existing:
                campus = Campus(**campus_info)
                session.add(campus)
                session.flush()
                campus_map[campus_info["nome"]] = campus
                print(f"  ✓ Added campus: {campus_info['nome']}")
            else:
                campus_map[campus_info["nome"]] = existing

        # Seed buildings (predios)
        predios_data = [
            {
                "nome": "UAC",
                "descricao": "Edifício Paulo Freire",
                "id": 1,
                "campus_nome": "FUP",  # Reference by campus name instead of campus.id
            },
            {
                "nome": "UEP",
                "descricao": "Edifício Cora Coralina",
                "id": 2,
                "campus_nome": "FUP",  # Reference by campus name instead of campus.id
            },
        ]

        predios_map = {}
        for predio_data in predios_data:
            existing = (
                session.query(Predio).filter(Predio.nome == predio_data["nome"]).first()
            )
            if not existing:
                # Create building - pass nome, descricao, and campus_id
                campus_nome = predio_data["campus_nome"]
                selected_campus = campus_map.get(campus_nome)
                if not selected_campus:
                    # Fallback to first available campus if mapping fails
                    selected_campus = next(iter(campus_map.values()))

                predio = Predio(
                    nome=predio_data["nome"],
                    descricao=predio_data["descricao"],
                    campus_id=selected_campus.id,
                )
                session.add(predio)
                session.flush()
                predios_map[predio_data["id"]] = predio
                print(f"  ✓ Added building: {predio_data['nome']} (id={predio.id})")
            else:
                predios_map[predio_data["id"]] = existing

        # Seed room types
        tipos_sala_data = [
            {"nome": "Auditório"},
            {"nome": "Sala de Aula"},
            {"nome": "Laboratório"},
            {"nome": "Laboratório de Física e Geologia"},
            {"nome": "Laboratório de Química"},
            {"nome": "Laboratório de Biologia"},
            {"nome": "Laboratório de Geologia"},
            {"nome": "Laboratório de Informática"},
            {"nome": "Laboratório de Matemática"},
            {"nome": "Laboratório de Linguagens e Artes"},
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

        # Seed room characteristics FIRST (before rooms, so caracteristicas_map works)
        caracteristicas_data = [
            {"nome": "Projetor"},
            {"nome": "Quadro Branco"},
            {"nome": "Quadro de Giz"},
            {"nome": "Acesso para Cadeirantes"},
            {"nome": "Ar Condicionado"},
            {"nome": "Ventilador"},
            {"nome": "Computadores"},
            {"nome": "Equipamento de Som"},
            {"nome": "Mesas Redondas"},
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

        # Flush to ensure characteristics are visible in database
        session.flush()

        # Get all Caracteristica records for mapping (now they exist!)
        caracteristicas_map = {
            carac.nome: carac for carac in session.query(Caracteristica).all()
        }

        # Seed rooms (salas) with detailed information
        salas_data = [
            {
                "nome": "AT-42/32",
                "descricao": "Lab. Mat.",
                "capacidade": 16,
                "andar": 0,
                "tipo_sala": "Laboratório de Matemática",
                "predio_id": 1,
                "caracteristicas": ["Mesas Redondas", "Ventilador"],
            },
            {
                "nome": "AT-42/12",
                "capacidade": 36,
                "andar": 0,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": ["Projetor", "Quadro Branco", "Ventilador"],
            },
            {
                "nome": "AT-48/20",
                "capacidade": 16,
                "andar": 0,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": ["Mesas Redondas"],
            },
            {
                "nome": "AT-48/22",
                "capacidade": 50,
                "andar": 0,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": [],
            },
            {
                "nome": "AT-42/30",
                "capacidade": 35,
                "andar": 0,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": [],
            },
            {
                "nome": "A1-42/8",
                "capacidade": 40,
                "andar": 1,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": ["Quadro de Giz", "Projetor", "Ventilador"],
            },
            {
                "nome": "A1-42/12",
                "capacidade": 30,
                "andar": 1,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": [],
            },
            {
                "nome": "A1-48/20",
                "capacidade": 50,
                "andar": 1,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": [],
            },
            {
                "nome": "A1-48/22",
                "capacidade": 50,
                "andar": 1,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": ["Quadro de Giz", "Projetor", "Ventilador"],
            },
            {
                "nome": "A1-42/30",
                "capacidade": 35,
                "andar": 1,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": [],
            },
            {
                "nome": "A1-48/32",
                "descricao": "Lab. Ling. Artes 1",
                "capacidade": 16,
                "andar": 1,
                "tipo_sala": "Laboratório de Linguagens e Artes",
                "predio_id": 1,
                "caracteristicas": [
                    "Mesas Redondas",
                    "Projetor",
                    "Ventilador",
                    "Quadro Branco",
                ],
            },
            {
                "nome": "A1-42/34",
                "capacidade": 30,
                "andar": 1,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": ["Quadro de Giz", "Projetor", "Ventilador"],
            },
            {
                "nome": "A1-48/40",
                "descricao": "Lab. Ling. Artes 2",
                "capacidade": 16,
                "andar": 1,
                "tipo_sala": "Laboratório de Linguagens e Artes",
                "predio_id": 1,
                "caracteristicas": [
                    "Mesas Redondas",
                    "Projetor",
                    "Ventilador",
                    "Quadro Branco",
                ],
            },
            {
                "nome": "A1-42/42",
                "capacidade": 30,
                "andar": 1,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": [],
            },
            {
                "nome": "A1-48/50",
                "capacidade": 50,
                "andar": 1,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": ["Quadro de Giz", "Projetor", "Ventilador"],
            },
            {
                "nome": "A1-48/52",
                "capacidade": 50,
                "andar": 1,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": [],
            },
            {
                "nome": "A1-42/60",
                "capacidade": 35,
                "andar": 1,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": [],
            },
            {
                "nome": "A1-42/62",
                "descricao": "Auditório 3",
                "capacidade": 80,
                "andar": 1,
                "tipo_sala": "Auditório",
                "predio_id": 1,
                "caracteristicas": ["Projetor", "Ventilador"],
            },
            {
                "nome": "A1-19/63",
                "capacidade": 40,
                "andar": 1,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": ["Projetor", "Quadro Branco", "Ventilador"],
            },
            {
                "nome": "A1-05/68",
                "descricao": "Auditório Augusto Boal",
                "capacidade": 150,
                "andar": 1,
                "tipo_sala": "Auditório",
                "predio_id": 1,
                "caracteristicas": [
                    "Projetor",
                    "Ar Condicionado",
                    "Equipamento de Som",
                ],
            },
            {
                "nome": "AT-79/11",
                "capacidade": 50,
                "andar": 0,
                "tipo_sala": "Sala de Aula",
                "predio_id": 2,
                "caracteristicas": [],
            },
            {
                "nome": "AT-53/26",
                "descricao": "Lab. Fís. Geo. 1",
                "capacidade": 40,
                "andar": 0,
                "tipo_sala": "Laboratório de Física e Geologia",
                "predio_id": 2,
                "caracteristicas": ["Ventilador", "Quadro Branco"],
            },
            {
                "nome": "AT-66/26",
                "descricao": "Lab. Fís. Geo. 2",
                "capacidade": 40,
                "andar": 0,
                "tipo_sala": "Laboratório de Física e Geologia",
                "predio_id": 2,
                "caracteristicas": ["Ventilador", "Quadro de Giz"],
            },
            {
                "nome": "A1-20/7",
                "descricao": "Lab. Bio. 2",
                "capacidade": 24,
                "andar": 1,
                "tipo_sala": "Laboratório de Biologia",
                "predio_id": 1,
                "caracteristicas": [],
            },
            {
                "nome": "A1-09/9",
                "descricao": "Lab. Bio. 1",
                "capacidade": 36,
                "andar": 1,
                "tipo_sala": "Laboratório de Biologia",
                "predio_id": 1,
                "caracteristicas": [],
            },
            {
                "nome": "AT-09/9",
                "descricao": "Lab. Quí. 2",
                "capacidade": 36,
                "andar": 0,
                "tipo_sala": "Laboratório de Química",
                "predio_id": 1,
                "caracteristicas": ["Ventilador"],
            },
            {
                "nome": "AT-22/7",
                "descricao": "Lab. Quí. 1",
                "capacidade": 40,
                "andar": 0,
                "tipo_sala": "Laboratório de Química",
                "predio_id": 1,
                "caracteristicas": ["Ventilador"],
            },
            {
                "nome": "A1-09/9",
                "capacidade": 50,
                "andar": 1,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": [],
            },
            {
                "nome": "AT-22/7",
                "capacidade": 50,
                "andar": 0,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": [],
            },
            {
                "nome": "AT-09/09",
                "capacidade": 50,
                "andar": 0,
                "tipo_sala": "Sala de Aula",
                "predio_id": 1,
                "caracteristicas": [],
            },
            {
                "nome": "AT-48/10",
                "descricao": "Lab. Info. 1",
                "capacidade": 22,
                "andar": 0,
                "tipo_sala": "Laboratório de Informática",
                "predio_id": 1,
                "caracteristicas": ["Computadores", "Projetor", "Ar Condicionado"],
            },
            {
                "nome": "A1-48/10",
                "descricao": "Lab. Info. 2",
                "capacidade": 25,
                "andar": 1,
                "tipo_sala": "Laboratório de Informática",
                "predio_id": 1,
                "caracteristicas": ["Computadores", "Projetor", "Ventilador"],
            },
            {
                "nome": "AT-25/26",
                "descricao": "Auditório Cora Coralina",
                "capacidade": 120,
                "andar": 0,
                "tipo_sala": "Auditório",
                "predio_id": 1,
                "caracteristicas": ["Computadores", "Projetor", "Ventilador"],
            },
            {
                "nome": "AT-78/46",
                "descricao": "Laboratório de Geoestatística e Geodésia",
                "capacidade": 1,  # Capacidade simbólica para evitar uso em aulas
                "andar": 0,
                "tipo_sala": "Laboratório",
                "predio_id": 2,
                "caracteristicas": [],
            },
            {
                "nome": "AT-78/46",
                "descricao": "Laboratório de Apoio e Pesquisa em Ensino de Ciências 2",
                "capacidade": 1,  # Capacidade simbólica para evitar uso em aulas
                "andar": 0,
                "tipo_sala": "Laboratório",
                "predio_id": 2,
                "caracteristicas": [],
            },
        ]

        # Get all TipoSala records for mapping
        tipos_sala_map = {tipo.nome: tipo for tipo in session.query(TipoSala).all()}

        for sala_info in salas_data:
            existing = (
                session.query(Sala).filter(Sala.nome == sala_info["nome"]).first()
            )
            if not existing:
                # Get the tipo_sala_id
                tipo_nome = sala_info["tipo_sala"]
                tipo_sala = tipos_sala_map.get(tipo_nome)
                if not tipo_sala:
                    # Fallback to Sala de Aula if tipo not found
                    tipo_sala = tipos_sala_map.get("Sala de Aula") or tipo_sala_ref

                selected_predio = predios_map.get(sala_info["predio_id"])
                if not selected_predio:
                    # Fallback to predio_id 1 if mapping fails
                    selected_predio = predios_map.get(1)
                    if not selected_predio:
                        # Fallback to first available predio if mapping fails
                        selected_predio = next(iter(predios_map.values()))

                sala = Sala(
                    nome=sala_info["nome"],
                    descricao=sala_info.get(
                        "descricao"
                    ),  # ADDED: Include descricao if provided
                    predio_id=(
                        selected_predio.id
                        if selected_predio
                        else next(iter(predios_map.values())).id
                    ),
                    tipo_sala_id=(
                        tipo_sala.id
                        if tipo_sala
                        else (tipo_sala_ref.id if tipo_sala_ref else 1)
                    ),
                    capacidade=sala_info["capacidade"],
                    andar=sala_info["andar"],
                )
                session.add(sala)
                session.flush()  # Flush to get the sala.id
                print(
                    f"  ✓ Added sala: {sala_info['nome']} (andar={sala_info['andar']}, capacidade={sala_info['capacidade']}, tipo={tipo_nome})"
                )
            else:
                sala = existing
                print(f"  → Sala already exists: {sala_info['nome']}")

            # Always check/create caracteristicas associations for this sala
            # (whether it was just created or already existed)
            if sala_info["caracteristicas"]:
                print(
                    f"    → Processing {len(sala_info['caracteristicas'])} characteristics for {sala_info['nome']}: {sala_info['caracteristicas']}"
                )

                # Check existing associations for this sala
                existing_associations = session.execute(
                    sala_caracteristicas.select().where(
                        sala_caracteristicas.c.sala_id == sala.id
                    )
                ).fetchall()
                existing_carac_ids = {
                    assoc.caracteristica_id for assoc in existing_associations
                }
                print(f"    → Found {len(existing_carac_ids)} existing associations")

                inserted_count = 0
                for carac_nome in sala_info["caracteristicas"]:
                    carac = caracteristicas_map.get(carac_nome)
                    if carac:
                        # Only create association if it doesn't already exist
                        if carac.id not in existing_carac_ids:
                            # Use manual insert with proper session management
                            insert_stmt = sala_caracteristicas.insert().values(
                                sala_id=sala.id, caracteristica_id=carac.id
                            )
                            session.execute(insert_stmt)
                            inserted_count += 1
                            print(
                                f"    ✓ Inserted: sala_id={sala.id}, caracteristica_id={carac.id} ({carac_nome})"
                            )
                        else:
                            print(
                                f"    → Association already exists for {carac_nome} on room {sala_info['nome']}"
                            )
                    else:
                        print(
                            f"    ⚠️ Characteristic '{carac_nome}' not found in map for room {sala_info['nome']}"
                        )
                print(f"    → Total inserted: {inserted_count}")
                if inserted_count > 0:
                    print(
                        f"    ✅ Added {inserted_count} characteristics to {sala_info['nome']}: {', '.join(sala_info['caracteristicas'])}"
                    )
            else:
                print(f"    → No characteristics defined for {sala_info['nome']}")

        session.flush()  # Flush all sala and association inserts

        # Seed admin users
        admin_users_data = [
            {
                "username": "admin",
                "nome_completo": "Administrador",
                "role": "admin",
            },
            {
                "username": "gestor",
                "nome_completo": "Gestor",
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

        # Update professor id=20 (Profa. Donária) to have baixa mobilidade
        professor = session.query(Professor).filter(Professor.id == 20).first()
        if professor:
            professor.tem_baixa_mobilidade = True
            print("  ✓ Updated professor id=20: tem_baixa_mobilidade = True")

        # Seed rule for FUP0246 to use room AT-22/7
        regra_data = {
            "id": 1,
            "descricao": "🔒 Obrigatório: Disciplina FUP0246 deve usar Laboratório de Química",
            "tipo_regra": "DISCIPLINA_TIPO_SALA",
            "config_json": '{"codigo_disciplina": "FUP0246", "tipo_sala_id": 5}',
            "prioridade": 0,
        }
        existing_regra = (
            session.query(Regra).filter(Regra.id == regra_data["id"]).first()
        )
        if not existing_regra:
            regra = Regra(**regra_data)
            session.add(regra)
            print(f"  ✓ Added rule: {regra_data['descricao']}")

        session.commit()
        print("✅ Database seeding completed successfully")


def run_sql_migrations(migrations_dir: str | None = None) -> None:
    """Run SQL migration files from a directory and record applied files.

    This is a lightweight runner for .sql files. It creates a table
    `schema_migrations(filename TEXT UNIQUE, applied_at TEXT)` and executes
    any .sql files not yet applied. Files are applied in sorted order.
    """
    from pathlib import Path

    print("Running SQL migrations...")

    base_dir = Path(__file__).parent
    mig_dir = Path(migrations_dir) if migrations_dir else base_dir / "migrations"
    if not mig_dir.exists() or not mig_dir.is_dir():
        print(f"  ⚠️  Migrations directory not found: {mig_dir}")
        return

    # Use raw DBAPI connection for executescript convenience (works for SQLite)
    raw_conn = _engine.raw_connection()
    try:
        cur = raw_conn.cursor()

        # ensure migrations tracking table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        # get applied filenames
        cur.execute("SELECT filename FROM schema_migrations")
        applied = {row[0] for row in cur.fetchall()}

        # collect .sql files sorted
        files = sorted([p for p in mig_dir.iterdir() if p.suffix == ".sql"])
        to_apply = [p for p in files if p.name not in applied]

        if not to_apply:
            print("  No new migrations to apply.")
            return

        for f in to_apply:
            print(f"  Applying migration: {f.name}")
            sql = f.read_text(encoding="utf-8")

            # Quick heuristic: if migration contains an ALTER TABLE ADD COLUMN,
            # check whether the column already exists and skip execution if so.
            skip_execution = False
            try:
                for line in sql.splitlines():
                    line_stripped = line.strip()
                    up = line_stripped.upper()
                    if up.startswith("ALTER TABLE") and "ADD COLUMN" in up:
                        # naive parse: tokens -> ALTER TABLE <table> ADD COLUMN <col>
                        parts = line_stripped.split()
                        # find table name (after ALTER TABLE)
                        try:
                            tbl_idx = [p.upper() for p in parts].index("TABLE") + 1
                            table_name = parts[tbl_idx].strip('"`')
                        except Exception:
                            continue

                        # find column name after ADD COLUMN
                        try:
                            add_idx = [p.upper() for p in parts].index("COLUMN") + 1
                            col_name = parts[add_idx].strip(',;"`')
                        except Exception:
                            # fallback: take next token after ADD
                            continue

                        # check pragma for existence
                        cur.execute(f"PRAGMA table_info({table_name});")
                        existing_cols = {r[1] for r in cur.fetchall()}
                        if col_name in existing_cols:
                            print(
                                f"    ⚠️ Column '{col_name}' already exists on '{table_name}', marking migration as applied and skipping execution."
                            )
                            cur.execute(
                                "INSERT OR IGNORE INTO schema_migrations(filename) VALUES (?)",
                                (f.name,),
                            )
                            raw_conn.commit()
                            skip_execution = True
                            break
            except Exception:
                # If any check fails, fall back to executing the script and letting sqlite report
                skip_execution = False

            if skip_execution:
                continue

            try:
                cur.executescript(sql)
                cur.execute(
                    "INSERT INTO schema_migrations(filename) VALUES (?)", (f.name,)
                )
                raw_conn.commit()
                print(f"    ✓ Applied {f.name}")
            except Exception as e:
                # Handle common sqlite duplicate-column error as applied
                msg = str(e).lower()
                if "duplicate column name" in msg or "already exists" in msg:
                    print(
                        f"    ⚠️ Migration {f.name} produced duplicate column or already exists error; recording as applied."
                    )
                    cur.execute(
                        "INSERT OR IGNORE INTO schema_migrations(filename) VALUES (?)",
                        (f.name,),
                    )
                    raw_conn.commit()
                    continue
                raw_conn.rollback()
                print(f"    ✗ Failed {f.name}: {e}")
                raise

        print("✅ SQL migrations completed")

    finally:
        try:
            cur.close()
        except Exception:
            pass
        raw_conn.close()
