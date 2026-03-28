"""DTO schemas for application configuration persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class AppConfigurationRead(BaseModel):
    """DTO for reading an active application configuration."""

    id: int
    config_key: str
    schema_version: str
    overrides_json: Dict[str, Any] = Field(default_factory=dict)
    defaults_revision: Optional[str] = None
    updated_by: Optional[str] = None
    change_reason: Optional[str] = None
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AppConfigurationHistoryRead(BaseModel):
    """DTO for reading historical application configuration snapshots."""

    id: int
    config_key: str
    schema_version: str
    overrides_json: Dict[str, Any] = Field(default_factory=dict)
    effective_config_json: Dict[str, Any] = Field(default_factory=dict)
    changed_by: Optional[str] = None
    change_reason: Optional[str] = None
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
