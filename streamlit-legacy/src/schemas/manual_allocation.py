"""DTO schemas for Manual Allocation domain."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from dataclasses import dataclass


# ============================================================================
# COMPATIBILITY SCORING
# ============================================================================


@dataclass
class CompatibilityScore:
    """Internal scoring structure for room compatibility."""

    total_score: int = 0
    hard_rules_compliant: bool = False
    soft_preferences_compliant: bool = False
    meets_capacity: bool = False
    rule_violations: List[str] = None

    def __post_init__(self):
        if self.rule_violations is None:
            self.rule_violations = []


# ============================================================================
# SUGGESTION DTOs
# ============================================================================


class RoomSuggestion(BaseModel):
    """Represents a room suggestion for manual allocation."""

    sala_id: int = Field(..., gt=0)
    nome_sala: str = Field(..., min_length=1)
    tipo_sala_nome: str = Field(..., min_length=1)
    capacidade: int = Field(..., ge=0)
    andar: Optional[int] = None
    predio_nome: str = Field(..., min_length=1)

    # Compatibility scoring
    compatibility_score: int = Field(default=0, ge=0)

    # Rule compliance
    hard_rules_compliant: bool = Field(default=False)
    soft_preferences_compliant: bool = Field(default=False)
    meets_capacity: bool = Field(default=False)

    # Conflict status
    has_conflicts: bool = Field(default=False)
    conflict_details: List[str] = Field(default_factory=list)

    # Metadata
    rule_violations: List[str] = Field(default_factory=list)
    motivation_reason: str = Field("", description="Why this room was suggested")

    # Detailed scoring breakdown (for advanced UI)
    scoring_breakdown: Optional[Dict[str, Any]] = Field(
        None, description="Detailed breakdown of how this room was scored"
    )

    class Config:
        from_attributes = True


class AllocationSuggestions(BaseModel):
    """Complete suggestion results for a demand."""

    demanda_id: int
    top_suggestions: List[RoomSuggestion] = Field(default_factory=list)
    other_available: List[RoomSuggestion] = Field(default_factory=list)
    conflicting_rooms: List[RoomSuggestion] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ============================================================================
# ALLOCATION RESULT DTOs
# ============================================================================


class ConflictDetail(BaseModel):
    """Details of conflicts preventing allocation."""

    tipo_conflito: str = Field(...)  # 'semester_allocation' | 'ad_hoc_reservation'
    dia_sigaa: int = Field(..., ge=2, le=7)
    codigo_bloco: str = Field(..., min_length=1)
    entidade_conflitante: str = Field(...)  # course name, reservation title
    identificador_conflitante: str = Field(...)  # course code, reservation ID


class AllocationResult(BaseModel):
    """Result of attempting to allocate a demand."""

    success: bool = Field(default=False)
    demanda_id: int
    sala_id: Optional[int] = None

    # Success case
    created_allocation_ids: List[int] = Field(default_factory=list)

    # Failure case
    conflicts: List[ConflictDetail] = Field(default_factory=list)
    error_message: Optional[str] = None

    # Metadata
    allocated_blocks_count: int = Field(default=0)
    atomic_blocks_preview: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ============================================================================
# FILTER DTOs
# ============================================================================


class AllocationFilters(BaseModel):
    """Filters for the demand queue in manual allocation."""

    semester_id: Optional[int] = None
    search_text: Optional[str] = Field(None, max_length=255)
    rule_filter_type: Optional[str] = Field(
        None, description="Filter by rule type: 'laboratorio', 'mobilidade', etc."
    )
    professor_filter: Optional[str] = Field(
        None, description="Filter by professor name"
    )
    course_filter: Optional[str] = Field(None, description="Filter by course code")

    class Config:
        from_attributes = True


class AllocationProgress(BaseModel):
    """Progress summary for manual allocation."""

    semester_id: int
    total_demands: int = Field(default=0)
    allocated_demands: int = Field(default=0)
    unallocated_demands: int = Field(default=0)
    allocation_percent: float = Field(default=0.0)

    class Config:
        from_attributes = True
