"""
Test fixtures and configuration for all tests.
"""

import pytest
import os
from pathlib import Path

# Add src to path for imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.database import get_db_session
from src.db.migrations import init_db, drop_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def test_db():
    """
    Create a test database (in-memory SQLite).
    """
    # Use in-memory database for tests
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Create all tables
    from src.models.base import Base

    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_db):
    """
    Create a fresh database session for each test.
    """
    SessionLocal = sessionmaker(bind=test_db)
    session = SessionLocal()

    yield session

    # Cleanup - rollback and clear session
    session.rollback()
    session.expunge_all()
    session.close()


@pytest.fixture(scope="function")
def sample_campus(db_session):
    """
    Create a sample campus for testing.
    """
    from src.models.inventory import Campus

    # Generate unique name per test
    import time

    unique_name = f"Campus Central {int(time.time() * 1000000) % 1000000}"

    campus = Campus(nome=unique_name, descricao="Main campus")
    db_session.add(campus)
    db_session.commit()
    db_session.refresh(campus)

    return campus


@pytest.fixture
def sample_predio(db_session, sample_campus):
    """
    Create a sample building for testing.
    """
    from src.models.inventory import Predio

    predio = Predio(nome="Bloco A", campus_id=sample_campus.id)
    db_session.add(predio)
    db_session.commit()
    db_session.refresh(predio)

    return predio


@pytest.fixture
def sample_tipo_sala(db_session):
    """
    Create a sample room type for testing.
    """
    from src.models.inventory import TipoSala

    tipo = TipoSala(nome="Sala de Aula", descricao="Regular classroom")
    db_session.add(tipo)
    db_session.commit()
    db_session.refresh(tipo)

    return tipo


@pytest.fixture
def sample_sala(db_session, sample_predio, sample_tipo_sala):
    """
    Create a sample room for testing.
    """
    from src.models.inventory import Sala

    sala = Sala(
        nome="A101",
        predio_id=sample_predio.id,
        tipo_sala_id=sample_tipo_sala.id,
        capacidade=30,
        andar=1,
    )
    db_session.add(sala)
    db_session.commit()
    db_session.refresh(sala)

    return sala


@pytest.fixture
def sample_usuario(db_session):
    """
    Create a sample admin user for testing.

    NOTE: No password_hash here - passwords are stored in streamlit-authenticator
    YAML file, not in the database.
    """
    from src.models.academic import Usuario
    import time

    unique_id = int(time.time() * 1000000) % 1000000

    usuario = Usuario(
        username=f"admin{unique_id}",
        email=f"admin{unique_id}@fup.unb.br",
        nome_completo="Test Administrator",
        roles="admin",
        ativo=True,
    )
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)

    return usuario


@pytest.fixture
def sample_semestre(db_session):
    """
    Create a sample semester for testing.
    """
    from src.models.academic import Semestre

    semestre = Semestre(nome="2024.1", status="Planejamento")
    db_session.add(semestre)
    db_session.commit()
    db_session.refresh(semestre)

    return semestre


@pytest.fixture
def sample_professor(db_session):
    """
    Create a sample professor for testing.
    """
    from src.models.academic import Professor

    prof = Professor(
        nome_completo="Prof. João Silva",
        tem_baixa_mobilidade=False,
        username_login="joao.silva",
    )
    db_session.add(prof)
    db_session.commit()
    db_session.refresh(prof)

    return prof


@pytest.fixture
def sample_demanda(db_session, sample_semestre):
    """
    Create a sample demand for testing.
    """
    from src.models.academic import Demanda

    demanda = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="COMP001",
        nome_disciplina="Programação I",
        professores_disciplina="Prof. João Silva",
        horario_sigaa_bruto="M1;M2;SEG",
        nao_alocar=False,
    )
    db_session.add(demanda)
    db_session.commit()
    db_session.refresh(demanda)

    return demanda


@pytest.fixture
def sample_dia_semana(db_session):
    """
    Create a sample weekday for testing.
    """
    from src.models.horario import DiaSemana

    dia = DiaSemana(id_sigaa=2, nome="SEG")
    db_session.add(dia)
    db_session.commit()
    db_session.refresh(dia)

    return dia


@pytest.fixture
def sample_horario_bloco(db_session):
    """
    Create a sample time block for testing.
    """
    from src.models.horario import HorarioBloco

    horario = HorarioBloco(
        codigo_bloco="M1", turno="M", horario_inicio="08:00", horario_fim="09:50"
    )
    db_session.add(horario)
    db_session.commit()
    db_session.refresh(horario)

    return horario
