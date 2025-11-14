"""
Room Service - Reflex Async Wrapper
Handles room inventory operations with existing business logic

Following service layer patterns from docs/API_Interface_Specifications.md
"""

from typing import Any, Dict, List, Optional

from .base_service import BaseService


class RoomService(BaseService):
    """
    Reflex-compatible room service wrapper

    Integrates with existing room management logic
    """

    @staticmethod
    async def get_all_rooms() -> List[Dict[str, Any]]:
        """
        Get all rooms from database

        Returns:
            List of room dictionaries
        """
        try:
            # Import and use existing room repository
            from streamlit_legacy.src.repositories.sala import SalaRepository

            # Execute synchronously wrapped in async
            rooms = await RoomService.execute_async(
                lambda: SalaRepository.get_all_complete()
            )

            # Ensure we return a list
            if isinstance(rooms, list):
                return rooms
            else:
                return []

        except Exception as e:
            print(f"Error loading rooms: {e}")
            return []

    @staticmethod
    async def get_room_by_id(room_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific room by ID

        Args:
            room_id: Room ID to retrieve

        Returns:
            Room data dictionary or None if not found
        """
        try:
            from streamlit_legacy.src.repositories.sala import SalaRepository

            room = await RoomService.execute_async(
                lambda: SalaRepository.get_by_id(room_id)
            )

            return room if isinstance(room, dict) else None

        except Exception as e:
            print(f"Error getting room {room_id}: {e}")
            return None

    @staticmethod
    async def get_rooms_by_building(building_name: str) -> List[Dict[str, Any]]:
        """
        Get rooms for a specific building

        Args:
            building_name: Building name to filter by

        Returns:
            List of rooms in the specified building
        """
        try:
            from streamlit_legacy.src.repositories.sala import SalaRepository

            rooms = await RoomService.execute_async(
                lambda: SalaRepository.get_by_building(building_name)
            )

            return rooms if isinstance(rooms, list) else []

        except Exception as e:
            print(f"Error getting rooms for building '{building_name}': {e}")
            return []

    @staticmethod
    async def create_room(room_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new room

        Args:
            room_data: Room data dictionary

        Returns:
            Dict with "success", "room", and "message" keys
        """
        try:
            from streamlit_legacy.src.models.academic import Sala
            from streamlit_legacy.src.repositories.sala import SalaRepository

            # Validate room data
            validation_result = RoomService._validate_room_data(room_data)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"Validation failed: {', '.join(validation_result['errors'])}",
                }

            # Create room object
            room_obj = Sala(
                nome=room_data["nome"],
                predio=room_data["predio"],
                capacidade=room_data["capacidade"],
                tipo_sala=room_data.get("tipo_sala", "Standard"),
                descrição=room_data.get("descrição"),
                equipamento=room_data.get("equipamento", []),
            )

            # Save to database
            saved_room = await RoomService.execute_async(
                lambda: SalaRepository.create_room_with_validation(room_obj)
            )

            if saved_room:
                return {
                    "success": True,
                    "room": {
                        "id": saved_room.id if hasattr(saved_room, "id") else None,
                        "nome": saved_room.nome,
                        "predio": saved_room.predio,
                        "capacidade": saved_room.capacidade,
                        "tipo_sala": saved_room.tipo_sala,
                        "descrição": saved_room.descrição,
                        "equipamento": saved_room.equipamento or [],
                    },
                    "message": f"Room '{room_data['nome']}' created successfully",
                }
            else:
                return {"success": False, "error": "Failed to save room to database"}

        except Exception as e:
            return {"success": False, "error": f"Room creation failed: {str(e)}"}

    @staticmethod
    async def update_room(room_id: int, room_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing room

        Args:
            room_id: ID of room to update
            room_data: Updated room data

        Returns:
            Dict with "success" and "message" keys
        """
        try:
            from streamlit_legacy.src.repositories.sala import SalaRepository

            # Validate room data
            validation_result = RoomService._validate_room_data(room_data)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"Validation failed: {', '.join(validation_result['errors'])}",
                }

            # Update room
            updated = await RoomService.execute_async(
                lambda: SalaRepository.update_room(room_id, room_data)
            )

            if updated:
                return {
                    "success": True,
                    "message": f"Room '{room_data['nome']}' updated successfully",
                }
            else:
                return {"success": False, "error": "Room not found or update failed"}

        except Exception as e:
            return {"success": False, "error": f"Room update failed: {str(e)}"}

    @staticmethod
    async def delete_room(room_id: int) -> Dict[str, Any]:
        """
        Delete a room

        Args:
            room_id: ID of room to delete

        Returns:
            Dict with "success" and "message" keys
        """
        try:
            from streamlit_legacy.src.repositories.sala import SalaRepository

            # Check if room has active reservations first
            has_reservations = await RoomService.execute_async(
                lambda: SalaRepository.room_has_active_reservations(room_id)
            )

            if has_reservations:
                return {
                    "success": False,
                    "error": "Cannot delete room - it has active reservations",
                }

            # Delete room
            deleted = await RoomService.execute_async(
                lambda: SalaRepository.delete_room(room_id)
            )

            if deleted:
                return {"success": True, "message": "Room deleted successfully"}
            else:
                return {"success": False, "error": "Room not found or deletion failed"}

        except Exception as e:
            return {"success": False, "error": f"Room deletion failed: {str(e)}"}

    @staticmethod
    async def get_room_utilization(
        room_id: int, date_range: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Get utilization statistics for a room

        Args:
            room_id: Room ID to analyze
            date_range: Optional date range for analysis

        Returns:
            Dict with utilization data
        """
        try:
            from streamlit_legacy.src.repositories.sala import SalaRepository

            utilization = await RoomService.execute_async(
                lambda: SalaRepository.get_room_utilization_stats(room_id, date_range)
            )

            return (
                utilization
                if isinstance(utilization, dict)
                else {
                    "utilized_hours": 0,
                    "total_hours": 0,
                    "utilization_rate": 0,
                    "reservations_count": 0,
                }
            )

        except Exception as e:
            print(f"Error getting room utilization: {e}")
            return {
                "utilized_hours": 0,
                "total_hours": 0,
                "utilization_rate": 0,
                "reservations_count": 0,
            }

    @staticmethod
    async def search_rooms(query: str) -> List[Dict[str, Any]]:
        """
        Search rooms by name, building, or description

        Args:
            query: Search query string

        Returns:
            List of matching rooms
        """
        try:
            from streamlit_legacy.src.repositories.sala import SalaRepository

            rooms = await RoomService.execute_async(
                lambda: SalaRepository.search_rooms(query)
            )

            return rooms if isinstance(rooms, list) else []

        except Exception as e:
            print(f"Error searching rooms: {e}")
            return []

    @staticmethod
    def _validate_room_data(room_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate room data before creation/update

        Args:
            room_data: Room data to validate

        Returns:
            Dict with "valid" and "errors" keys
        """
        errors = []

        # Required fields
        if not room_data.get("nome", "").strip():
            errors.append("Room name is required")

        if not room_data.get("predio", "").strip():
            errors.append("Building is required")

        # Capacity validation
        capacity = room_data.get("capacidade", 0)
        if not isinstance(capacity, int) or capacity <= 0:
            errors.append("Capacity must be a positive integer")
        elif capacity > 10000:
            errors.append("Capacity cannot exceed 10,000")

        # Name uniqueness check would go here in a real implementation
        # For now, just basic validation

        return {"valid": len(errors) == 0, "errors": errors}
