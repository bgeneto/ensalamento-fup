"""
Allocation and reservation models.
"""

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    UniqueConstraint,
    DateTime,
    JSON,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import json

from src.models.base import BaseModel


class Regra(BaseModel):
    """Allocation rule entity - hard and soft rules for allocation."""

    __tablename__ = "regras"

    descricao = Column(String(255), nullable=False)
    tipo_regra = Column(
        String(100), nullable=False
    )  # Rule type (e.g., "DISCIPLINA_TIPO_SALA", "DISCIPLINA_SALA", "DISCIPLINA_CARACTERISTICA")
    config_json = Column(Text, nullable=False)  # JSON configuration for rule parameters
    prioridade = Column(
        Integer, default=1
    )  # 0=hard rule (must be satisfied), >0=soft preference (prioritization level)

    def __repr__(self) -> str:
        return f"<Regra(id={self.id}, tipo='{self.tipo_regra}', prioridade={self.prioridade})>"

    def get_config(self) -> dict:
        """Get parsed config_json as dictionary."""
        import json

        try:
            return json.loads(self.config_json) if self.config_json else {}
        except json.JSONDecodeError:
            return {}

    def set_config(self, config_dict: dict):
        """Set config_json from dictionary."""
        import json

        self.config_json = json.dumps(config_dict, ensure_ascii=False)


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

    __table_args__ = (
        # UNIQUE constraint to prevent scheduling conflicts:
        # Cannot have same semester/room/day/block allocation
        UniqueConstraint(
            "semestre_id",
            "sala_id",
            "dia_semana_id",
            "codigo_bloco",
            name="ux_alocacoes_semestrais_unica",
        ),
        {"sqlite_autoincrement": True},
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

    # Relationships
    sala = relationship("Sala", back_populates="reservas")

    def __repr__(self) -> str:
        return f"<ReservaEsporadica(id={self.id}, sala={self.sala_id}, data={self.data_reserva})>"


class ReservaEvento(BaseModel):
    """Parent event entity for recurring reservations.

    This is the parent table that stores the main event information
    and recurrence rules. Individual occurrences are stored in
    reservas_ocorrencias.
    """

    __tablename__ = "reservas_eventos"

    # Foreign keys
    sala_id = Column(Integer, ForeignKey("salas.id"), nullable=False)
    username_criador = Column(
        String(100), ForeignKey("usuarios.username"), nullable=False
    )

    # Event details
    titulo_evento = Column(String(255), nullable=False)
    nome_solicitante = Column(
        String(255), nullable=False
    )  # Required - full name of person requesting reservation
    nome_responsavel = Column(
        String(255), nullable=True
    )  # Optional - full name of person responsible for event

    # Recurrence rule in JSON format
    # Examples:
    # {"tipo": "unica"} - single occurrence
    # {"tipo": "semanal", "dias": [2, 4], "fim": "2025-12-31"} - every Mon, Wed until Dec 31
    # {"tipo": "diaria", "intervalo": 1, "fim": "2025-11-30"} - daily until Nov 30
    # {"tipo": "mensal", "dia_mes": 15, "fim": "2025-12-31"} - 15th of each month
    # {"tipo": "mensal", "posicao": 1, "dia_semana": 2, "fim": "2025-12-31"} - first Monday of each month
    regra_recorrencia_json = Column(Text, nullable=False, default='{"tipo": "unica"}')

    # Timestamps (inherited from BaseModel)

    # Relationships
    sala = relationship("Sala")
    ocorrencias = relationship(
        "ReservaOcorrencia", back_populates="evento", cascade="all, delete-orphan"
    )

    def get_regra_recorrencia(self) -> dict:
        """Get parsed recurrence rule as dictionary."""
        try:
            return (
                json.loads(self.regra_recorrencia_json)
                if self.regra_recorrencia_json
                else {"tipo": "unica"}
            )
        except json.JSONDecodeError:
            return {"tipo": "unica"}

    def set_regra_recorrencia(self, regra_dict: dict):
        """Set recurrence rule from dictionary."""
        self.regra_recorrencia_json = json.dumps(regra_dict, ensure_ascii=False)

    def is_recorrente(self) -> bool:
        """Check if this is a recurring event."""
        regra = self.get_regra_recorrencia()
        return regra.get("tipo") != "unica"

    def __repr__(self) -> str:
        return f"<ReservaEvento(id={self.id}, titulo='{self.titulo_evento}', sala={self.sala_id})>"


class ReservaOcorrencia(BaseModel):
    """Individual occurrence of a recurring reservation.

    This is the child table that stores each specific date/time
    instance of a recurring reservation event.
    """

    __tablename__ = "reservas_ocorrencias"

    # Foreign key to parent event
    evento_id = Column(Integer, ForeignKey("reservas_eventos.id"), nullable=False)

    # Specific occurrence details
    data_reserva = Column(String(10), nullable=False)  # DATE as YYYY-MM-DD string
    codigo_bloco = Column(
        String(10), ForeignKey("horarios_bloco.codigo_bloco"), nullable=False
    )

    # Optional exception status (e.g., "Cancelada")
    status_excecao = Column(String(50), nullable=True)

    # Unique constraint to prevent duplicate occurrences
    __table_args__ = (
        UniqueConstraint(
            "evento_id",
            "data_reserva",
            "codigo_bloco",
            name="ux_reservas_ocorrencias_unica",
        ),
        {"sqlite_autoincrement": True},
    )

    # Relationships
    evento = relationship("ReservaEvento", back_populates="ocorrencias")
    bloco_horario = relationship("HorarioBloco")

    def __repr__(self) -> str:
        return f"<ReservaOcorrencia(id={self.id}, evento_id={self.evento_id}, data={self.data_reserva}, bloco={self.codigo_bloco})>"
