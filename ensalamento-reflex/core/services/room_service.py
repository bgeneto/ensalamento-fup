"""Room service - async wrappers for room inventory management.

This service provides async operations for CRUD on the room inventory,
including filtering, capacity checks, and feature/characteristic queries.
"""

import logging
from typing import Any, Dict, List, Optional

from .base_service import BaseService

logger = logging.getLogger(__name__)


class RoomService(BaseService):
    """Async wrapper for room inventory management.

    Manages classroom CRUD operations, building/campus organization,
    room characteristics, and availability checking.

    Key operations:
    - Create/read/update/delete rooms
    - List rooms with filtering (building, capacity, characteristics)
    - Get room details and schedule availability
    - Manage room characteristics
    """

    @staticmethod
    async def get_all_rooms(
        building_id: Optional[int] = None,
        room_type_id: Optional[int] = None,
        capacity_min: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Load all rooms with optional filtering.

        Retrieves room inventory from database with optional filters
        for building, room type, and minimum capacity.

        Args:
            building_id: Optional filter by building (predio_id)
            room_type_id: Optional filter by room type (tipo_sala_id)
            capacity_min: Optional minimum capacity filter

        Returns:
            List of room dictionaries with keys:
            - id, nome, capacidade, predio_id, predio_nome,
              tipo_sala_id, tipo_sala_nome, caracteristicas (list)

        Example:
            >>> rooms = await RoomService.get_all_rooms(
            ...     building_id=1,
            ...     capacity_min=30
            ... )
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.sala import SalaRepository

            def _fetch_rooms():
                """Synchronous fetch from database."""
                with get_db_session() as session:
                    repo = SalaRepository(session)

                    # Get all rooms
                    rooms = repo.get_all()

                    # Apply filters
                    filtered_rooms = rooms

                    if building_id is not None:
                        filtered_rooms = [
                            r for r in filtered_rooms if r.predio_id == building_id
                        ]

                    if room_type_id is not None:
                        filtered_rooms = [
                            r for r in filtered_rooms if r.tipo_sala_id == room_type_id
                        ]

                    if capacity_min is not None:
                        filtered_rooms = [
                            r for r in filtered_rooms if r.capacidade >= capacity_min
                        ]

                    # Convert to dicts with related data
                    result = []
                    for room in filtered_rooms:
                        room_dict = {
                            "id": room.id,
                            "name": room.nome,
                            "capacity": room.capacidade,
                            "building_id": room.predio_id,
                            "building_name": room.predio.nome if room.predio else None,
                            "room_type_id": room.tipo_sala_id,
                            "room_type_name": (
                                room.tipo_sala.nome if room.tipo_sala else None
                            ),
                            "campus": (
                                room.predio.campus.nome
                                if room.predio and room.predio.campus
                                else None
                            ),
                            "characteristics": [
                                {
                                    "id": c.id,
                                    "name": c.nome,
                                }
                                for c in room.caracteristicas
                            ],
                            "created_at": str(room.created_at),
                        }
                        result.append(room_dict)

                    return result

            result = await BaseService.execute_async(_fetch_rooms)
            logger.info(f"Loaded {len(result)} rooms")

            return result

        except Exception as e:
            logger.error(f"Failed to load rooms: {e}", exc_info=True)
            return []

    @staticmethod
    async def get_room_details(room_id: int) -> Dict[str, Any]:
        """Get detailed information for a specific room.

        Args:
            room_id: Room ID

        Returns:
            dict with detailed room information including:
            - Basic info (name, capacity, building, type)
            - Characteristics (features available)
            - Schedule (allocated time blocks)
            - Constraints (professor preferences, etc.)

        Example:
            >>> details = await RoomService.get_room_details(1)
            >>> print(details['name'], details['capacity'])
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.sala import SalaRepository

            def _fetch_details():
                """Synchronous fetch."""
                with get_db_session() as session:
                    repo = SalaRepository(session)
                    room = repo.get_by_id(room_id)

                    if not room:
                        return {
                            "success": False,
                            "message": f"Room {room_id} not found",
                        }

                    return {
                        "success": True,
                        "id": room.id,
                        "name": room.nome,
                        "capacity": room.capacidade,
                        "building_id": room.predio_id,
                        "building_name": room.predio.nome if room.predio else None,
                        "room_type_id": room.tipo_sala_id,
                        "room_type_name": (
                            room.tipo_sala.nome if room.tipo_sala else None
                        ),
                        "campus": (
                            room.predio.campus.nome
                            if room.predio and room.predio.campus
                            else None
                        ),
                        "characteristics": [
                            {
                                "id": c.id,
                                "name": c.nome,
                            }
                            for c in room.caracteristicas
                        ],
                        "notes": room.observacoes or "",
                        "created_at": str(room.created_at),
                        "updated_at": str(room.updated_at),
                    }

            return await BaseService.execute_async(_fetch_details)

        except Exception as e:
            logger.error(f"Failed to get room details: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    async def create_room(room_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new room.

        Args:
            room_data: dict with keys:
            - nome (str, required): Room name
            - capacidade (int, required): Room capacity
            - predio_id (int, required): Building ID
            - tipo_sala_id (int, required): Room type ID
            - observacoes (str, optional): Notes about the room
            - caracteristicas (list, optional): List of characteristic IDs

        Returns:
            dict with keys:
            - success (bool): Whether creation succeeded
            - room_id (int): ID of created room (if success)
            - message (str): Status or error message

        Example:
            >>> data = {
            ...     "nome": "Sala A-101",
            ...     "capacidade": 40,
            ...     "predio_id": 1,
            ...     "tipo_sala_id": 1,
            ... }
            >>> result = await RoomService.create_room(data)
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.sala import SalaRepository
            from src.schemas.sala import SalaSchema

            def _create():
                """Synchronous creation."""
                with get_db_session() as session:
                    # Validate required fields
                    required_fields = [
                        "nome",
                        "capacidade",
                        "predio_id",
                        "tipo_sala_id",
                    ]
                    for field in required_fields:
                        if field not in room_data or room_data[field] is None:
                            raise ValueError(f"Missing required field: {field}")

                    # Check for duplicate name
                    repo = SalaRepository(session)
                    existing = repo.get_by_name(room_data["nome"])
                    if existing:
                        return {
                            "success": False,
                            "message": f"Room '{room_data['nome']}' already exists",
                        }

                    # Create room
                    schema = SalaSchema(**room_data)
                    created = repo.create(schema)

                    return {
                        "success": True,
                        "room_id": created.id,
                        "message": "Room created successfully",
                    }

            result = await BaseService.execute_async(_create)

            if result.get("success"):
                logger.info(f"Created room: {result['room_id']}")

            return result

        except Exception as e:
            logger.error(f"Room creation failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create room",
            }

    @staticmethod
    async def update_room(
        room_id: int,
        update_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a room.

        Args:
            room_id: ID of room to update
            update_data: Fields to update (see create_room for field names)

        Returns:
            dict with keys:
            - success (bool): Whether update succeeded
            - message (str): Status or error message
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.sala import SalaRepository

            def _update():
                """Synchronous update."""
                with get_db_session() as session:
                    repo = SalaRepository(session)
                    room = repo.get_by_id(room_id)

                    if not room:
                        return {
                            "success": False,
                            "message": f"Room {room_id} not found",
                        }

                    # Check for duplicate name if updating
                    if "nome" in update_data and update_data["nome"] != room.nome:
                        existing = repo.get_by_name(update_data["nome"])
                        if existing:
                            return {
                                "success": False,
                                "message": f"Room '{update_data['nome']}' already exists",
                            }

                    repo.update(room_id, update_data)

                    return {
                        "success": True,
                        "message": "Room updated successfully",
                    }

            result = await BaseService.execute_async(_update)

            if result.get("success"):
                logger.info(f"Updated room {room_id}")

            return result

        except Exception as e:
            logger.error(f"Room update failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    async def delete_room(room_id: int) -> Dict[str, Any]:
        """Delete a room.

        Only allows deletion if room has no active allocations.

        Args:
            room_id: ID of room to delete

        Returns:
            dict with keys:
            - success (bool): Whether deletion succeeded
            - message (str): Status or error message
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.sala import SalaRepository

            def _delete():
                """Synchronous deletion."""
                with get_db_session() as session:
                    repo = SalaRepository(session)
                    room = repo.get_by_id(room_id)

                    if not room:
                        return {
                            "success": False,
                            "message": f"Room {room_id} not found",
                        }

                    # Check for allocations
                    if room.alocacoes and len(room.alocacoes) > 0:
                        return {
                            "success": False,
                            "message": "Cannot delete room with active allocations",
                        }

                    repo.delete(room_id)

                    return {
                        "success": True,
                        "message": "Room deleted successfully",
                    }

            result = await BaseService.execute_async(_delete)

            if result.get("success"):
                logger.info(f"Deleted room {room_id}")

            return result

        except Exception as e:
            logger.error(f"Room deletion failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    async def get_room_schedule(
        room_id: int,
        semester_id: int,
    ) -> Dict[str, Any]:
        """Get room's allocated schedule for a semester.

        Returns the courses/demands allocated to this room for the
        specified semester, organized by day and time block.

        Args:
            room_id: Room ID
            semester_id: Semester ID

        Returns:
            dict with keys:
            - room_id, room_name, semester_id
            - schedule: list of allocated time blocks
            - availability: list of free time blocks
            - occupancy_rate: percentage of time booked

        Example:
            >>> schedule = await RoomService.get_room_schedule(1, 20251)
            >>> print(f"Occupancy: {schedule['occupancy_rate']}%")
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.alocacao_semestral import (
                AlocacaoSemestralRepository,
            )

            def _get_schedule():
                """Synchronous fetch."""
                with get_db_session() as session:
                    repo = AlocacaoSemestralRepository(session)

                    # Get allocations for this room and semester
                    allocations = repo.get_by_room_and_semester(room_id, semester_id)

                    schedule_blocks = [
                        {
                            "dia_semana": (
                                a.horario_bloco.dia_semana.nome
                                if a.horario_bloco
                                else None
                            ),
                            "horario": (
                                a.horario_bloco.nome if a.horario_bloco else None
                            ),
                            "course": a.demanda.disciplina.nome if a.demanda else None,
                            "professors": (
                                [p.nome for p in a.demanda.professores]
                                if a.demanda
                                else []
                            ),
                        }
                        for a in allocations
                    ]

                    # Calculate occupancy
                    total_blocks = 7 * 15  # 7 days, ~15 time blocks
                    occupied = len(schedule_blocks)
                    occupancy_rate = (
                        (occupied / total_blocks * 100) if total_blocks > 0 else 0
                    )

                    return {
                        "success": True,
                        "room_id": room_id,
                        "semester_id": semester_id,
                        "schedule": schedule_blocks,
                        "occupied_blocks": occupied,
                        "total_blocks": total_blocks,
                        "occupancy_rate": round(occupancy_rate, 1),
                    }

            return await BaseService.execute_async(_get_schedule)

        except Exception as e:
            logger.error(f"Failed to get schedule: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    async def add_characteristic(
        room_id: int,
        characteristic_id: int,
    ) -> Dict[str, Any]:
        """Add a characteristic to a room.

        Associates a feature/characteristic with the room (e.g., projector, whiteboard).

        Args:
            room_id: Room ID
            characteristic_id: Characteristic ID

        Returns:
            dict with keys:
            - success (bool): Whether addition succeeded
            - message (str): Status message
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.sala import SalaRepository

            def _add():
                """Synchronous addition."""
                with get_db_session() as session:
                    repo = SalaRepository(session)
                    room = repo.get_by_id(room_id)

                    if not room:
                        return {
                            "success": False,
                            "message": f"Room {room_id} not found",
                        }

                    # Add characteristic
                    repo.add_characteristic(room_id, characteristic_id)

                    return {
                        "success": True,
                        "message": "Characteristic added",
                    }

            result = await BaseService.execute_async(_add)

            if result.get("success"):
                logger.info(
                    f"Added characteristic {characteristic_id} to room {room_id}"
                )

            return result

        except Exception as e:
            logger.error(f"Failed to add characteristic: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    async def remove_characteristic(
        room_id: int,
        characteristic_id: int,
    ) -> Dict[str, Any]:
        """Remove a characteristic from a room.

        Args:
            room_id: Room ID
            characteristic_id: Characteristic ID

        Returns:
            dict with keys:
            - success (bool): Whether removal succeeded
            - message (str): Status message
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.sala import SalaRepository

            def _remove():
                """Synchronous removal."""
                with get_db_session() as session:
                    repo = SalaRepository(session)
                    repo.remove_characteristic(room_id, characteristic_id)

                    return {
                        "success": True,
                        "message": "Characteristic removed",
                    }

            result = await BaseService.execute_async(_remove)

            if result.get("success"):
                logger.info(
                    f"Removed characteristic {characteristic_id} from room {room_id}"
                )

            return result

        except Exception as e:
            logger.error(f"Failed to remove characteristic: {e}")
            return {
                "success": False,
                "error": str(e),
            }
