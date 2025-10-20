"""
Domain models for inventory management (Campus, Building, Room, etc.)
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Text, Table, Boolean
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


# Association table for Room-Characteristic N:N relationship
sala_caracteristicas = Table(
    "sala_caracteristicas",
    BaseModel.registry.metadata,
    Column(
        "sala_id", Integer, ForeignKey("salas.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "caracteristica_id",
        Integer,
        ForeignKey("caracteristicas.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Campus(BaseModel):
    """Campus entity - represents physical campuses."""

    __tablename__ = "campus"

    nome = Column(String(255), nullable=False, unique=True)
    descricao = Column(Text, nullable=True)

    # Relationships
    predios = relationship(
        "Predio", back_populates="campus", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Campus(id={self.id}, nome='{self.nome}')>"


class Predio(BaseModel):
    """Building entity - buildings belong to a campus."""

    __tablename__ = "predios"

    nome = Column(String(255), nullable=False, unique=True)
    campus_id = Column(Integer, ForeignKey("campus.id"), nullable=False)

    # Relationships
    campus = relationship("Campus", back_populates="predios")
    salas = relationship("Sala", back_populates="predio", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Predio(id={self.id}, nome='{self.nome}')>"


class TipoSala(BaseModel):
    """Room type entity (classroom, lab, auditorium, etc.)."""

    __tablename__ = "tipos_sala"

    nome = Column(String(255), nullable=False, unique=True)
    descricao = Column(Text, nullable=True)

    # Relationships
    salas = relationship("Sala", back_populates="tipo_sala")

    def __repr__(self) -> str:
        return f"<TipoSala(id={self.id}, nome='{self.nome}')>"


class Caracteristica(BaseModel):
    """Room characteristic entity (projector, wheelchair access, etc.)."""

    __tablename__ = "caracteristicas"

    nome = Column(String(255), nullable=False, unique=True)

    # Relationships
    salas = relationship(
        "Sala", secondary=sala_caracteristicas, back_populates="caracteristicas"
    )

    def __repr__(self) -> str:
        return f"<Caracteristica(id={self.id}, nome='{self.nome}')>"


class Sala(BaseModel):
    """Room entity - physical classroom or lab."""

    __tablename__ = "salas"

    nome = Column(String(255), nullable=False)
    predio_id = Column(Integer, ForeignKey("predios.id"), nullable=False)
    tipo_sala_id = Column(Integer, ForeignKey("tipos_sala.id"), nullable=False)
    capacidade = Column(Integer, default=0)
    andar = Column(Integer, nullable=True)
    tipo_assento = Column(String(100), nullable=True)

    # Relationships
    predio = relationship("Predio", back_populates="salas")
    tipo_sala = relationship("TipoSala", back_populates="salas")
    caracteristicas = relationship(
        "Caracteristica", secondary=sala_caracteristicas, back_populates="salas"
    )
    alocacoes = relationship(
        "AlocacaoSemestral", back_populates="sala", cascade="all, delete-orphan"
    )
    reservas = relationship(
        "ReservaEsporadica", back_populates="sala", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Unique constraint on name within a building
        {"sqlite_autoincrement": True},
    )

    def __repr__(self) -> str:
        return f"<Sala(id={self.id}, nome='{self.nome}')>"
