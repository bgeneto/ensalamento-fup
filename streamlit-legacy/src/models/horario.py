"""
Time management models for Sigaa time blocks and weekdays.
"""

from datetime import time as time_type
from sqlalchemy import Column, Integer, String, Time, DateTime
from datetime import datetime

from src.models.base import Base


class DiaSemana(Base):
    """Weekday entity - maps Sigaa day codes (2-7) to day names."""

    __tablename__ = "dias_semana"

    id_sigaa = Column(Integer, primary_key=True, autoincrement=False)
    nome = Column(String(50), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<DiaSemana(id_sigaa={self.id_sigaa}, nome='{self.nome}')>"


class HorarioBloco(Base):
    """Time block entity - Sigaa atomic time blocks (M1-M5, T1-T6, N1-N4)."""

    __tablename__ = "horarios_bloco"

    codigo_bloco = Column(String(10), primary_key=True, autoincrement=False)
    turno = Column(String(10), nullable=False)  # M (morning), T (afternoon), N (night)
    horario_inicio = Column(String(5), nullable=False)  # Store as HH:MM string
    horario_fim = Column(String(5), nullable=False)  # Store as HH:MM string
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<HorarioBloco(codigo_bloco='{self.codigo_bloco}', inicio={self.horario_inicio}, fim={self.horario_fim})>"
