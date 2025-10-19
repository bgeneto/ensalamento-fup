"""
Allocation and reservation models.
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class Regra(BaseModel):
    """Allocation rule entity - hard and soft rules for allocation."""

    __tablename__ = "regras"

    descricao = Column(String(255), nullable=False)
    tipo_regra = Column(
        String(100), nullable=False
    )  # Rule type (e.g., DISCIPLINA_TIPO_SALA)
    config_json = Column(Text)  # JSON configuration
    prioridade = Column(Integer, default=1)  # 0=hard, >0=soft (soft preference level)

    def __repr__(self) -> str:
        return f"<Regra(id={self.id}, tipo='{self.tipo_regra}')>"


class AlocacaoSemestral(BaseModel):
    """Semester allocation entity - course-room assignment by atomic time block."""

    __tablename__ = "alocacoes_semestrais"

    semestre_id = Column(Integer, ForeignKey("semestres.id"), nullable=False)
    demanda_id = Column(Integer, ForeignKey("demandas.id"), nullable=False)
    sala_id = Column(Integer, ForeignKey("salas.id"), nullable=False)
    dia_semana_id = Column(Integer, ForeignKey("dias_semana.id_sigaa"), nullable=False)
    codigo_bloco = Column(
        String(10), ForeignKey("horarios_bloco.codigo_bloco"), nullable=False
    )

    # Relationships
    semestre = relationship("Semestre", back_populates="alocacoes")
    demanda = relationship("Demanda", back_populates="alocacoes")
    sala = relationship("Sala", back_populates="alocacoes")

    def __repr__(self) -> str:
        return f"<AlocacaoSemestral(id={self.id}, demanda={self.demanda_id}, sala={self.sala_id})>"


class ReservaEsporadica(BaseModel):
    """Ad-hoc reservation entity - occasional room bookings by users.

    Schema fields:
    - sala_id: Foreign key to salas
    - username_solicitante: Foreign key to usuarios.username
    - titulo_evento: Event title
    - data_reserva: DATE (YYYY-MM-DD)
    - codigo_bloco: Foreign key to horarios_bloco
    - status: Aprovada, Rejeitada, etc.
    """

    __tablename__ = "reservas_esporadicas"

    sala_id = Column(Integer, ForeignKey("salas.id"), nullable=False)
    username_solicitante = Column(
        String(100), ForeignKey("usuarios.username"), nullable=False
    )
    titulo_evento = Column(String(255), nullable=False)
    data_reserva = Column(String(10), nullable=False)  # DATE as YYYY-MM-DD string
    codigo_bloco = Column(
        String(10), ForeignKey("horarios_bloco.codigo_bloco"), nullable=False
    )
    status = Column(String(50), default="Aprovada")  # Aprovada, Rejeitada, etc.

    # Relationships
    sala = relationship("Sala", back_populates="reservas")

    def __repr__(self) -> str:
        return f"<ReservaEsporadica(id={self.id}, sala={self.sala_id}, data={self.data_reserva})>"
