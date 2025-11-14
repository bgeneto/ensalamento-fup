"""
Allocation Service - Reflex Async Wrapper
Provides async interface to existing allocation business logic

Following service layer patterns from docs/API_Interface_Specifications.md
"""

from typing import Any, Dict, Optional

from .base_service import BaseService


class AllocationService(BaseService):
    """
    Reflex-compatible allocation service wrapper

    Integrates with existing business logic from streamlit-legacy
    """

    @staticmethod
    async def execute_allocation(
        semester_id: int, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute autonomous allocation asynchronously

        Args:
            semester_id: Semester to allocate
            config: Optional allocation configuration

        Returns:
            Dict with allocation results and statistics

        Integration: Uses existing OptimizedAutonomousAllocationService
        """
        # Default configuration
        if config is None:
            config = {
                "include_hard_rules": True,
                "include_soft_preferences": True,
                "max_iterations": 100,
            }

        try:
            # Import and use existing allocation service
            from streamlit_legacy.src.services.optimized_autonomous_allocation_service import (
                OptimizedAutonomousAllocationService,
            )

            # Execute allocation in thread pool to not block event loop
            allocation_service = OptimizedAutonomousAllocationService()

            result = await AllocationService.execute_async(
                allocation_service.execute_autonomous_allocation, semester_id
            )

            # Ensure result is serializable for Reflex state
            if isinstance(result, dict):
                # Add configuration info for tracking
                result["config_used"] = config
                return result
            else:
                # Handle unexpected result format
                return {
                    "success": False,
                    "error": "Allocation service returned unexpected result format",
                    "config_used": config,
                }

        except Exception as e:
            # Return structured error response
            return {
                "success": False,
                "error": str(e),
                "config_used": config,
                "allocations_completed": 0,
                "execution_time": 0,
            }

    @staticmethod
    async def get_allocation_progress(semester_id: int) -> Dict[str, Any]:
        """
        Get allocation progress for semester

        Args:
            semester_id: Semester to check

        Returns:
            Dict with progress information
        """
        try:
            from streamlit_legacy.src.services.optimized_autonomous_allocation_service import (
                OptimizedAutonomousAllocationService,
            )

            allocation_service = OptimizedAutonomousAllocationService()

            progress = await AllocationService.execute_async(
                allocation_service.get_allocation_progress, semester_id
            )

            # Ensure progress is in expected format
            if isinstance(progress, dict):
                return progress
            else:
                return {
                    "percentage": 0,
                    "total_demands": 0,
                    "allocated_demands": 0,
                    "status": "unknown",
                }

        except Exception as e:
            return {
                "percentage": 0,
                "total_demands": 0,
                "allocated_demands": 0,
                "status": "error",
                "error": str(e),
            }

    @staticmethod
    async def get_allocation_history(
        semester_id: int, limit: int = 10
    ) -> list[Dict[str, Any]]:
        """
        Get allocation history for semester

        Args:
            semester_id: Semester to get history for
            limit: Maximum number of history records to return

        Returns:
            List of allocation history records
        """
        try:
            # This would integrate with allocation history repository
            # For now, return empty list as allocation history may not be implemented yet
            return []

        except Exception as e:
            print(f"Error fetching allocation history: {e}")
            return []

    @staticmethod
    async def validate_allocation_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate allocation configuration

        Args:
            config: Allocation configuration to validate

        Returns:
            Dict with validation result {"valid": bool, "errors": list}
        """
        errors = []

        # Validate required fields
        if "semester_id" not in config:
            errors.append("semester_id is required")

        # Validate optional fields
        include_hard = config.get("include_hard_rules", True)
        include_soft = config.get("include_soft_preferences", True)
        max_iter = config.get("max_iterations", 100)

        if not isinstance(include_hard, bool):
            errors.append("include_hard_rules must be boolean")
        if not isinstance(include_soft, bool):
            errors.append("include_soft_preferences must be boolean")

        if not isinstance(max_iter, int) or max_iter < 1:
            errors.append("max_iterations must be positive integer")

        return {"valid": len(errors) == 0, "errors": errors}

    @staticmethod
    async def get_allocation_constraints(semester_id: int) -> Dict[str, Any]:
        """
        Get allocation constraints for semester

        Args:
            semester_id: Semester to get constraints for

        Returns:
            Dict with constraint information
        """
        try:
            # This would analyze current allocations and return constraint info
            # For now, return basic structure
            return {
                "semester_id": semester_id,
                "available_rooms": 0,  # Would compute from database
                "unallocated_demands": 0,  # Would compute from database
                "conflicts_detected": 0,  # Would check current conflicts
            }

        except Exception as e:
            print(f"Error fetching allocation constraints: {e}")
            return {"semester_id": semester_id, "error": str(e)}

    @staticmethod
    async def export_allocation_results(
        semester_id: int, format_type: str = "pdf"
    ) -> Dict[str, Any]:
        """
        Export allocation results

        Args:
            semester_id: Semester to export
            format_type: Export format ("pdf", "excel", "csv")

        Returns:
            Dict with export result {"success": bool, "data": bytes, "filename": str}
        """
        try:
            if format_type == "pdf":
                # Use existing PDF export service
                from streamlit_legacy.src.services.pdf_report_service import (
                    PdfReportService,
                )

                pdf_data = await AllocationService.execute_async(
                    PdfReportService.generate_allocation_report, semester_id
                )

                return {
                    "success": True,
                    "data": pdf_data,
                    "filename": f"allocation_report_{semester_id}.pdf",
                    "content_type": "application/pdf",
                }

            elif format_type == "excel":
                # This would implement Excel export
                return {"success": False, "error": "Excel export not yet implemented"}

            else:
                return {"success": False, "error": f"Unknown format: {format_type}"}

        except Exception as e:
            return {"success": False, "error": str(e)}
