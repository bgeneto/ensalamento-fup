"""ORM models for application-level configuration storage."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, String, Text, UniqueConstraint

from src.models.base import BaseModel


class AppConfiguration(BaseModel):
    """Active persisted configuration for a named application setting."""

    __tablename__ = "app_configurations"

    config_key = Column(String(100), nullable=False, unique=True, index=True)
    schema_version = Column(String(20), nullable=False, default="1")
    overrides_json = Column(Text, nullable=False, default="{}")
    defaults_revision = Column(String(50), nullable=True)
    updated_by = Column(String(100), ForeignKey("usuarios.username"), nullable=True)
    change_reason = Column(Text, nullable=True)
    source = Column(String(50), nullable=False, default="ui")

    __table_args__ = (
        UniqueConstraint("config_key", name="ux_app_configurations_config_key"),
        {"sqlite_autoincrement": True},
    )


class AppConfigurationHistory(BaseModel):
    """Immutable snapshots for auditing configuration changes over time."""

    __tablename__ = "app_configuration_history"

    config_key = Column(String(100), nullable=False, index=True)
    schema_version = Column(String(20), nullable=False, default="1")
    overrides_json = Column(Text, nullable=False, default="{}")
    effective_config_json = Column(Text, nullable=False, default="{}")
    changed_by = Column(String(100), ForeignKey("usuarios.username"), nullable=True)
    change_reason = Column(Text, nullable=True)
    source = Column(String(50), nullable=False, default="ui")

    __table_args__ = ({"sqlite_autoincrement": True},)
