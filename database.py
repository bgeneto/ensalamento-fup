"""
Database setup and SQLAlchemy models for Sistema de Ensalamento FUP/UnB
"""

import os
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    Time,
    Date,
    ForeignKey,
    UniqueConstraint,
    Boolean,
    func,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.pool import StaticPool
from config import DATABASE_URL

Base = declarative_base()


# Physical Structure Models
class Campus(Base):
    """Campus SQLAlchemy model"""

    __tablename__ = "campus"

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, unique=True)
    descricao = Column(Text)

    # Relationships
    predios = relationship("Predio", back_populates="campus")

    def __repr__(self):
        return f"<Campus(id={self.id}, nome='{self.nome}')>"


class Predio(Base):
    """Building SQLAlchemy model"""

    __tablename__ = "predios"

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, unique=True)
    campus_id = Column(Integer, ForeignKey("campus.id"), nullable=False)

    # Relationships
    campus = relationship("Campus", back_populates="predios")
    salas = relationship("Sala", back_populates="predio")

    def __repr__(self):
        return f"<Predio(id={self.id}, nome='{self.nome}', campus_id={self.campus_id})>"


class TipoSala(Base):
    """Room type SQLAlchemy model"""

    __tablename__ = "tipos_sala"

    id = Column(Integer, primary_key=True)
    nome = Column(String(50), nullable=False, unique=True)
    descricao = Column(Text)

    # Relationships
    salas = relationship("Sala", back_populates="tipo_sala")

    def __repr__(self):
        return f"<TipoSala(id={self.id}, nome='{self.nome}')>"


class Caracteristica(Base):
    """Room characteristic SQLAlchemy model"""

    __tablename__ = "caracteristicas"

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, unique=True)

    # Relationships
    salas = relationship(
        "Sala", secondary="sala_caracteristicas", back_populates="caracteristicas"
    )

    def __repr__(self):
        return f"<Caracteristica(id={self.id}, nome='{self.nome}')>"


class Sala(Base):
    """Room SQLAlchemy model"""

    __tablename__ = "salas"

    id = Column(Integer, primary_key=True)
    nome = Column(String(50), nullable=False)
    predio_id = Column(Integer, ForeignKey("predios.id"), nullable=False)
    tipo_sala_id = Column(Integer, ForeignKey("tipos_sala.id"), nullable=False)
    capacidade = Column(Integer, default=0)
    andar = Column(String(10))
    tipo_assento = Column(String(50))

    # Relationships
    predio = relationship("Predio", back_populates="salas")
    tipo_sala = relationship("TipoSala", back_populates="salas")
    caracteristicas = relationship(
        "Caracteristica", secondary="sala_caracteristicas", back_populates="salas"
    )
    alocacoes_semestrais = relationship("AlocacaoSemestral", back_populates="sala")
    reservas_esporadicas = relationship("ReservaEsporadica", back_populates="sala")

    # Unique constraint on room name and building
    __table_args__ = (UniqueConstraint("nome", "predio_id", name="uq_nome_predio"),)

    def __repr__(self):
        return f"<Sala(id={self.id}, nome='{self.nome}', predio_id={self.predio_id}, capacidade={self.capacidade})>"


# Association table for room characteristics
class SalaCaracteristica(Base):
    """Room-characteristic association table"""

    __tablename__ = "sala_caracteristicas"

    sala_id = Column(Integer, ForeignKey("salas.id"), primary_key=True)
    caracteristica_id = Column(
        Integer, ForeignKey("caracteristicas.id"), primary_key=True
    )

    # Relationships
    sala = relationship("Sala", back_populates="caracteristicas")
    caracteristica = relationship("Caracteristica", back_populates="salas")

    def __repr__(self):
        return f"<SalaCaracteristica(sala_id={self.sala_id}, caracteristica_id={self.caracteristica_id})>"


# Time Models
class DiaSemana(Base):
    """Day of week SQLAlchemy model"""

    __tablename__ = "dias_semana"

    id_sigaa = Column(Integer, primary_key=True)
    nome = Column(String(10), nullable=False, unique=True)

    # Relationships
    alocacoes_semestrais = relationship(
        "AlocacaoSemestral", back_populates="dia_semana"
    )

    def __repr__(self):
        return f"<DiaSemana(id_sigaa={self.id_sigaa}, nome='{self.nome}')>"


class HorarioBloco(Base):
    """Time block SQLAlchemy model"""

    __tablename__ = "horarios_bloco"

    codigo_bloco = Column(String(3), primary_key=True)
    turno = Column(String(1), nullable=False)
    horario_inicio = Column(Time, nullable=False)
    horario_fim = Column(Time, nullable=False)

    # Relationships
    alocacoes_semestrais = relationship(
        "AlocacaoSemestral", back_populates="horario_bloco"
    )
    reservas_esporadicas = relationship(
        "ReservaEsporadica", back_populates="horario_bloco"
    )

    def __repr__(self):
        return f"<HorarioBloco(codigo='{self.codigo_bloco}', turno='{self.turno}', inicio='{self.horario_inicio}')>"


# Academic Models
class Semestre(Base):
    """Semester SQLAlchemy model"""

    __tablename__ = "semestres"

    id = Column(Integer, primary_key=True)
    nome = Column(String(10), nullable=False, unique=True)
    status = Column(String(20), default="Planejamento")

    # Relationships
    demandas = relationship("Demanda", back_populates="semestre")

    def __repr__(self):
        return f"<Semestre(id={self.id}, nome='{self.nome}', status='{self.status}')>"


class Demanda(Base):
    """Demand SQLAlchemy model"""

    __tablename__ = "demandas"

    id = Column(Integer, primary_key=True)
    semestre_id = Column(Integer, ForeignKey("semestres.id"), nullable=False)
    codigo_disciplina = Column(String(20), nullable=False)
    nome_disciplina = Column(String(200))
    professores_disciplina = Column(String(500))
    turma_disciplina = Column(String(20))
    vagas_disciplina = Column(Integer)
    horario_sigaa_bruto = Column(String(50), nullable=False)
    nivel_disciplina = Column(String(50))

    # Relationships
    semestre = relationship("Semestre", back_populates="demandas")
    alocacoes_semestrais = relationship("AlocacaoSemestral", back_populates="demanda")

    def __repr__(self):
        return f"<Demanda(id={self.id}, disciplina='{self.codigo_disciplina}', turma='{self.turma_disciplina}')>"


# Rule Models
class Regra(Base):
    """Allocation rule SQLAlchemy model"""

    __tablename__ = "regras"

    id = Column(Integer, primary_key=True)
    descricao = Column(String(500), nullable=False)
    tipo_regra = Column(String(50), nullable=False)
    config_json = Column(Text, nullable=False)
    prioridade = Column(Integer, default=1)

    def __repr__(self):
        return f"<Regra(id={self.id}, tipo='{self.tipo_regra}', prioridade={self.prioridade})>"


# Allocation Models
class AlocacaoSemestral(Base):
    """Semester allocation SQLAlchemy model"""

    __tablename__ = "alocacoes_semestrais"

    id = Column(Integer, primary_key=True)
    demanda_id = Column(Integer, ForeignKey("demandas.id"), nullable=False)
    sala_id = Column(Integer, ForeignKey("salas.id"), nullable=False)
    dia_semana_id = Column(Integer, ForeignKey("dias_semana.id_sigaa"), nullable=False)
    codigo_bloco = Column(
        String(3), ForeignKey("horarios_bloco.codigo_bloco"), nullable=False
    )

    # Relationships
    demanda = relationship("Demanda", back_populates="alocacoes_semestrais")
    sala = relationship("Sala", back_populates="alocacoes_semestrais")
    dia_semana = relationship("DiaSemana", back_populates="alocacoes_semestrais")
    horario_bloco = relationship("HorarioBloco", back_populates="alocacoes_semestrais")

    def __repr__(self):
        return f"<AlocacaoSemestral(id={self.id}, sala_id={self.sala_id}, dia={self.dia_semana_id}, bloco='{self.codigo_bloco}')>"


# Reservation Models
class ReservaEsporadica(Base):
    """Sporadic reservation SQLAlchemy model"""

    __tablename__ = "reservas_esporadicas"

    id = Column(Integer, primary_key=True)
    sala_id = Column(Integer, ForeignKey("salas.id"), nullable=False)
    username_solicitante = Column(
        String(50), ForeignKey("usuarios.username"), nullable=False
    )
    titulo_evento = Column(String(200), nullable=False)
    data_reserva = Column(Date, nullable=False)
    codigo_bloco = Column(
        String(3), ForeignKey("horarios_bloco.codigo_bloco"), nullable=False
    )
    status = Column(String(20), default="Aprovada")

    # Relationships
    sala = relationship("Sala", back_populates="reservas_esporadicas")
    solicitante = relationship("Usuario", back_populates="reservas_esporadicas")
    horario_bloco = relationship("HorarioBloco", back_populates="reservas_esporadicas")

    # Unique constraint to prevent double bookings
    __table_args__ = (
        UniqueConstraint(
            "sala_id", "data_reserva", "codigo_bloco", name="uq_reserva_conflito"
        ),
    )

    def __repr__(self):
        return f"<ReservaEsporadica(id={self.id}, sala_id={self.sala_id}, data='{self.data_reserva}', status='{self.status}')>"


# User Models
class Usuario(Base):
    """User SQLAlchemy model"""

    __tablename__ = "usuarios"

    username = Column(String(50), primary_key=True, nullable=False)
    password_hash = Column(String(60), nullable=False)
    nome_completo = Column(String(200))
    role = Column(String(20), default="professor")

    # Relationships
    reservas_esporadicas = relationship(
        "ReservaEsporadica", back_populates="solicitante"
    )

    def __repr__(self):
        return f"<Usuario(username='{self.username}', role='{self.role}')>"


# Database Manager
class DatabaseManager:
    """Singleton database manager for connection handling"""

    _instance = None
    _engine = None
    _SessionLocal = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._engine is None:
            self._initialize_database()

    def _initialize_database(self):
        """Initialize database engine and session"""
        # For SQLite, we need to enable foreign key support
        connect_args = {"check_same_thread": False}

        if DATABASE_URL.startswith("sqlite"):
            connect_args["poolclass"] = StaticPool

        self._engine = create_engine(
            DATABASE_URL,
            connect_args=connect_args,
            echo=os.getenv("DEBUG", "False").lower() == "true",
        )

        self._SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self._engine
        )

    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self._engine)

    def drop_tables(self):
        """Drop all database tables"""
        Base.metadata.drop_all(bind=self._engine)

    def get_session(self) -> Session:
        """Get a new database session"""
        return self._SessionLocal()

    def close_session(self, session: Session):
        """Close database session"""
        session.close()

    def check_connection(self) -> bool:
        """Check database connection"""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


# Database initialization functions
def init_database():
    """Initialize database with schema and basic data"""
    db_manager = DatabaseManager()

    # Create tables
    db_manager.create_tables()

    # Enable foreign key support for SQLite
    if DATABASE_URL.startswith("sqlite"):
        with db_manager.get_session() as session:
            session.execute(text("PRAGMA foreign_keys = ON"))
            session.commit()

    return db_manager


def create_session() -> Session:
    """Create a new database session"""
    db_manager = DatabaseManager()
    return db_manager.get_session()


def get_database_info():
    """Get database connection information"""
    db_manager = DatabaseManager()

    # Get database path
    if DATABASE_URL.startswith("sqlite"):
        db_path = DATABASE_URL.replace("sqlite:///", "")
    else:
        db_path = DATABASE_URL

    # Check connection and count tables
    is_connected = db_manager.check_connection()

    tables_count = 0
    last_modified = None

    if is_connected:
        try:
            with db_manager.get_session() as session:
                # Count tables
                result = session.execute(
                    text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                    if DATABASE_URL.startswith("sqlite")
                    else text(
                        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
                    )
                )
                scalar_result = result.scalar()
                if scalar_result is not None:
                    tables_count = (
                        scalar_result[0]
                        if hasattr(scalar_result, "__iter__")
                        else scalar_result
                    )
                else:
                    tables_count = 0

                # Get last modified time (for SQLite)
                if DATABASE_URL.startswith("sqlite"):
                    try:
                        import os

                        if os.path.exists(db_path):
                            last_modified = datetime.fromtimestamp(
                                os.path.getmtime(db_path)
                            )
                    except:
                        pass

        except Exception:
            pass

    return {
        "database_path": db_path,
        "is_connected": is_connected,
        "tables_count": tables_count,
        "last_modified": last_modified,
    }


# Context manager for database sessions
class DatabaseSession:
    """Context manager for database sessions"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.session = None

    def __enter__(self) -> Session:
        self.session = self.db_manager.get_session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type:
                self.session.rollback()
            else:
                self.session.commit()
            self.session.close()
