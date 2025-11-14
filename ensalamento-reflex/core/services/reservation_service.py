"""Reservation service - async wrappers for event scheduling.

This service provides async operations for creating, updating, and managing
event-specific room reservations with conflict detection.
"""

import logging
from typing import Any, Dict, Optional

from .base_service import BaseService

logger = logging.getLogger(__name__)


class ReservationService(BaseService):
    """Async wrapper for sporadic reservation (event scheduling) system.

    Manages one-off room reservations for events with automatic
    conflict detection and approval workflows.

    Key operations:
    - Create/update/delete reservations
    - Check for time and room conflicts
    - List reservations with filtering
    - Approve/reject reservations
    """

    @staticmethod
    async def get_all_reservations(
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list[Dict[str, Any]]:
        """Load all reservations with optional filtering.

        Retrieves event reservations from the database, optionally
        filtered by status and date range.

        Args:
            status: Filter by status (e.g., "Aprovada", "Pendente", "Rejeitada")
            date_from: Start date (ISO format: YYYY-MM-DD)
            date_to: End date (ISO format: YYYY-MM-DD)

        Returns:
            List of reservation dictionaries with keys:
            - id, titulo_evento, sala_id, data_reserva, horario_inicio,
              horario_fim, nome_solicitante, status, motivo_rejeicao

        Example:
            >>> reservations = await ReservationService.get_all_reservations(
            ...     status="Aprovada",
            ...     date_from="2025-11-15"
            ... )
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.reserva_esporadica import ReservaEsporadicaRepository

            def _fetch_reservations():
                """Synchronous fetch from database."""
                with get_db_session() as session:
                    repo = ReservaEsporadicaRepository(session)

                    # Build filter
                    filters = {}
                    if status:
                        filters["status"] = status
                    if date_from:
                        filters["data_reserva_min"] = date_from
                    if date_to:
                        filters["data_reserva_max"] = date_to

                    # Get filtered reservations
                    reservations = (
                        repo.get_all(**filters) if filters else repo.get_all()
                    )

                    # Convert ORM to dicts
                    return [
                        {
                            "id": r.id,
                            "titulo_evento": r.titulo_evento,
                            "sala_id": r.sala_id,
                            "sala_nome": r.sala.nome if r.sala else None,
                            "data_reserva": str(r.data_reserva),
                            "horario_inicio": str(r.horario_inicio),
                            "horario_fim": str(r.horario_fim),
                            "nome_solicitante": r.nome_solicitante,
                            "email_solicitante": r.email_solicitante,
                            "status": r.status,
                            "motivo_rejeicao": r.motivo_rejeicao,
                            "criada_em": str(r.created_at),
                        }
                        for r in reservations
                    ]

            result = await BaseService.execute_async(_fetch_reservations)
            logger.info(f"Loaded {len(result)} reservations")

            return result

        except Exception as e:
            logger.error(f"Failed to load reservations: {e}", exc_info=True)
            return []

    @staticmethod
    async def create_reservation(reservation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new event reservation.

        Creates a reservation record and automatically checks for conflicts.
        Reservations start in "Pendente" (Pending) status for admin approval.

        Args:
            reservation_data: dict with keys:
            - titulo_evento (str, required): Event title
            - sala_id (int, required): Room ID
            - data_reserva (str, required): Date (ISO format)
            - horario_inicio (str, required): Start time (HH:MM)
            - horario_fim (str, required): End time (HH:MM)
            - nome_solicitante (str, required): Requester name
            - email_solicitante (str, required): Requester email
            - descricao (str, optional): Event description

        Returns:
            dict with keys:
            - success (bool): Whether creation succeeded
            - reservation_id (int): ID of created reservation (if success)
            - conflicts (list): List of conflicting reservations (if any)
            - message (str): Status or error message

        Example:
            >>> data = {
            ...     "titulo_evento": "Seminário de IA",
            ...     "sala_id": 1,
            ...     "data_reserva": "2025-11-20",
            ...     "horario_inicio": "14:00",
            ...     "horario_fim": "15:30",
            ...     "nome_solicitante": "Prof. Silva",
            ...     "email_solicitante": "silva@unb.br",
            ... }
            >>> result = await ReservationService.create_reservation(data)
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.reserva_esporadica import ReservaEsporadicaRepository
            from src.schemas.reserva import ReservaEsporadicaSchema

            def _create():
                """Synchronous creation."""
                with get_db_session() as session:
                    # Validate required fields
                    required_fields = [
                        "titulo_evento",
                        "sala_id",
                        "data_reserva",
                        "horario_inicio",
                        "horario_fim",
                        "nome_solicitante",
                        "email_solicitante",
                    ]

                    for field in required_fields:
                        if field not in reservation_data or not reservation_data[field]:
                            raise ValueError(f"Missing required field: {field}")

                    # Check conflicts
                    repo = ReservaEsporadicaRepository(session)
                    conflicts = repo.find_conflicts(
                        sala_id=reservation_data["sala_id"],
                        data=reservation_data["data_reserva"],
                        horario_inicio=reservation_data["horario_inicio"],
                        horario_fim=reservation_data["horario_fim"],
                    )

                    if conflicts:
                        return {
                            "success": False,
                            "conflicts": [
                                {
                                    "id": c.id,
                                    "titulo": c.titulo_evento,
                                    "horario_inicio": str(c.horario_inicio),
                                    "horario_fim": str(c.horario_fim),
                                }
                                for c in conflicts
                            ],
                            "message": f"Found {len(conflicts)} conflicting reservations",
                        }

                    # Create reservation
                    schema = ReservaEsporadicaSchema(**reservation_data)
                    created = repo.create(schema)

                    return {
                        "success": True,
                        "reservation_id": created.id,
                        "message": "Reservation created successfully (pending approval)",
                    }

            result = await BaseService.execute_async(_create)

            if result.get("success"):
                logger.info(f"Created reservation: {result['reservation_id']}")
            else:
                logger.warning(f"Reservation creation failed: {result.get('message')}")

            return result

        except Exception as e:
            logger.error(f"Reservation creation failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create reservation",
            }

    @staticmethod
    async def check_conflicts(
        sala_id: int,
        data_reserva: str,
        horario_inicio: str,
        horario_fim: str,
        exclude_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Check for conflicts without creating a reservation.

        Useful for preview checking when filling out the form.

        Args:
            sala_id: Room ID to check
            data_reserva: Date (ISO format)
            horario_inicio: Start time (HH:MM)
            horario_fim: End time (HH:MM)
            exclude_id: Optional reservation ID to exclude (for updates)

        Returns:
            dict with keys:
            - has_conflicts (bool): Whether conflicts exist
            - conflicts (list): List of conflicting reservations

        Example:
            >>> conflicts = await ReservationService.check_conflicts(
            ...     sala_id=1,
            ...     data_reserva="2025-11-20",
            ...     horario_inicio="14:00",
            ...     horario_fim="15:30"
            ... )
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.reserva_esporadica import ReservaEsporadicaRepository

            def _check():
                """Synchronous conflict check."""
                with get_db_session() as session:
                    repo = ReservaEsporadicaRepository(session)

                    conflicts = repo.find_conflicts(
                        sala_id=sala_id,
                        data=data_reserva,
                        horario_inicio=horario_inicio,
                        horario_fim=horario_fim,
                    )

                    # Filter out excluded reservation
                    if exclude_id:
                        conflicts = [c for c in conflicts if c.id != exclude_id]

                    return {
                        "has_conflicts": len(conflicts) > 0,
                        "conflicts": [
                            {
                                "id": c.id,
                                "titulo": c.titulo_evento,
                                "horario_inicio": str(c.horario_inicio),
                                "horario_fim": str(c.horario_fim),
                                "solicitante": c.nome_solicitante,
                            }
                            for c in conflicts
                        ],
                    }

            return await BaseService.execute_async(_check)

        except Exception as e:
            logger.error(f"Conflict check failed: {e}")
            return {
                "has_conflicts": True,
                "error": str(e),
            }

    @staticmethod
    async def update_reservation(
        reservation_id: int,
        update_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a reservation.

        Updates an existing reservation (if not already approved).

        Args:
            reservation_id: ID of reservation to update
            update_data: Fields to update (see create_reservation for field names)

        Returns:
            dict with keys:
            - success (bool): Whether update succeeded
            - message (str): Status or error message
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.reserva_esporadica import ReservaEsporadicaRepository

            def _update():
                """Synchronous update."""
                with get_db_session() as session:
                    repo = ReservaEsporadicaRepository(session)
                    reservation = repo.get_by_id(reservation_id)

                    if not reservation:
                        return {
                            "success": False,
                            "message": f"Reservation {reservation_id} not found",
                        }

                    # Only allow updating if not approved
                    if reservation.status == "Aprovada":
                        return {
                            "success": False,
                            "message": "Cannot update approved reservations",
                        }

                    # Check conflicts for changed date/time/room
                    if any(
                        k in update_data
                        for k in [
                            "sala_id",
                            "data_reserva",
                            "horario_inicio",
                            "horario_fim",
                        ]
                    ):
                        conflicts = repo.find_conflicts(
                            sala_id=update_data.get("sala_id", reservation.sala_id),
                            data=update_data.get(
                                "data_reserva", str(reservation.data_reserva)
                            ),
                            horario_inicio=update_data.get(
                                "horario_inicio", str(reservation.horario_inicio)
                            ),
                            horario_fim=update_data.get(
                                "horario_fim", str(reservation.horario_fim)
                            ),
                        )
                        conflicts = [c for c in conflicts if c.id != reservation_id]

                        if conflicts:
                            return {
                                "success": False,
                                "message": "Time conflict with existing reservations",
                            }

                    repo.update(reservation_id, update_data)

                    return {
                        "success": True,
                        "message": "Reservation updated successfully",
                    }

            result = await BaseService.execute_async(_update)

            if result.get("success"):
                logger.info(f"Updated reservation {reservation_id}")

            return result

        except Exception as e:
            logger.error(f"Update failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    async def delete_reservation(reservation_id: int) -> Dict[str, Any]:
        """Delete a reservation.

        Only allows deletion of pending reservations (not approved).

        Args:
            reservation_id: ID of reservation to delete

        Returns:
            dict with keys:
            - success (bool): Whether deletion succeeded
            - message (str): Status message
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.reserva_esporadica import ReservaEsporadicaRepository

            def _delete():
                """Synchronous deletion."""
                with get_db_session() as session:
                    repo = ReservaEsporadicaRepository(session)
                    reservation = repo.get_by_id(reservation_id)

                    if not reservation:
                        return {
                            "success": False,
                            "message": f"Reservation {reservation_id} not found",
                        }

                    if reservation.status == "Aprovada":
                        return {
                            "success": False,
                            "message": "Cannot delete approved reservations",
                        }

                    repo.delete(reservation_id)

                    return {
                        "success": True,
                        "message": "Reservation deleted successfully",
                    }

            result = await BaseService.execute_async(_delete)

            if result.get("success"):
                logger.info(f"Deleted reservation {reservation_id}")

            return result

        except Exception as e:
            logger.error(f"Deletion failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    async def approve_reservation(
        reservation_id: int,
        admin_comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Approve a pending reservation (admin only).

        Args:
            reservation_id: ID of reservation to approve
            admin_comment: Optional approval comment

        Returns:
            dict with keys:
            - success (bool): Whether approval succeeded
            - message (str): Status message
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.reserva_esporadica import ReservaEsporadicaRepository

            def _approve():
                """Synchronous approval."""
                with get_db_session() as session:
                    repo = ReservaEsporadicaRepository(session)

                    repo.update(
                        reservation_id,
                        {
                            "status": "Aprovada",
                            "observacoes_admin": admin_comment,
                        },
                    )

                    return {
                        "success": True,
                        "message": "Reservation approved",
                    }

            result = await BaseService.execute_async(_approve)

            if result.get("success"):
                logger.info(f"Approved reservation {reservation_id}")

            return result

        except Exception as e:
            logger.error(f"Approval failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    async def reject_reservation(
        reservation_id: int,
        reason: str,
    ) -> Dict[str, Any]:
        """Reject a pending reservation (admin only).

        Args:
            reservation_id: ID of reservation to reject
            reason: Reason for rejection

        Returns:
            dict with keys:
            - success (bool): Whether rejection succeeded
            - message (str): Status message
        """
        try:
            from src.config.database import get_db_session
            from src.repositories.reserva_esporadica import ReservaEsporadicaRepository

            def _reject():
                """Synchronous rejection."""
                with get_db_session() as session:
                    repo = ReservaEsporadicaRepository(session)

                    repo.update(
                        reservation_id,
                        {
                            "status": "Rejeitada",
                            "motivo_rejeicao": reason,
                        },
                    )

                    return {
                        "success": True,
                        "message": "Reservation rejected",
                    }

            result = await BaseService.execute_async(_reject)

            if result.get("success"):
                logger.info(f"Rejected reservation {reservation_id}")

            return result

        except Exception as e:
            logger.error(f"Rejection failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }
