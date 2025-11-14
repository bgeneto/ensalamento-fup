"""
Reservation Service - Reflex Async Wrapper
Handles room reservation operations with conflict detection

Following service layer patterns from docs/API_Interface_Specifications.md
"""

from typing import Any, Dict, List

from .base_service import BaseService


class ReservationService(BaseService):
    """
    Reflex-compatible reservation service wrapper

    Integrates with existing reservation management logic
    """

    @staticmethod
    async def get_all_reservations() -> List[Dict[str, Any]]:
        """
        Get all reservations from database

        Returns:
            List of reservation dictionaries
        """
        try:
            # Import and use existing reservation repository
            from streamlit_legacy.src.repositories.reserva_ocorrencia import (
                ReservaOcorrenciaRepository,
            )

            # Execute synchronously wrapped in async
            reservations = await ReservationService.execute_async(
                lambda: ReservaOcorrenciaRepository.get_all_with_details()
            )

            # Ensure we return a list
            if isinstance(reservations, list):
                return reservations
            else:
                return []

        except Exception as e:
            print(f"Error loading reservations: {e}")
            return []

    @staticmethod
    async def get_reservation_by_id(reservation_id: int) -> Dict[str, Any] | None:
        """
        Get a specific reservation by ID

        Args:
            reservation_id: Reservation ID to retrieve

        Returns:
            Reservation data or None if not found
        """
        try:
            from streamlit_legacy.src.repositories.reserva_ocorrencia import (
                ReservaOcorrenciaRepository,
            )

            reservation = await ReservationService.execute_async(
                lambda: ReservaOcorrenciaRepository.get_by_id_with_details(
                    reservation_id
                )
            )

            return reservation if isinstance(reservation, dict) else None

        except Exception as e:
            print(f"Error getting reservation {reservation_id}: {e}")
            return None

    @staticmethod
    async def check_conflicts(conflict_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for scheduling conflicts

        Args:
            conflict_data: Dict with reservation details to check

        Returns:
            List of conflicting reservations
        """
        try:
            from streamlit_legacy.src.services.reserva_evento_service import (
                ReservaEventoService,
            )

            # Execute conflict check
            conflicts = await ReservationService.execute_async(
                lambda: ReservaEventoService.check_reservation_conflicts(conflict_data)
            )

            # Ensure we return a list
            if isinstance(conflicts, list):
                return conflicts
            else:
                return []

        except Exception as e:
            print(f"Error checking conflicts: {e}")
            return []

    @staticmethod
    async def create_reservation(reservation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new reservation with validation

        Args:
            reservation_data: Reservation data dictionary

        Returns:
            Dict with "success", "reservation", and "message" keys
        """
        try:
            from streamlit_legacy.src.services.reserva_evento_service import (
                ReservaEventoService,
            )

            # Validate reservation data
            validation_result = ReservationService._validate_reservation_data(
                reservation_data
            )
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"Validation failed: {', '.join(validation_result['errors'])}",
                }

            # Check for conflicts first
            conflict_data = {
                "data_reserva": reservation_data["data_reserva"],
                "bloqueio_horário": reservation_data["bloqueio_horário"],
                "duração_horas": reservation_data["duração_horas"],
                "sala_id": reservation_data["sala_id"],
            }

            conflicts = await ReservationService.check_conflicts(conflict_data)

            if conflicts:
                return {
                    "success": False,
                    "error": f"Time conflict detected: {len(conflicts)} conflicting reservations",
                    "conflicts": conflicts,
                }

            # Create reservation
            result = await ReservationService.execute_async(
                lambda: ReservaEventoService.create_reservation(reservation_data)
            )

            if result and isinstance(result, dict) and result.get("success"):
                return {
                    "success": True,
                    "reservation": result,
                    "message": "Reservation created successfully",
                }
            else:
                return {"success": False, "error": "Failed to create reservation"}

        except Exception as e:
            return {"success": False, "error": f"Reservation creation failed: {str(e)}"}

    @staticmethod
    async def update_reservation(
        reservation_id: int, reservation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing reservation

        Args:
            reservation_id: ID of reservation to update
            reservation_data: Updated reservation data

        Returns:
            Dict with "success" and "message" keys
        """
        try:
            from streamlit_legacy.src.services.reserva_evento_service import (
                ReservaEventoService,
            )

            # Validate reservation data
            validation_result = ReservationService._validate_reservation_data(
                reservation_data
            )
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"Validation failed: {', '.join(validation_result['errors'])}",
                }

            # Update reservation
            result = await ReservationService.execute_async(
                lambda: ReservaEventoService.update_reservation(
                    reservation_id, reservation_data
                )
            )

            if result and isinstance(result, dict) and result.get("success"):
                return {"success": True, "message": "Reservation updated successfully"}
            else:
                return {
                    "success": False,
                    "error": "Reservation not found or update failed",
                }

        except Exception as e:
            return {"success": False, "error": f"Reservation update failed: {str(e)}"}

    @staticmethod
    async def delete_reservation(reservation_id: int) -> Dict[str, Any]:
        """
        Delete a reservation

        Args:
            reservation_id: ID of reservation to delete

        Returns:
            Dict with "success" and "message" keys
        """
        try:
            from streamlit_legacy.src.services.reserva_evento_service import (
                ReservaEventoService,
            )

            # Delete reservation
            result = await ReservationService.execute_async(
                lambda: ReservaEventoService.delete_reservation(reservation_id)
            )

            if result and isinstance(result, dict) and result.get("success"):
                return {"success": True, "message": "Reservation deleted successfully"}
            else:
                return {
                    "success": False,
                    "error": "Reservation not found or deletion failed",
                }

        except Exception as e:
            return {"success": False, "error": f"Reservation deletion failed: {str(e)}"}

    @staticmethod
    async def update_reservation_status(
        reservation_id: int, status: str
    ) -> Dict[str, Any]:
        """
        Update reservation status (approve/cancel)

        Args:
            reservation_id: ID of reservation
            status: New status ("Aprovada", "Cancelada", etc.)

        Returns:
            Dict with "success" and "message" keys
        """
        try:
            from streamlit_legacy.src.services.reserva_evento_service import (
                ReservaEventoService,
            )

            # Update status
            result = await ReservationService.execute_async(
                lambda: ReservaEventoService.update_reservation_status(
                    reservation_id, status
                )
            )

            if result and isinstance(result, dict) and result.get("success"):
                return {
                    "success": True,
                    "message": f"Reservation status updated to '{status}'",
                }
            else:
                return {
                    "success": False,
                    "error": "Reservation not found or status update failed",
                }

        except Exception as e:
            return {"success": False, "error": f"Status update failed: {str(e)}"}

    @staticmethod
    async def get_reservations_by_room(
        room_id: int, date_range: Dict[str, str] | None = None
    ) -> List[Dict[str, Any]]:
        """
        Get reservations for a specific room

        Args:
            room_id: Room ID
            date_range: Optional date range {"start": "2023-01-01", "end": "2023-12-31"}

        Returns:
            List of reservations for the room
        """
        try:
            from streamlit_legacy.src.repositories.reserva_ocorrencia import (
                ReservaOcorrenciaRepository,
            )

            reservations = await ReservationService.execute_async(
                lambda: ReservaOcorrenciaRepository.get_by_room(room_id, date_range)
            )

            return reservations if isinstance(reservations, list) else []

        except Exception as e:
            print(f"Error getting reservations for room {room_id}: {e}")
            return []

    @staticmethod
    async def get_reservations_by_requester(
        requester_name: str,
    ) -> List[Dict[str, Any]]:
        """
        Get reservations by requester name

        Args:
            requester_name: Name of the person who made the reservation

        Returns:
            List of reservations by the requester
        """
        try:
            from streamlit_legacy.src.repositories.reserva_ocorrencia import (
                ReservaOcorrenciaRepository,
            )

            reservations = await ReservationService.execute_async(
                lambda: ReservaOcorrenciaRepository.get_by_requester(requester_name)
            )

            return reservations if isinstance(reservations, list) else []

        except Exception as e:
            print(f"Error getting reservations for requester {requester_name}: {e}")
            return []

    @staticmethod
    async def get_reservations_by_date_range(
        start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Get reservations within a date range

        Args:
            start_date: Start date in "YYYY-MM-DD" format
            end_date: End date in "YYYY-MM-DD" format

        Returns:
            List of reservations in the date range
        """
        try:
            date_range = {"start": start_date, "end": end_date}
            from streamlit_legacy.src.repositories.reserva_ocorrencia import (
                ReservaOcorrenciaRepository,
            )

            reservations = await ReservationService.execute_async(
                lambda: ReservaOcorrenciaRepository.get_by_date_range(date_range)
            )

            return reservations if isinstance(reservations, list) else []

        except Exception as e:
            print(
                f"Error getting reservations for date range {start_date} to {end_date}: {e}"
            )
            return []

    @staticmethod
    def _validate_reservation_data(reservation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate reservation data before creation/update

        Args:
            reservation_data: Reservation data to validate

        Returns:
            Dict with "valid" and "errors" keys
        """
        errors = []

        # Required fields
        if not reservation_data.get("titulo_evento", "").strip():
            errors.append("Event title is required")

        if not reservation_data.get("data_reserva"):
            errors.append("Reservation date is required")

        if not reservation_data.get("bloqueio_horário"):
            errors.append("Time block selection is required")

        if not reservation_data.get("sala_id"):
            errors.append("Room selection is required")

        # Validate room capacity vs attendees
        room_id = reservation_data.get("sala_id")
        attendees = reservation_data.get("número_participantes", 1)

        if room_id and attendees:
            # Check room capacity (would need to get room info)
            # For now, basic date validation
            pass

        # Basic date validation
        date_str = reservation_data.get("data_reserva", "")
        if date_str:
            try:
                # Parse YYYY-MM-DD format
                year, month, day = map(int, date_str.split("-"))
                import datetime

                reservation_date = datetime.date(year, month, day)

                # Check if date is not in the past
                if reservation_date < datetime.date.today():
                    errors.append("Cannot make reservations for past dates")

            except ValueError:
                errors.append("Invalid date format")

        return {"valid": len(errors) == 0, "errors": errors}

    @staticmethod
    async def generate_reservation_report(reservation_id: int) -> Dict[str, Any]:
        """
        Generate a detailed report for a reservation

        Args:
            reservation_id: ID of reservation to report on

        Returns:
            Dict with comprehensive reservation details
        """
        try:
            reservation = await ReservationService.get_reservation_by_id(reservation_id)

            if not reservation:
                return {"error": "Reservation not found"}

            # Add conflict information
            conflicts = await ReservationService.check_conflicts(
                {
                    "data_reserva": reservation.get("data_reserva"),
                    "bloqueio_horário": reservation.get("bloqueio_horário"),
                    "duração_horas": reservation.get("duração_horas", 1),
                    "sala_id": reservation.get("sala_id"),
                }
            )

            report = {
                **reservation,
                "conflicts": conflicts,
                "conflict_count": len(conflicts),
                "generated_at": "2025-11-14T13:30:00Z",  # Should use current timestamp
            }

            return report

        except Exception as e:
            return {"error": f"Report generation failed: {str(e)}"}
