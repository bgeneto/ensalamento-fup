"""Room inventory management state - Phase 2 Business Logic."""

import logging
from typing import Any, Dict, Optional

import reflex as rx

from core.services.room_service import RoomService
from .base_state import BaseState

logger = logging.getLogger(__name__)


class RoomState(BaseState):
    """Room inventory management with pagination and filtering.
    
    Handles:
    - Room CRUD operations
    - Pagination for large datasets
    - Filtering and search
    - Capacity/facility management
    """

    # Data
    rooms: list[Dict[str, Any]] = []
    displayed_rooms: list[Dict[str, Any]] = []

    # Pagination
    page: int = 1
    page_size: int = 20

    # Filters
    search_query: str = ""
    building_filter: str = "all"
    capacity_min: int = 0
    room_type_filter: str = "all"

    # Create/Edit dialog
    show_dialog: bool = False
    is_editing: bool = False
    edit_room_id: Optional[int] = None

    @rx.var
    def filtered_rooms(self) -> list[Dict[str, Any]]:
        """Computed filtered rooms based on current filters."""
        filtered = self.rooms

        # Search filter
        if self.search_query:
            query = self.search_query.lower()
            filtered = [
                room for room in filtered
                if query in room.get("nome", "").lower()
                or query in room.get("descricao", "").lower()
            ]

        # Building filter
        if self.building_filter != "all":
            filtered = [
                room for room in filtered
                if room.get("predio_nome") == self.building_filter
            ]

        # Capacity filter
        if self.capacity_min > 0:
            filtered = [
                room for room in filtered
                if room.get("capacidade", 0) >= self.capacity_min
            ]

        # Room type filter
        if self.room_type_filter != "all":
            filtered = [
                room for room in filtered
                if room.get("tipo_sala_nome") == self.room_type_filter
            ]

        return filtered

    @rx.var
    def total_pages(self) -> int:
        """Computed total pages for pagination."""
        total_filtered = len(self.filtered_rooms)
        return max(1, (total_filtered + self.page_size - 1) // self.page_size)

    @rx.var
    def current_page_rooms(self) -> list[Dict[str, Any]]:
        """Computed rooms for current page (defensive reassignment handled by rx.var)."""
        filtered = self.filtered_rooms
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        return filtered[start:end]

    def update_displayed_rooms(self):
        """Update displayed rooms based on pagination."""
        self.displayed_rooms = list(self.current_page_rooms)

    def next_page(self):
        """Navigate to next page."""
        if self.page < self.total_pages:
            self.page += 1
            self.update_displayed_rooms()

    def prev_page(self):
        """Navigate to previous page."""
        if self.page > 1:
            self.page -= 1
            self.update_displayed_rooms()

    def go_to_page(self, page: int):
        """Navigate to specific page."""
        if 1 <= page <= self.total_pages:
            self.page = page
            self.update_displayed_rooms()

    def apply_filters(self):
        """Apply current filters and reset to page 1."""
        self.page = 1
        self.update_displayed_rooms()

    def set_search_query(self, query: str):
        """Set search query and apply filters."""
        self.search_query = query
        self.apply_filters()

    def set_building_filter(self, building: str):
        """Set building filter."""
        self.building_filter = building
        self.apply_filters()

    def set_capacity_min(self, capacity: int):
        """Set minimum capacity filter."""
        self.capacity_min = capacity
        self.apply_filters()

    def set_room_type_filter(self, room_type: str):
        """Set room type filter."""
        self.room_type_filter = room_type
        self.apply_filters()

    def clear_filters(self):
        """Clear all filters."""
        self.search_query = ""
        self.building_filter = "all"
        self.capacity_min = 0
        self.room_type_filter = "all"
        self.page = 1
        self.update_displayed_rooms()

    def toggle_dialog(self):
        """Toggle create/edit dialog."""
        self.show_dialog = not self.show_dialog
        if not self.show_dialog:
            self.is_editing = False
            self.edit_room_id = None

    async def load_rooms(self):
        """Load all rooms from database using RoomService."""
        try:
            # Call RoomService to get all rooms
            rooms = await RoomService.get_all_rooms()
            
            self.rooms = rooms
            self.page = 1  # Reset to first page
            self.update_displayed_rooms()
            
            yield rx.toast.info(f"Carregadas {len(rooms)} salas")

        except Exception as e:
            yield rx.toast.error(f"Falha ao carregar salas: {e}")
            logger.error("Failed to load rooms", exc_info=True)

    async def create_room(self, room_data: Dict[str, Any]):
        """Create new room with validation using RoomService.
        
        Args:
            room_data: Room details
        """
        try:
            # Validate required fields
            if not room_data.get("nome"):
                yield rx.toast.error("Nome da sala é obrigatório")
                return

            if not room_data.get("capacidade"):
                yield rx.toast.error("Capacidade é obrigatória")
                return

            # Call RoomService to create room (validates duplicates internally)
            result = await RoomService.create_room(room_data)
            
            if result.get("success"):
                # Reload rooms to show new one
                await self.load_rooms()
                
                yield rx.toast.success(f"Sala #{result.get('room_id')} criada com sucesso!")
                
                # Close dialog
                self.toggle_dialog()
            else:
                yield rx.toast.error(result.get("message", "Falha ao criar sala"))

        except Exception as e:
            yield rx.toast.error(f"Falha ao criar sala: {e}")
            logger.error("Room creation failed", exc_info=True)

    async def update_room(self, room_id: int, room_data: Dict[str, Any]):
        """Update existing room using RoomService.
        
        Args:
            room_id: ID of room to update
            room_data: Updated room data
        """
        try:
            # Validate
            if not room_data.get("nome"):
                yield rx.toast.error("Nome da sala é obrigatório")
                return

            # Call RoomService to update room (validates duplicates internally)
            result = await RoomService.update_room(room_id, room_data)
            
            if result.get("success"):
                # Reload rooms to show updated one
                await self.load_rooms()
                
                yield rx.toast.success("Sala atualizada com sucesso!")
                
                # Close dialog
                self.toggle_dialog()
            else:
                yield rx.toast.error(result.get("message", "Falha ao atualizar sala"))

        except Exception as e:
            yield rx.toast.error(f"Falha ao atualizar sala: {e}")
            logger.error("Room update failed", exc_info=True)

    async def delete_room(self, room_id: int):
        """Delete room using RoomService.
        
        Args:
            room_id: ID of room to delete
        """
        try:
            # Call RoomService to delete room
            result = await RoomService.delete_room(room_id)
            
            if result.get("success"):
                # Reload rooms to reflect deletion
                await self.load_rooms()
                
                yield rx.toast.success("Sala deletada com sucesso!")
            else:
                yield rx.toast.error(result.get("message", "Falha ao deletar sala"))

        except Exception as e:
            yield rx.toast.error(f"Falha ao deletar sala: {e}")
            logger.error("Room deletion failed", exc_info=True)

    def start_edit(self, room_id: int):
        """Start editing a room."""
        self.is_editing = True
        self.edit_room_id = room_id
        self.show_dialog = True

    def cancel_edit(self):
        """Cancel editing."""
        self.toggle_dialog()
        self.is_editing = False
        self.edit_room_id = None
