"""Allocation engine state - Phase 2 Business Logic."""

import asyncio
import logging
from typing import Any, Dict, Optional

import reflex as rx

from core.services.allocation_service import AllocationService
from .base_state import BaseState

logger = logging.getLogger(__name__)


class AllocationState(BaseState):
    """Allocation operations state with progress tracking.
    
    Manages the autonomous room allocation process with:
    - Loading state to prevent concurrent executions
    - Progress tracking for long-running operations
    - Result caching and history
    """

    # Loading states for different operations
    loading_allocation: bool = False
    loading_import: bool = False

    # Progress tracking
    allocation_progress: int = 0
    import_progress: int = 0

    # Results and data
    allocation_result: Optional[Dict[str, Any]] = None
    last_semester_id: int = 20251  # Default current semester
    allocation_history: list[Dict[str, Any]] = []

    @rx.var
    def allocation_in_progress(self) -> bool:
        """Check if allocation is currently running."""
        return self.loading_allocation

    @rx.var
    def import_in_progress(self) -> bool:
        """Check if import is currently running."""
        return self.loading_import

    @rx.var
    def last_allocation_summary(self) -> Dict[str, Any]:
        """Computed summary of last allocation result."""
        if not self.allocation_result:
            return {
                "status": "No allocation executed",
                "allocated_count": 0,
                "conflicts_count": 0,
                "success": False,
            }

        return {
            "status": "Completed" if self.allocation_result.get("success") else "Failed",
            "allocated_count": self.allocation_result.get("allocations_completed", 0),
            "conflicts_count": self.allocation_result.get("conflicts_detected", 0),
            "success": self.allocation_result.get("success", False),
        }

    async def run_autonomous_allocation(self, semester_id: int):
        """Execute autonomous allocation with Reflex patterns.
        
        Follows the pattern:
        - Check if already running (prevent concurrent)
        - Set loading state with yield for UI update
        - Execute async operation with progress updates
        - Handle errors with toast feedback
        - Clean up in finally block
        
        Args:
            semester_id: Semester to allocate
        """
        # Prevent concurrent allocations
        if self.loading_allocation:
            yield rx.toast.info("Alocação já está em execução")
            return

        self.loading_allocation = True
        self.allocation_progress = 0
        self.error = ""
        yield  # Update UI to show loading state

        try:
            # Progress update 1: Starting allocation
            self.allocation_progress = 10
            yield rx.toast.info("Iniciando processo de alocação...")

            # TODO: Replace with actual service call
            # result = await AllocationService.execute_allocation_async(semester_id)
            # For now, simulate the operation
            result = await self._simulate_allocation(semester_id)

            if result.get("success"):
                # Progress update 2: Processing results
                self.allocation_progress = 90
                yield rx.toast.info("Processando resultados...")

                # Store result
                self.allocation_result = result
                self.last_semester_id = semester_id

                # Add to history (defensive reassignment)
                self.allocation_history.append({
                    "semester_id": semester_id,
                    "timestamp": result.get("timestamp"),
                    "allocations_completed": result.get("allocations_completed", 0),
                    "success": True,
                })
                self.allocation_history = list(self.allocation_history)

                # Progress complete
                self.allocation_progress = 100
                yield rx.toast.success(
                    f"Alocação concluída: {result['allocations_completed']} aulas alocadas"
                )

            else:
                error_msg = result.get("error", "Erro desconhecido")
                yield rx.toast.error(f"Falha na alocação: {error_msg}")
                # Add failed attempt to history
                self.allocation_history.append({
                    "semester_id": semester_id,
                    "timestamp": result.get("timestamp"),
                    "success": False,
                    "error": error_msg,
                })
                self.allocation_history = list(self.allocation_history)

        except Exception as e:
            error_msg = f"Erro na alocação: {str(e)}"
            self.error = error_msg
            yield rx.toast.error(error_msg)
            logger.error("Allocation execution failed", exc_info=True)

            # Add error to history
            self.allocation_history.append({
                "semester_id": semester_id,
                "success": False,
                "error": str(e),
            })
            self.allocation_history = list(self.allocation_history)

        finally:
            self.loading_allocation = False
            self.allocation_progress = 0

    async def import_semester_data(self, semester_id: int):
        """Import semester data from external source with progress tracking.
        
        Phases:
        1. Fetch from API (25%)
        2. Validate and process (50%)
        3. Save to database (75%)
        4. Finalize (100%)
        
        Args:
            semester_id: Semester to import
        """
        if self.loading_import:
            yield rx.toast.info("Importação já está em execução")
            return

        self.loading_import = True
        self.import_progress = 0
        yield

        try:
            # Phase 1: Fetch from API
            self.import_progress = 25
            yield rx.toast.info("Buscando dados do Sistema de Oferta...")

            # TODO: Replace with actual service call
            # import_data = await OfertaApiService.fetch_semester(semester_id)
            import_data = await self._simulate_api_fetch(semester_id)

            # Phase 2: Process and validate
            self.import_progress = 50
            yield rx.toast.info("Processando dados...")

            # TODO: Process data through service
            # processed = await ProcessingService.process_semester(import_data)
            processed = import_data  # Simulated

            # Phase 3: Save to database
            self.import_progress = 75
            yield rx.toast.info("Salvando no banco de dados...")

            # TODO: Replace with actual service call
            # save_result = await SemesterService.save_imported_data(semester_id, processed)
            save_result = {"success": True, "items_saved": len(processed)}

            # Phase 4: Complete
            self.import_progress = 100
            yield rx.toast.success(
                f"Importação concluída: {save_result['items_saved']} itens salvos"
            )

        except Exception as e:
            yield rx.toast.error(f"Importação falhou: {e}")
            logger.error("Semester import failed", exc_info=True)

        finally:
            self.loading_import = False
            self.import_progress = 0

    def clear_allocation_history(self):
        """Clear allocation history."""
        self.allocation_history = []

    def clear_last_result(self):
        """Clear the last allocation result."""
        self.allocation_result = None

    # Simulated methods for development (replace with real service calls)

    async def _simulate_allocation(self, semester_id: int) -> Dict[str, Any]:
        """Execute allocation using AllocationService.
        
        Calls the async AllocationService.execute_allocation() which wraps
        the legacy OptimizedAutonomousAllocationService allocation engine.
        """
        try:
            # Call the real service
            result = await AllocationService.execute_allocation(semester_id)
            return result
        except Exception as e:
            logger.error(f"Allocation service error: {e}")
            return {
                "success": False,
                "error": str(e),
                "semester_id": semester_id,
            }

    async def _simulate_api_fetch(self, semester_id: int) -> list[Dict[str, Any]]:
        """Simulate API fetch for development.
        
        Replace with actual OfertaApiService.fetch_semester() call.
        """
        await asyncio.sleep(1)  # Simulate network delay

        return [
            {
                "id": 1,
                "course_code": "MAT123",
                "title": "Cálculo I",
                "professor": "Dr. Silva",
            },
            {
                "id": 2,
                "course_code": "FIS101",
                "title": "Física I",
                "professor": "Dra. Santos",
            },
        ]
