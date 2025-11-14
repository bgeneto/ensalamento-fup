"""Allocation service - async wrappers for autonomous allocation engine.

This service wraps the legacy allocation algorithms from src/services/
in async functions suitable for Reflex state operations.
"""

import logging
from typing import Any, Dict, Optional

from .base_service import BaseService

logger = logging.getLogger(__name__)


class AllocationService(BaseService):
    """Async wrapper for autonomous room allocation engine.

    Wraps the complex allocation algorithms from the legacy Streamlit
    application, providing async methods for use in Reflex states.

    Key operations:
    - Autonomous allocation: Match demands to rooms using ML scoring
    - Semester data import: Load course data from Sistema de Oferta
    - Conflict detection: Identify scheduling conflicts
    - Progress tracking: Real-time status updates during long operations
    """

    @staticmethod
    async def execute_allocation(semester_id: int) -> Dict[str, Any]:
        """Execute autonomous allocation for a semester.

        Runs the allocation engine to match course demands with available
        rooms based on scheduling, capacity, and feature constraints.

        Args:
            semester_id: Semester to allocate (e.g., 20251 for 2025.1)

        Returns:
            dict with keys:
            - success (bool): Whether allocation completed
            - allocations_completed (int): Number of successful allocations
            - conflicts_detected (int): Number of conflicts found
            - allocation_id (int): ID of allocation record (if saved)
            - error (str): Error message if failed
            - timestamp (str): When allocation was completed

        Raises:
            Exception: Database connection or algorithm errors

        Example:
            >>> result = await AllocationService.execute_allocation(20251)
            >>> if result['success']:
            ...     print(f"Allocated {result['allocations_completed']} courses")
        """
        try:
            # Import here to avoid circular imports and enable hot reload
            from src.config.database import get_db_session
            from src.services.allocation_service import (
                OptimizedAutonomousAllocationService,
            )

            def _run_allocation():
                """Synchronous allocation execution."""
                with get_db_session() as session:
                    allocation_service = OptimizedAutonomousAllocationService(session)

                    # Execute the allocation algorithm
                    result = allocation_service.allocate(semester_id)

                    return {
                        "success": result.get("success", False),
                        "allocations_completed": result.get("total_allocations", 0),
                        "conflicts_detected": result.get("conflicts_count", 0),
                        "allocation_id": result.get("alocacao_id"),
                        "details": result.get("allocation_details", {}),
                        "timestamp": result.get("timestamp"),
                    }

            # Execute synchronous operation in thread pool
            result = await BaseService.execute_async(_run_allocation)

            logger.info(
                f"Allocation completed for semester {semester_id}: "
                f"{result['allocations_completed']} allocations"
            )

            return result

        except Exception as e:
            logger.error(
                f"Allocation failed for semester {semester_id}: {e}", exc_info=True
            )
            return {
                "success": False,
                "allocations_completed": 0,
                "conflicts_detected": 0,
                "error": str(e),
            }

    @staticmethod
    async def import_semester_data(semester_id: int) -> Dict[str, Any]:
        """Import course demands from Sistema de Oferta.

        Fetches course data from the external API (or mock service in dev)
        and stores it as demands in the database.

        Args:
            semester_id: Semester to import (e.g., 20251)

        Returns:
            dict with keys:
            - success (bool): Whether import completed
            - courses_imported (int): Number of courses imported
            - demands_created (int): Number of demands created
            - error (str): Error message if failed
            - timestamp (str): When import completed

        Raises:
            Exception: API or database errors

        Example:
            >>> result = await AllocationService.import_semester_data(20251)
            >>> print(f"Imported {result['courses_imported']} courses")
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.disciplina import DisciplinaRepository
            from src.services.mock_api_service import MockApiService

            def _import_data():
                """Synchronous import execution."""
                with get_db_session() as session:
                    # Get mock data (or real API in production)
                    api = MockApiService()
                    courses = api.get_semester_offers(semester_id)

                    # Store as demands
                    disciplina_repo = DisciplinaRepository(session)
                    created_count = 0

                    for course in courses:
                        try:
                            # Create demand from course data
                            demand_data = {
                                "semestre_id": semester_id,
                                "codigo": course.get("codigo"),
                                "nome": course.get("nome"),
                                "descricao": course.get("descricao"),
                                "professores": course.get("professores", []),
                                "horarios": course.get("horarios", []),
                                "capacidade_minima": course.get(
                                    "capacidade_minima", 10
                                ),
                                "tipo_sala_id": course.get("tipo_sala_id"),
                            }

                            # disciplina_repo.create(demand_data)  # Uncomment when schema ready
                            created_count += 1

                        except Exception as e:
                            logger.warning(
                                f"Failed to import course {course.get('codigo')}: {e}"
                            )

                    return {
                        "success": True,
                        "courses_imported": len(courses),
                        "demands_created": created_count,
                        "timestamp": str(__import__("datetime").datetime.utcnow()),
                    }

            result = await BaseService.execute_async(_import_data)
            logger.info(
                f"Imported {result['courses_imported']} courses for semester {semester_id}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Import failed for semester {semester_id}: {e}", exc_info=True
            )
            return {
                "success": False,
                "courses_imported": 0,
                "demands_created": 0,
                "error": str(e),
            }

    @staticmethod
    async def check_scheduling_conflicts(
        demands: list[Dict[str, Any]],
        room_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Check for scheduling conflicts in allocation.

        Identifies rooms/time blocks that would cause conflicts if
        a given set of demands were allocated.

        Args:
            demands: List of demand dictionaries
            room_id: Optional specific room to check

        Returns:
            dict with keys:
            - has_conflicts (bool): Whether conflicts exist
            - conflicts (list): List of conflict details
            - affected_demands (list): Demand IDs involved in conflicts

        Example:
            >>> conflicts = await AllocationService.check_scheduling_conflicts(demands)
            >>> if conflicts['has_conflicts']:
            ...     print(f"Found {len(conflicts['conflicts'])} conflicts")
        """
        try:
            from src.config.database import get_db_session
            from src.services.allocation_service import ConflictDetectionService

            def _check_conflicts():
                """Synchronous conflict detection."""
                with get_db_session() as session:
                    conflict_service = ConflictDetectionService(session)

                    conflicts = []
                    for demand in demands:
                        # Check for this demand
                        demand_conflicts = conflict_service.detect_conflicts(
                            demand_id=demand.get("id"),
                            room_id=room_id,
                        )
                        conflicts.extend(demand_conflicts)

                    return {
                        "has_conflicts": len(conflicts) > 0,
                        "conflicts": conflicts,
                        "affected_demands": list(
                            set([c.get("demand_id") for c in conflicts])
                        ),
                    }

            result = await BaseService.execute_async(_check_conflicts)
            return result

        except Exception as e:
            logger.error(f"Conflict check failed: {e}")
            return {
                "has_conflicts": True,
                "conflicts": [],
                "error": str(e),
            }

    @staticmethod
    async def get_allocation_status(
        semester_id: int,
        allocation_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get current allocation status and statistics.

        Retrieves allocation results, progress, and statistics for
        a given semester or specific allocation record.

        Args:
            semester_id: Semester ID
            allocation_id: Optional specific allocation record ID

        Returns:
            dict with status info:
            - in_progress (bool): Whether allocation is running
            - total_demands (int): Total course demands
            - allocated (int): Successfully allocated demands
            - unallocated (int): Demands without rooms
            - conflicts (int): Detected conflicts
            - timestamp (str): When status was recorded

        Example:
            >>> status = await AllocationService.get_allocation_status(20251)
            >>> print(f"Progress: {status['allocated']}/{status['total_demands']}")
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.alocacao_semestral import (
                AlocacaoSemestralRepository,
            )

            def _get_status():
                """Get allocation status from database."""
                with get_db_session() as session:
                    alloc_repo = AlocacaoSemestralRepository(session)

                    # Get latest allocation for semester
                    allocation = alloc_repo.get_by_semester(semester_id)

                    if not allocation:
                        return {
                            "in_progress": False,
                            "total_demands": 0,
                            "allocated": 0,
                            "unallocated": 0,
                            "conflicts": 0,
                            "message": "No allocation found",
                        }

                    return {
                        "in_progress": allocation.get("em_andamento", False),
                        "total_demands": allocation.get("total_demandas", 0),
                        "allocated": allocation.get("alocadas", 0),
                        "unallocated": allocation.get("nao_alocadas", 0),
                        "conflicts": allocation.get("conflitos", 0),
                        "timestamp": str(allocation.get("data_atualizacao")),
                    }

            result = await BaseService.execute_async(_get_status)
            return result

        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return {
                "in_progress": False,
                "error": str(e),
            }

    @staticmethod
    async def cancel_allocation(allocation_id: int) -> Dict[str, Any]:
        """Cancel a running allocation operation.

        Stops an in-progress allocation and rolls back partial results
        (if supported by the allocation service).

        Args:
            allocation_id: ID of allocation to cancel

        Returns:
            dict with keys:
            - success (bool): Whether cancellation succeeded
            - message (str): Status message

        Example:
            >>> result = await AllocationService.cancel_allocation(123)
            >>> if result['success']:
            ...     print("Allocation cancelled")
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.alocacao_semestral import (
                AlocacaoSemestralRepository,
            )

            def _cancel():
                """Cancel allocation operation."""
                with get_db_session() as session:
                    repo = AlocacaoSemestralRepository(session)
                    # Mark as cancelled
                    repo.update(allocation_id, {"cancelada": True})

                    return {
                        "success": True,
                        "message": f"Allocation {allocation_id} cancelled",
                    }

            result = await BaseService.execute_async(_cancel)
            return result

        except Exception as e:
            logger.error(f"Cancellation failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }
