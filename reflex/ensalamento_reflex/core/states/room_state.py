"""
Room State - Reflex Implementation
Manages room inventory and operations with reactive updates

Following patterns from docs/Technical_Constraints_Patterns.md:
- ✅ Defensive mutation patterns
- ✅ Computed properties with @rx.var
- ✅ Loading states for async operations
- ✅ Toast notifications for user feedback
"""

import reflex as rx

from ...services.room_service import RoomService


class RoomState(rx.State):
    """Room management state with comprehensive CRUD operations"""

    # Data
    rooms: list[dict] = []

    # Loading states (following loading pattern)
    loading_rooms: bool = False
    loading_create: bool = False
    loading_update: bool = False
    loading_delete: bool = False

    # Pagination
    page: int = 1
    page_size: int = 20

    # Filters
    search_query: str = ""
    building_filter: str = "all"
    capacity_min: int = 0
    room_type_filter: str = "all"

    # Form data for room creation/updates
    form_name: str = ""
    form_building: str = ""
    form_capacity: int = 0
    form_room_type: str = "Standard"
    form_description: str = ""
    form_equipment: list[str] = []

    # Form validation errors
    form_name_error: str = ""
    form_building_error: str = ""
    form_capacity_error: str = ""

    # UI state
    show_create_form: bool = False
    editing_room: dict | None = None
    selected_room: dict | None = None

    @rx.var
    def total_rooms(self) -> int:
        """Computed total room count"""
        return len(self.rooms)

    @rx.var
    def filtered_rooms(self) -> list[dict]:
        """Computed filtered rooms based on current filters"""
        filtered = self.rooms

        # Search filter
        if self.search_query.strip():
            query = self.search_query.strip().lower()
            filtered = [
                room
                for room in filtered
                if query in room.get("nome", "").lower()
                or query in room.get("predio", "").lower()
                or query in room.get("descrição", "").lower()
            ]

        # Building filter
        if self.building_filter != "all":
            filtered = [
                room for room in filtered if room.get("predio") == self.building_filter
            ]

        # Room type filter
        if self.room_type_filter != "all":
            filtered = [
                room
                for room in filtered
                if room.get("tipo_sala", "Standard") == self.room_type_filter
            ]

        # Capacity filter
        if self.capacity_min > 0:
            filtered = [
                room
                for room in filtered
                if room.get("capacidade", 0) >= self.capacity_min
            ]

        return filtered

    @rx.var
    def displayed_rooms(self) -> list[dict]:
        """Computed rooms displayed for current page"""
        filtered = self.filtered_rooms
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        return filtered[start:end]

    @rx.var
    def total_pages(self) -> int:
        """Computed total pages for pagination"""
        total_filtered = len(self.filtered_rooms)
        if total_filtered == 0:
            return 1
        return (total_filtered + self.page_size - 1) // self.page_size

    @rx.var
    def available_buildings(self) -> list[str]:
        """Computed unique buildings list for filter"""
        buildings = set(
            room.get("predio", "") for room in self.rooms if room.get("predio")
        )
        return sorted(list(buildings))

    @rx.var
    def rooms_by_building(self) -> dict[str, list[dict]]:
        """Computed rooms grouped by building"""
        grouped = {}
        for room in self.rooms:
            building = room.get("predio", "Unknown")
            if building not in grouped:
                grouped[building] = []
            grouped[building].append(room)
        return grouped

    @rx.var
    def utilization_summary(self) -> dict[str, dict]:
        """Computed room utilization summary"""
        utilized = sum(1 for room in self.rooms if room.get("alocado", False))
        return {
            "utilized_count": utilized,
            "available_count": len(self.rooms) - utilized,
            "utilization_percentage": (
                (utilized / len(self.rooms) * 100) if self.rooms else 0
            ),
        }

    async def load_rooms(self):
        """
        Load all rooms from database

        Following loading pattern with user feedback
        """
        if self.loading_rooms:
            yield rx.toast.info("Already loading rooms...")
            return

        self.loading_rooms = True
        self.error = ""
        yield

        try:
            # Use async service layer
            rooms_data = await RoomService.get_all_rooms()

            # Defensive reassignment
            self.rooms = rooms_data
            self.rooms = list(self.rooms)

            # Reset pagination
            self.page = 1

            yield rx.toast.success(f"Loaded {len(rooms_data)} rooms successfully")

        except Exception as e:
            self.error = f"Failed to load rooms: {str(e)}"
            yield rx.toast.error(f"Failed to load rooms: {e}")

        finally:
            self.loading_rooms = False

    def set_search_query(self, value: str):
        """Update search query and reset to page 1"""
        self.search_query = value.strip()
        self.page = 1

    def set_building_filter(self, value: str):
        """Update building filter and reset to page 1"""
        self.building_filter = value
        self.page = 1

    def set_room_type_filter(self, value: str):
        """Update room type filter and reset to page 1"""
        self.room_type_filter = value
        self.page = 1

    def set_capacity_min(self, value: int):
        """Update capacity filter and reset to page 1"""
        self.capacity_min = max(0, int(value))
        self.page = 1

    def set_page_size(self, value: int):
        """Update page size and reset to page 1"""
        self.page_size = max(5, min(100, int(value)))
        self.page = 1

    def next_page(self):
        """Navigate to next page"""
        if self.page < self.total_pages:
            self.page += 1

    def prev_page(self):
        """Navigate to previous page"""
        if self.page > 1:
            self.page -= 1

    def reset_filters(self):
        """Reset all filters and pagination"""
        self.search_query = ""
        self.building_filter = "all"
        self.capacity_min = 0
        self.room_type_filter = "all"
        self.page = 1
        yield rx.toast.info("Filters reset")

    def show_create_form(self):
        """Show create room form"""
        self.show_create_form = True
        self.editing_room = None
        self._clear_form()

    def hide_create_form(self):
        """Hide create room form"""
        self.show_create_form = False
        self.editing_room = None
        self._clear_form()

    def start_editing_room(self, room: dict):
        """Start editing a room"""
        self.editing_room = room
        self.show_create_form = True

        # Populate form with room data
        self.form_name = room.get("nome", "")
        self.form_building = room.get("predio", "")
        self.form_capacity = room.get("capacidade", 0)
        self.form_room_type = room.get("tipo_sala", "Standard")
        self.form_description = room.get("descrição", "")
        self.form_equipment = room.get("equipamento", [])

    def select_room(self, room: dict):
        """Select a room for viewing/editing"""
        self.selected_room = room

    async def create_room(self):
        """
        Create new room with validation

        Following validation and loading patterns
        """
        if self.loading_create:
            yield rx.toast.info("Already creating room...")
            return

        # Client-side validation
        if not self._validate_form():
            return

        self.loading_create = True
        yield

        try:
            # Prepare room data
            room_data = {
                "nome": self.form_name,
                "predio": self.form_building,
                "capacidade": self.form_capacity,
                "tipo_sala": self.form_room_type,
                "descrição": self.form_description,
                "equipamento": self.form_equipment,
            }

            # Create via service
            result = await RoomService.create_room(room_data)

            if result and result.get("success"):
                # Add to local state defensively
                new_room = result.get("room", room_data)
                self.rooms.append(new_room)
                self.rooms = list(self.rooms)

                # Reset form and UI
                self.hide_create_form()
                yield rx.toast.success(
                    f"Room '{new_room.get('nome')}' created successfully"
                )
            else:
                error_msg = (
                    result.get("error", "Failed to create room")
                    if result
                    else "Failed to create room"
                )
                yield rx.toast.error(error_msg)

        except Exception as e:
            yield rx.toast.error(f"Room creation failed: {e}")

        finally:
            self.loading_create = False

    async def update_room(self):
        """
        Update existing room with validation
        """
        if self.loading_update or not self.editing_room:
            return

        if not self._validate_form():
            return

        self.loading_update = True
        yield

        try:
            # Prepare updated data
            room_data = {
                "nome": self.form_name,
                "predio": self.form_building,
                "capacidade": self.form_capacity,
                "tipo_sala": self.form_room_type,
                "descrição": self.form_description,
                "equipamento": self.form_equipment,
            }

            # Update via service
            result = await RoomService.update_room(self.editing_room["id"], room_data)

            if result and result.get("success"):
                # Update local state
                room_id = self.editing_room["id"]
                for i, room in enumerate(self.rooms):
                    if room["id"] == room_id:
                        self.rooms[i] = {**room, **room_data}
                        break

                self.rooms = list(self.rooms)
                self.hide_create_form()
                yield rx.toast.success(
                    f"Room '{room_data['nome']}' updated successfully"
                )
            else:
                error_msg = (
                    result.get("error", "Failed to update room")
                    if result
                    else "Failed to update room"
                )
                yield rx.toast.error(error_msg)

        except Exception as e:
            yield rx.toast.error(f"Room update failed: {e}")

        finally:
            self.loading_update = False

    async def delete_room(self, room_id: int):
        """
        Delete room with confirmation
        """
        if self.loading_delete:
            return

        self.loading_delete = True
        yield

        try:
            result = await RoomService.delete_room(room_id)

            if result and result.get("success"):
                # Remove from local state defensively
                self.rooms = [r for r in self.rooms if r["id"] != room_id]
                self.rooms = list(self.rooms)

                yield rx.toast.success("Room deleted successfully")
            else:
                error_msg = (
                    result.get("error", "Failed to delete room")
                    if result
                    else "Failed to delete room"
                )
                yield rx.toast.error(error_msg)

        except Exception as e:
            yield rx.toast.error(f"Room deletion failed: {e}")

        finally:
            self.loading_delete = False

    def _validate_form(self) -> bool:
        """Validate room form data"""
        errors = []

        # Name validation
        if not self.form_name.strip():
            errors.append("Room name is required")
        elif len(self.form_name.strip()) < 2:
            errors.append("Room name must be at least 2 characters")

        # Building validation
        if not self.form_building.strip():
            errors.append("Building is required")

        # Capacity validation
        if self.form_capacity <= 0:
            errors.append("Capacity must be greater than 0")

        # Update error states
        self.form_name_error = (
            "Room name is required" if not self.form_name.strip() else ""
        )
        self.form_building_error = (
            "Building is required" if not self.form_building.strip() else ""
        )
        self.form_capacity_error = (
            "Capacity must be greater than 0" if self.form_capacity <= 0 else ""
        )

        if errors:
            yield rx.toast.error(f"Validation failed: {', '.join(errors[:2])}")
            return False

        return True

    def _clear_form(self):
        """Clear all form data and errors"""
        self.form_name = ""
        self.form_building = ""
        self.form_capacity = 0
        self.form_room_type = "Standard"
        self.form_description = ""
        self.form_equipment = []

        self.form_name_error = ""
        self.form_building_error = ""
        self.form_capacity_error = ""
