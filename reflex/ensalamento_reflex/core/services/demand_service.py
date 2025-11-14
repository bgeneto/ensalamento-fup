"""
Demand Service - Reflex Async Wrapper
Handles demand data import from external APIs

Following service layer patterns from docs/API_Interface_Specifications.md
"""

from typing import Any, Dict, List

from .base_service import BaseService


class DemandService(BaseService):
    """
    Reflex-compatible demand import service wrapper

    Integrates with existing Sistema de Oferta API logic
    """

    @staticmethod
    async def import_from_api(semester_id: int) -> List[Dict[str, Any]]:
        """
        Import demand data from Sistema de Oferta API

        Args:
            semester_id: Semester to import demand for

        Returns:
            List of demand/course data from API
        """
        try:
            # Use existing Oferta API service
            from streamlit_legacy.src.services.oferta_api import OfertaApiService

            # Execute API call asynchronously
            demand_data = await DemandService.execute_async(
                OfertaApiService.get_demand_for_semester, semester_id
            )

            # Ensure it's a list format
            if isinstance(demand_data, list):
                return demand_data
            elif isinstance(demand_data, dict):
                # Handle single item response
                return [demand_data]
            else:
                # Handle unexpected format
                print(f"Warning: Unexpected demand data format: {type(demand_data)}")
                return []

        except Exception as e:
            print(f"Error importing demand data: {e}")
            # Return empty list instead of crashing
            return []

    @staticmethod
    async def validate_and_save(
        import_result: List[Dict[str, Any]], semester_id: int
    ) -> Dict[str, Any]:
        """
        Validate imported demand data and save to database

        Args:
            import_result: Raw data from API import
            semester_id: Semester to associate data with

        Returns:
            Dict with validation and save results
        """
        validation_errors = []
        validation_warnings = []
        saved_count = 0

        try:
            # Validate data structure
            if not isinstance(import_result, list):
                validation_errors.append("Import result must be a list")
                return {
                    "valid": False,
                    "errors": validation_errors,
                    "warnings": validation_warnings,
                    "saved": saved_count,
                }

            if len(import_result) == 0:
                validation_warnings.append("No demand data to import")

            # Validate each item
            for i, item in enumerate(import_result):
                if not isinstance(item, dict):
                    validation_errors.append(f"Item {i} must be a dictionary")
                    continue

                # Required field validation
                required_fields = [
                    "codigo_disciplina",
                    "turma_disciplina",
                    "horario_sigaa_bruto",
                ]
                for field in required_fields:
                    if field not in item or item[field] is None:
                        validation_errors.append(
                            f"Item {i} ({item.get('codigo_disciplina', 'unknown')}): missing required field '{field}'"
                        )

            if validation_errors:
                return {
                    "valid": False,
                    "errors": validation_errors,
                    "warnings": validation_warnings,
                    "saved": saved_count,
                }

            # Save validated data

            saved_count = await DemandService.execute_async(
                DemandService._save_demand_data_sync, import_result, semester_id
            )

        except Exception as e:
            validation_errors.append(f"Save operation failed: {str(e)}")

        return {
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "warnings": validation_warnings,
            "saved": saved_count,
            "total_imported": len(import_result),
        }

    @staticmethod
    def _save_demand_data_sync(
        demand_data: List[Dict[str, Any]], semester_id: int
    ) -> int:
        """
        Synchronous helper to save demand data to database

        Args:
            demand_data: Validated demand data
            semester_id: Semester to associate with

        Returns:
            Number of items saved
        """
        from streamlit_legacy.src.config.database import get_db_session
        from streamlit_legacy.src.models.academic import Demanda

        saved_count = 0

        with get_db_session() as session:
            # Clear existing demand data for this semester (if needed)
            # session.query(Demanda).filter(Demanda.semestre_id == semester_id).delete()

            # Save new demand data
            for item in demand_data:
                try:
                    # Create demand object
                    demand_obj = Demanda(
                        semestre_id=semester_id,
                        codigo_disciplina=item["codigo_disciplina"],
                        nome_disciplina=item.get("nome_disciplina"),
                        turma_disciplina=item["turma_disciplina"],
                        vagas_disciplina=item.get("vagas_disciplina", 0),
                        horario_sigaa_bruto=item["horario_sigaa_bruto"],
                        professores_disciplina=item.get("professores_disciplina", ""),
                        id_oferta_externo=item.get("id_oferta_externo"),
                        codigo_curso=item.get("codigo_curso"),
                    )

                    session.add(demand_obj)
                    saved_count += 1

                except Exception as e:
                    print(f"Error saving demand item: {e}")
                    continue

            session.commit()

        return saved_count

    @staticmethod
    async def finalize_import(
        semester_id: int, validation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Finalize import process and update semester metadata

        Args:
            semester_id: Semester that was imported
            validation_result: Results from validation/save process

        Returns:
            Dict with final results
        """
        try:
            # Update semester status or metadata

            await DemandService.execute_async(
                DemandService._update_semester_import_status,
                semester_id,
                validation_result,
            )

            return {
                "success": True,
                "semester_id": semester_id,
                "import_summary": validation_result,
                "message": f"Import completed for semester {semester_id}",
            }

        except Exception as e:
            return {"success": False, "semester_id": semester_id, "error": str(e)}

    @staticmethod
    def _update_semester_import_status(
        semester_id: int, validation_result: Dict[str, Any]
    ):
        """
        Update semester record with import completion status

        Args:
            semester_id: Semester to update
            validation_result: Import validation results
        """
        from streamlit_legacy.src.config.database import get_db_session
        from streamlit_legacy.src.models.academic import Semestre

        with get_db_session() as session:
            semester = (
                session.query(Semestre).filter(Semestre.id == semester_id).first()
            )

            if semester:
                # Could add import timestamp, success flag, etc.
                # For now, just ensure semester exists
                pass

            session.commit()

    @staticmethod
    async def get_demand_summary(semester_id: int) -> Dict[str, Any]:
        """
        Get summary of demand data for semester

        Args:
            semester_id: Semester to get summary for

        Returns:
            Dict with demand statistics
        """
        try:

            summary = await DemandService.execute_async(
                DemandService._get_demand_summary_sync, semester_id
            )

            return summary

        except Exception as e:
            return {
                "semester_id": semester_id,
                "error": str(e),
                "total_demands": 0,
                "courses_imported": 0,
            }

    @staticmethod
    def _get_demand_summary_sync(semester_id: int) -> Dict[str, Any]:
        """
        Get demand summary synchronously

        Args:
            semester_id: Semester to summarize

        Returns:
            Dict with summary statistics
        """
        from streamlit_legacy.src.config.database import get_db_session

        with get_db_session() as session:
            from streamlit_legacy.src.repositories.disciplina import (
                DisciplinaRepository,
            )

            repo = DisciplinaRepository(session)

            total_demands = len(repo.get_by_semester(semester_id))
            unique_courses = len(
                set(d["codigo_disciplina"] for d in repo.get_by_semester(semester_id))
            )

            return {
                "semester_id": semester_id,
                "total_demands": total_demands,
                "courses_imported": unique_courses,
                "last_updated": None,  # Could track timestamps
            }

    @staticmethod
    async def clear_demand_data(semester_id: int) -> Dict[str, Any]:
        """
        Clear all demand data for a semester (before re-import)

        Args:
            semester_id: Semester to clear

        Returns:
            Dict with deletion results
        """
        try:

            deleted_count = await DemandService.execute_async(
                DemandService._clear_demand_data_sync, semester_id
            )

            return {
                "success": True,
                "semester_id": semester_id,
                "deleted_count": deleted_count,
                "message": f"Cleared {deleted_count} demand records",
            }

        except Exception as e:
            return {"success": False, "semester_id": semester_id, "error": str(e)}

    @staticmethod
    def _clear_demand_data_sync(semester_id: int) -> int:
        """
        Clear demand data synchronously

        Args:
            semester_id: Semester to clear

        Returns:
            Number of records deleted
        """
        from streamlit_legacy.src.config.database import get_db_session
        from streamlit_legacy.src.models.academic import Demanda

        with get_db_session() as session:
            deleted_count = (
                session.query(Demanda)
                .filter(Demanda.semestre_id == semester_id)
                .delete()
            )

            session.commit()
            return deleted_count
