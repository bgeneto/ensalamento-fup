"""Reservation management state - Phase 2 Business Logic."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import reflex as rx

from core.services.reservation_service import ReservationService
from .base_state import BaseState

logger = logging.getLogger(__name__)


class ReservationState(BaseState):
    """Reservation management and conflict detection.
    
    Handles:
    - Reservation creation/update with time conflict detection
    - Filtering and search
    - Status tracking
    """

    # Data
    reservations: list[Dict[str, Any]] = []
    filtered_reservations: list[Dict[str, Any]] = []

    # UI state
    selected_reservation: Optional[Dict[str, Any]] = None
    show_create_dialog: bool = False

    # Filters
    search_query: str = ""
    status_filter: str = "all"  # all, approved, pending, cancelled
    date_range_start: str = ""
    date_range_end: str = ""

    @rx.var
    def total_reservations(self) -> int:
        """Computed total count."""
        return len(self.reservations)

    @rx.var
    def upcoming_reservations(self) -> list[Dict[str, Any]]:
        """Computed upcoming reservations (after now)."""
        now = datetime.now().isoformat()
        return [
            r for r in self.reservations
            if r.get("data_reserva", "") > now
        ]

    @rx.var
    def todays_reservations(self) -> list[Dict[str, Any]]:
        """Computed reservations for today."""
        today = datetime.now().date().isoformat()
        return [
            r for r in self.reservations
            if r.get("data_reserva", "").startswith(today)
        ]

    @rx.var
    def status_counts(self) -> Dict[str, int]:
        """Computed status distribution."""
        counts = {
            "approved": 0,
            "pending": 0,
            "cancelled": 0,
        }
        for r in self.reservations:
            status = r.get("status", "approved").lower()
            if status in counts:
                counts[status] += 1
        return counts

    def update_filters(self):
        """Update filtered results based on current filters."""
        filtered = self.reservations

        # Search filter
        if self.search_query:
            query = self.search_query.lower()
            filtered = [
                r for r in filtered
                if query in r.get("titulo_evento", "").lower()
                or query in r.get("nome_solicitante", "").lower()
            ]

        # Status filter
        if self.status_filter != "all":
            filtered = [
                r for r in filtered
                if r.get("status", "approved").lower() == self.status_filter.lower()
            ]

        # Date range filters
        if self.date_range_start:
            filtered = [
                r for r in filtered
                if r.get("data_reserva", "") >= self.date_range_start
            ]
        if self.date_range_end:
            filtered = [
                r for r in filtered
                if r.get("data_reserva", "") <= self.date_range_end
            ]

        # Defensive reassignment to trigger reactivity
        self.filtered_reservations = list(filtered)

    def set_search_query(self, query: str):
        """Set search query and update filters."""
        self.search_query = query
        self.update_filters()

    def set_status_filter(self, status: str):
        """Set status filter and update filters."""
        self.status_filter = status
        self.update_filters()

    def set_date_range(self, start: str, end: str):
        """Set date range and update filters."""
        self.date_range_start = start
        self.date_range_end = end
        self.update_filters()

    async def load_reservations(self):
        """Load all reservations from database using ReservationService."""
        try:
            # Call ReservationService to get all reservations
            reservations = await ReservationService.get_all_reservations()
            
            self.reservations = reservations
            self.update_filters()
            
            yield rx.toast.info(f"Carregadas {len(reservations)} reservas")

        except Exception as e:
            yield rx.toast.error(f"Falha ao carregar reservas: {e}")
            logger.error("Failed to load reservations", exc_info=True)

    async def create_reservation(self, reservation_data: Dict[str, Any]):
        """Create new reservation with validation and conflict checking.
        
        Args:
            reservation_data: Reservation details
        """
        try:
            # Validate data
            if not reservation_data.get("titulo_evento"):
                yield rx.toast.error("Título do evento é obrigatório")
                return

            if not reservation_data.get("data_reserva"):
                yield rx.toast.error("Data da reserva é obrigatória")
                return

            # Call ReservationService to create reservation (includes conflict check)
            result = await ReservationService.create_reservation(reservation_data)
            
            if result.get("success"):
                # Reload reservations to show new one
                await self.load_reservations()
                
                yield rx.toast.success(f"Reserva #{result.get('reservation_id')} criada com sucesso!")
                
                # Close dialog
                self.show_create_dialog = False
            else:
                # Show conflict info if available
                conflicts = result.get("conflicts", [])
                if conflicts:
                    conflict_info = ", ".join(
                        [c.get("titulo", "Evento desconhecido") for c in conflicts]
                    )
                    yield rx.toast.error(
                        f"Conflito detectado com: {conflict_info}"
                    )
                else:
                    yield rx.toast.error(result.get("message", "Falha ao criar reserva"))

        except Exception as e:
            yield rx.toast.error(f"Falha ao criar reserva: {e}")
            logger.error("Reservation creation failed", exc_info=True)

    async def update_reservation(
        self, reservation_id: int, updated_data: Dict[str, Any]
    ):
        """Update existing reservation.
        
        Args:
            reservation_id: ID of reservation to update
            updated_data: Updated reservation data
        """
        try:
            # Find reservation
            reservation = next(
                (r for r in self.reservations if r.get("id") == reservation_id),
                None,
            )

            if not reservation:
                yield rx.toast.error("Reserva não encontrada")
                return

            # Check conflicts (excluding this reservation)
            conflicts = await self._check_time_conflicts(updated_data, exclude_id=reservation_id)
            if conflicts:
                yield rx.toast.error("Conflito de horário detectado")
                return

            # Update reservation
            for key, value in updated_data.items():
                reservation[key] = value
            reservation["updated_at"] = datetime.now().isoformat()

            # Defensive reassignment
            self.reservations = list(self.reservations)

            yield rx.toast.success("Reserva atualizada com sucesso!")
            self.update_filters()
            self.selected_reservation = None

        except Exception as e:
            yield rx.toast.error(f"Falha ao atualizar reserva: {e}")
            logger.error("Reservation update failed", exc_info=True)

    async def delete_reservation(self, reservation_id: int):
        """Delete reservation.
        
        Args:
            reservation_id: ID of reservation to delete
        """
        try:
            # Remove from list
            self.reservations = [
                r for r in self.reservations if r.get("id") != reservation_id
            ]

            yield rx.toast.success("Reserva deletada com sucesso!")
            self.update_filters()
            self.selected_reservation = None

        except Exception as e:
            yield rx.toast.error(f"Falha ao deletar reserva: {e}")
            logger.error("Reservation deletion failed", exc_info=True)

    def show_reservation_details(self, reservation: Dict[str, Any]):
        """Show details for selected reservation."""
        self.selected_reservation = reservation

    def clear_selection(self):
        """Clear current selection."""
        self.selected_reservation = None

    def toggle_create_dialog(self):
        """Toggle create dialog visibility."""
        self.show_create_dialog = not self.show_create_dialog

    # Private helper methods

    async def _check_time_conflicts(
        self,
        reservation_data: Dict[str, Any],
        exclude_id: Optional[int] = None,
    ) -> list[Dict[str, Any]]:
        """Check for time conflicts with existing reservations.
        
        Args:
            reservation_data: Reservation to check
            exclude_id: Reservation ID to exclude from check
            
        Returns:
            List of conflicting reservations (empty if none)
        """
        try:
            # TODO: Implement actual conflict checking based on time blocks
            # For now, return empty list (no conflicts)
            return []

        except Exception as e:
            logger.error("Conflict check failed", exc_info=True)
            return []
