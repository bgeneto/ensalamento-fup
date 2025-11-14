"""Semester management state - Phase 2 Business Logic."""

import logging
from typing import Any, Dict, Optional

import reflex as rx

from .base_state import BaseState

logger = logging.getLogger(__name__)


class SemesterState(BaseState):
    """Semester and course data management.
    
    Handles:
    - Semester selection and data loading
    - Course/demand data management
    - Semester-specific allocations
    """

    # Current semester
    current_semester_id: int = 20251
    current_semester: Optional[Dict[str, Any]] = None
    available_semesters: list[Dict[str, Any]] = []

    # Demands/Courses
    demands: list[Dict[str, Any]] = []
    loading_demands: bool = False

    @rx.var
    def semester_display_name(self) -> str:
        """Computed semester display name (e.g., '2025.1')."""
        if not self.current_semester:
            return "Semestre não selecionado"

        semester_id = self.current_semester.get("id")
        if isinstance(semester_id, int):
            year = semester_id // 10
            period = semester_id % 10
            return f"{year}.{period}"

        return str(semester_id)

    @rx.var
    def total_demands(self) -> int:
        """Computed total number of demands/courses."""
        return len(self.demands)

    @rx.var
    def demands_by_period(self) -> Dict[str, int]:
        """Computed count of demands by time period."""
        by_period = {}
        for demand in self.demands:
            period = demand.get("horario_blocks", [])
            period_key = ", ".join(period) if period else "Sem horário"
            by_period[period_key] = by_period.get(period_key, 0) + 1

        return by_period

    async def load_semesters(self):
        """Load available semesters from database.
        
        TODO: Replace with actual SemesterService.get_all_semesters()
        """
        try:
            # TODO: self.available_semesters = await SemesterService.get_all_semesters_async()
            # For development, create mock semesters
            self.available_semesters = [
                {"id": 20251, "nome": "2025.1", "ativo": True},
                {"id": 20242, "nome": "2024.2", "ativo": False},
                {"id": 20241, "nome": "2024.1", "ativo": False},
            ]

            # Set current if not set
            if not self.current_semester and self.available_semesters:
                await self.select_semester(self.available_semesters[0]["id"])

        except Exception as e:
            yield rx.toast.error(f"Falha ao carregar semestres: {e}")
            logger.error("Failed to load semesters", exc_info=True)

    async def select_semester(self, semester_id: int):
        """Select a semester and load its data.
        
        Args:
            semester_id: Semester to select
        """
        try:
            self.current_semester_id = semester_id

            # Find semester details
            semester = next(
                (s for s in self.available_semesters if s.get("id") == semester_id),
                None,
            )
            self.current_semester = semester

            # Load demands for this semester
            await self.load_semester_demands(semester_id)

            yield rx.toast.success(f"Semestre {self.semester_display_name} selecionado")

        except Exception as e:
            yield rx.toast.error(f"Falha ao selecionar semestre: {e}")
            logger.error("Failed to select semester", exc_info=True)

    async def load_semester_demands(self, semester_id: int):
        """Load course demands for a semester.
        
        Args:
            semester_id: Semester ID
        """
        if self.loading_demands:
            return

        self.loading_demands = True

        try:
            # TODO: Replace with actual DemandService call
            # self.demands = await DemandService.get_semester_demands_async(semester_id)
            # For development, use empty list
            self.demands = []

        except Exception as e:
            yield rx.toast.error(f"Falha ao carregar demandas: {e}")
            logger.error("Failed to load demands", exc_info=True)

        finally:
            self.loading_demands = False

    async def refresh_semester_data(self):
        """Refresh current semester data."""
        if self.current_semester_id:
            await self.load_semester_demands(self.current_semester_id)
            yield rx.toast.success("Dados do semestre atualizados")
