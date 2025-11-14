"""
Allocation State - Reflex Implementation
Manages room allocation operations with reactive updates

Following patterns from docs/Technical_Constraints_Patterns.md:
- ✅ Defensive mutation patterns
- ✅ Computed properties with @rx.var
- ✅ Loading states for async operations
- ✅ Toast notifications for user feedback
"""

import asyncio

import reflex as rx

from ...services.allocation_service import AllocationService


class AllocationState(rx.State):
    """Main allocation state with comprehensive allocation management"""

    # Loading states (following loading pattern - docs/Technical_Constraints_Patterns.md)
    loading_allocation: bool = False
    loading_import: bool = False
    loading_progress_check: bool = False

    # Current semester (shared global state)
    current_semester_id: int = 20251

    # Allocation data and results
    allocation_result: dict | None = None
    last_allocation_id: int | None = None

    # Progress tracking
    allocation_progress: int = 0
    import_progress: int = 0

    # Form data for allocation settings
    include_hard_rules: bool = True
    include_soft_preferences: bool = True
    max_iterations: int = 100

    @rx.var
    def allocation_completion_percentage(self) -> float:
        """Computed property for allocation completion - following @rx.var pattern"""
        if not self.allocation_result:
            return 0.0

        alloc_completed = self.allocation_result.get("allocations_completed", 0)
        total_demands = getattr(self, "_total_demands_for_semester", 1)

        return (
            min((alloc_completed / total_demands) * 100, 100.0)
            if total_demands > 0
            else 0.0
        )

    @rx.var
    def recent_allocation_summary(self) -> dict:
        """Computed summary of recent allocation results"""
        if not self.allocation_result:
            return {
                "status": "No allocation run",
                "allocations_completed": 0,
                "execution_time": 0,
                "timestamp": None,
            }

        result = self.allocation_result
        return {
            "status": "Success" if result.get("success") else "Failed",
            "allocations_completed": result.get("allocations_completed", 0),
            "execution_time": result.get("execution_time", 0),
            "timestamp": getattr(result, "timestamp", None),
        }

    @rx.var
    def conflict_count(self) -> int:
        """Computed conflict count from allocation results"""
        if not self.allocation_result:
            return 0

        # Sum conflicts from different phases
        phase1 = self.allocation_result.get("phase1_hard_rules", {}).get("conflicts", 0)
        phase3 = self.allocation_result.get("phase3_atomic_allocation", {}).get(
            "conflicts", 0
        )
        return phase1 + phase3

    @rx.var
    def is_allocating(self) -> bool:
        """Computed property indicating if allocation is in progress"""
        return self.loading_allocation

    async def run_autonomous_allocation(self, semester_id: int):
        """
        Execute autonomous allocation with Reflex async patterns

        Follows the loading state pattern from docs/Technical_Constraints_Patterns.md:
        - Prevent concurrent operations
        - Progressive UI updates with yield
        - Toast notifications for feedback
        - Defensive state management
        """
        # Prevent concurrent allocation runs
        if self.loading_allocation:
            yield rx.toast.info("Allocation already running...")
            return

        # Initialize loading state with reset
        self.loading_allocation = True
        self.allocation_progress = 0
        self.allocation_result = None
        self.error = ""
        yield

        try:
            # Progress update 1: Starting validation
            self.allocation_progress = 5
            yield rx.toast.info("Validating allocation parameters...")

            # Prepare allocation configuration from current state
            allocation_config = {
                "semester_id": semester_id,
                "include_hard_rules": self.include_hard_rules,
                "include_soft_preferences": self.include_soft_preferences,
                "max_iterations": self.max_iterations,
            }

            # Progress update 2: Starting allocation
            self.allocation_progress = 15
            yield rx.toast.info("Starting allocation process...")

            # Execute allocation using service layer (async wrapper)
            result = await AllocationService.execute_allocation(
                semester_id, allocation_config
            )

            # Store result with defensive reassignment
            self.allocation_result = dict(result)  # Defensive copy
            self.last_allocation_id = result.get("id")

            # Progress update based on allocation result
            if result.get("success"):
                self.allocation_progress = 95
                yield rx.toast.info("Allocation completed - preparing results...")

                # Get final statistics
                stats = await self._get_allocation_stats(semester_id)
                self._total_demands_for_semester = stats.get("total_demands", 1)

                # Final progress update
                self.allocation_progress = 100
                yield rx.toast.success(
                    f"Allocation completed: {result.get('allocations_completed', 0)} placements in {result.get('execution_time', 0):.1f}s"
                )

            else:
                # Allocation failed
                yield rx.toast.error(
                    f"Allocation failed: {result.get('error', 'Unknown error')}"
                )
                self.allocation_progress = 100

            # Update state defensively
            self.allocation_result = dict(self.allocation_result)

        except Exception as e:
            # Error handling with user feedback
            self.error = f"Allocation error: {str(e)}"
            self.allocation_progress = 100
            yield rx.toast.error(f"Allocation failed: {e}")

        finally:
            # ALWAYS reset loading state in finally block
            self.loading_allocation = False

    async def refresh_allocation_progress(self, semester_id: int):
        """Refresh allocation progress for current semester"""
        if self.loading_progress_check:
            return

        self.loading_progress_check = True

        try:
            progress = await AllocationService.get_allocation_progress(semester_id)

            # Update progress state with defensive reassignment
            if isinstance(progress, dict):
                self.allocation_progress = min(progress.get("percentage", 0), 100)
                # Trigger UI update through computed properties
                self.allocation_result = (
                    dict(self.allocation_result) if self.allocation_result else None
                )

        except Exception as e:
            yield rx.toast.error(f"Failed to refresh progress: {e}")

        finally:
            self.loading_progress_check = False

    async def import_demand_data(self, semester_id: int):
        """
        Import demand data from external API

        Follows async import pattern with progress tracking
        """
        if self.loading_import:
            yield rx.toast.info("Import already in progress...")
            return

        self.loading_import = True
        self.import_progress = 0
        yield

        try:
            # Progress: Starting
            self.import_progress = 10
            yield rx.toast.info("Connecting to Sistema de Oferta API...")

            # Progress: Fetching data
            self.import_progress = 25
            yield rx.toast.info("Fetching course demand data...")

            # Execute import using service layer
            from ...services.demand_service import DemandService

            import_result = await DemandService.import_from_api(semester_id)

            # Progress: Processing
            self.import_progress = 60
            yield rx.toast.info("Processing and validating data...")

            # Validate and save
            validation_result = await DemandService.validate_and_save(
                import_result, semester_id
            )

            # Progress: Saving
            self.import_progress = 90
            yield rx.toast.info("Saving to database...")

            # Final save operation
            await DemandService.finalize_import(semester_id, validation_result)

            self.import_progress = 100
            yield rx.toast.success(
                f"Import completed: {validation_result.get('courses_imported', 0)} courses"
            )

        except Exception as e:
            yield rx.toast.error(f"Import failed: {e}")

        finally:
            self.loading_import = False
            self.import_progress = 0

    def set_allocation_config(
        self, include_hard: bool, include_soft: bool, max_iter: int
    ):
        """Update allocation configuration settings"""
        self.include_hard_rules = include_hard
        self.include_soft_preferences = include_soft
        self.max_iterations = max_iter

    async def _get_allocation_stats(self, semester_id: int) -> dict:
        """Get allocation statistics for semester - helper method"""
        try:
            # This would integrate with your existing stats service
            from streamlit_legacy.src.services.statistics_report_service import (
                StatisticsReportService,
            )

            stats = await asyncio.to_thread(
                StatisticsReportService.get_allocation_stats_sync, semester_id
            )
            return stats or {"total_demands": 1}
        except Exception:
            # Fallback if service unavailable
            return {"total_demands": 1}

    def clear_allocation_result(self):
        """Clear current allocation result"""
        self.allocation_result = None
        self.last_allocation_id = None
        self.allocation_progress = 0
        # Defensive update
        self.allocation_result = (
            dict(self.allocation_result) if self.allocation_result else None
        )

    def reset_to_defaults(self):
        """Reset allocation settings to defaults"""
        self.include_hard_rules = True
        self.include_soft_preferences = True
        self.max_iterations = 100
        self.clear_allocation_result()
        yield rx.toast.info("Allocation settings reset to defaults")
