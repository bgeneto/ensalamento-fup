"""
Database initialization and migrations.
"""

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
                "horario_fim": "09:50",
            },
            {
                "codigo_bloco": "M2",
                "turno": "M",
                "horario_inicio": "10:00",
                "horario_fim": "11:50",
            },
            {
                "codigo_bloco": "M3",
                "turno": "M",
                "horario_inicio": "12:00",
                "horario_fim": "13:50",
            },
            {
                "codigo_bloco": "M4",
                "turno": "M",
                "horario_inicio": "14:00",
                "horario_fim": "15:50",
            },
            {
                "codigo_bloco": "M5",
                "turno": "M",
                "horario_inicio": "16:00",
                "horario_fim": "17:50",
            },
            # Afternoon (T1-T6)
            {
                "codigo_bloco": "T1",
                "turno": "T",
                "horario_inicio": "08:00",
                "horario_fim": "09:50",
            },
            {
                "codigo_bloco": "T2",
                "turno": "T",
                "horario_inicio": "10:00",
                "horario_fim": "11:50",
            },
            {
                "codigo_bloco": "T3",
                "turno": "T",
                "horario_inicio": "12:00",
                "horario_fim": "13:50",
            },
            {
                "codigo_bloco": "T4",
                "turno": "T",
                "horario_inicio": "14:00",
                "horario_fim": "15:50",
            },
            {
                "codigo_bloco": "T5",
                "turno": "T",
                "horario_inicio": "16:00",
                "horario_fim": "17:50",
            },
            {
                "codigo_bloco": "T6",
                "turno": "T",
                "horario_inicio": "18:00",
                "horario_fim": "19:50",
            },
            # Night (N1-N4)
            {
                "codigo_bloco": "N1",
                "turno": "N",
                "horario_inicio": "18:00",
                "horario_fim": "19:50",
            },
            {
                "codigo_bloco": "N2",
                "turno": "N",
                "horario_inicio": "20:00",
                "horario_fim": "21:50",
            },
            {
                "codigo_bloco": "N3",
                "turno": "N",
                "horario_inicio": "22:00",
                "horario_fim": "23:50",
            },
            {
                "codigo_bloco": "N4",
                "turno": "N",
                "horario_inicio": "21:00",
                "horario_fim": "22:50",
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

        # Seed room types
        tipos_sala_data = [
            {"nome": "Sala de Aula", "descricao": "Regular classroom"},
            {"nome": "Laboratório", "descricao": "Laboratory"},
            {"nome": "Auditório", "descricao": "Auditorium"},
            {"nome": "Sala de Seminário", "descricao": "Seminar room"},
            {"nome": "Laboratório de Informática", "descricao": "Computer lab"},
        ]

        for tipo_data in tipos_sala_data:
            existing = (
                session.query(TipoSala)
                .filter(TipoSala.nome == tipo_data["nome"])
                .first()
            )
            if not existing:
                tipo = TipoSala(**tipo_data)
                session.add(tipo)
                print(f"  ✓ Added room type: {tipo_data['nome']}")

        # Seed room characteristics
        caracteristicas_data = [
            {"nome": "Projetor"},
            {"nome": "Quadro Branco"},
            {"nome": "Quadro Negro"},
            {"nome": "Acesso para Cadeirantes"},
            {"nome": "Ar Condicionado"},
            {"nome": "Computadores"},
            {"nome": "Equipamento de Som"},
            {"nome": "Câmera"},
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
                "email": "admin@fup.unb.br",
                "nome_completo": "Administrador Sistema",
                "roles": "admin",
                "ativo": True,
            },
            {
                "username": "gestor",
                "email": "gestor@fup.unb.br",
                "nome_completo": "Gestor de Alocação",
                "roles": "admin",
                "ativo": True,
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

        session.commit()
        print("✅ Database seeding completed successfully")
