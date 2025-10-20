"""
Academic domain models (Semester, Demand, Professor, User).
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Text, Boolean, Table
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


# Association table for Professor-Preferred Rooms
professor_prefere_sala = Table(
    "professor_prefere_sala",
    BaseModel.registry.metadata,
    Column(
        "professor_id",
        Integer,
        ForeignKey("professores.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "sala_id", Integer, ForeignKey("salas.id", ondelete="CASCADE"), primary_key=True
    ),
)


# Association table for Professor-Preferred Characteristics
professor_prefere_caracteristica = Table(
    "professor_prefere_caracteristica",
    BaseModel.registry.metadata,
    Column(
        "professor_id",
        Integer,
        ForeignKey("professores.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "caracteristica_id",
        Integer,
        ForeignKey("caracteristicas.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Semestre(BaseModel):
    """Semester entity - academic term (e.g., 2025.1, 2025.2)."""

    __tablename__ = "semestres"

    nome = Column(String(50), nullable=False, unique=True)
    status = Column(
        String(50), default="Planejamento"
    )  # Planejamento, Alocando, Finalizado, Ativo, Encerrado

    # Relationships - use lazy='select' to defer loading and avoid circular dependencies
    demandas = relationship(
        "Demanda",
        back_populates="semestre",
        cascade="all, delete-orphan",
        lazy="select",
    )
    alocacoes = relationship(
        "AlocacaoSemestral",
        back_populates="semestre",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Semestre(id={self.id}, nome='{self.nome}', status='{self.status}')>"


class Demanda(BaseModel):
    """Demand entity - course demand imported from external API."""

    __tablename__ = "demandas"

    semestre_id = Column(Integer, ForeignKey("semestres.id"), nullable=False)
    codigo_disciplina = Column(String(50), nullable=False)
    nome_disciplina = Column(String(255), nullable=False)
    professores_disciplina = Column(Text, nullable=True)  # Raw text from API
    turma_disciplina = Column(String(50), nullable=True)
    vagas_disciplina = Column(Integer, default=0)
    horario_sigaa_bruto = Column(String(255), nullable=False)  # e.g., "24M12 6T34"
    nivel_disciplina = Column(String(50), nullable=True)  # Graduação, Pós-Graduação

    # Relationships
    semestre = relationship("Semestre", back_populates="demandas")
    alocacoes = relationship(
        "AlocacaoSemestral", back_populates="demanda", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Demanda(id={self.id}, codigo='{self.codigo_disciplina}', nome='{self.nome_disciplina}')>"


class Professor(BaseModel):
    """Professor entity - managed by system administrators.

    IMPORTANT: Professors do NOT log into this system. They are managed as
    entities in the database by administrators who set their preferences
    and restrictions for classroom allocation.

    Attributes:
    - nome_completo: Full professor name
    - tem_baixa_mobilidade: Mobility restriction (hard constraint)
    - username_login: Reference to usuario table (if applicable, for audit trail)
    - salas_preferidas: N:N relationship to preferred rooms (managed by admin)
    - caracteristicas_preferidas: N:N relationship to preferred characteristics (managed by admin)
    """

    __tablename__ = "professores"

    nome_completo = Column(String(255), nullable=False)
    tem_baixa_mobilidade = Column(Boolean, default=False)  # Hard constraint
    username_login = Column(
        String(100), nullable=True
    )  # Reference for audit trail only

    # Relationships - managed exclusively by administrators
    salas_preferidas = relationship(
        "Sala", secondary=professor_prefere_sala, backref="professores_que_preferem"
    )
    caracteristicas_preferidas = relationship(
        "Caracteristica",
        secondary=professor_prefere_caracteristica,
        backref="professores_que_preferem",
    )

    def __repr__(self) -> str:
        return f"<Professor(id={self.id}, nome='{self.nome_completo}')>"


class Usuario(BaseModel):
    """User entity for authentication and audit logging.

    IMPORTANT: Schema defines username as TEXT PRIMARY KEY, not auto-incrementing id.
    This model uses BaseModel which includes id/created_at/updated_at.

    Fields in database schema:
    - username: PRIMARY KEY (TEXT, NOT NULL)
    - password_hash: TEXT NOT NULL
    - nome_completo: TEXT
    - role: TEXT DEFAULT 'professor'

    NOTE: Passwords are stored in .streamlit/config.yaml for streamlit-authenticator,
    not in this database table. This table is for reference/audit only.
    """

    __tablename__ = "usuarios"

    username = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=True)  # For future use if needed
    nome_completo = Column(String(255), nullable=True)
    role = Column(String(50), default="admin")  # admin, professor, gestor, etc.

    def __repr__(self) -> str:
        return (
            f"<Usuario(id={self.id}, username='{self.username}', role='{self.role}')>"
        )
