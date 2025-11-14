"""
Reservation State - Reflex Implementation
Manages room reservations and scheduling conflicts

Following patterns from docs/Technical_Constraints_Patterns.md:
- ✅ Defensive mutation patterns
- ✅ Computed properties with @rx.var
- ✅ Loading states for async operations
- ✅ Toast notifications for user feedback
"""

from datetime import date

import reflex as rx

from ...services.reservation_service import ReservationService


class ReservationState(rx.State):
    """Reservation management state with comprehensive scheduling operations"""

    # Data
    reservations: list[dict] = []

    # Loading states (following loading pattern)
    loading_reservations: bool = False
    loading_create: bool = False
    loading_update: bool = False
    loading_delete: bool = False
    loading_conflicts: bool = False

    # Filters and pagination
    page: int = 1
    page_size: int = 15

    search_query: str = ""
    status_filter: str = "all"
    requester_filter: str = ""
    date_filter_start: str = ""
    date_filter_end: str = ""
    building_filter: str = "all"

    # Form data for reservation creation/updates
    form_title: str = ""
    form_description: str = ""
    form_date: str = ""
    form_time_block: str = ""
    form_duration: int = 1  # in hours
    form_attendees: int = 1
    form_room_id: int | None = None
    form_requester_name: str = ""
    form_requester_email: str = ""
    form_purpose: str = ""

    # Form validation errors
    form_title_error: str = ""
    form_date_error: str = ""
    form_time_block_error: str = ""
    form_room_error: str = ""

    # UI state
    show_create_form: bool = False
    editing_reservation: dict | None = None
    selected_reservation: dict | None = None

    # Conflict checking
    conflicts_checked: bool = False
    conflicts_found: list[dict] = []

    @rx.var
    def total_reservations(self) -> int:
        """Computed total reservation count"""
        return len(self.reservations)

    @rx.var
    def filtered_reservations(self) -> list[dict]:
        """Computed filtered reservations based on current filters"""
        filtered = self.reservations

        # Search filter
        if self.search_query.strip():
            query = self.search_query.strip().lower()
            filtered = [
                res
                for res in filtered
                if query in res.get("titulo_evento", "").lower()
                or query in res.get("nome_solicitante", "").lower()
                or query in res.get("sala_nome", "").lower()
            ]

        # Status filter
        if self.status_filter != "all":
            filtered = [
                res
                for res in filtered
                if res.get("status", "Aprovada") == self.status_filter
            ]

        # Requester filter
        if self.requester_filter.strip():
            requester = self.requester_filter.strip().lower()
            filtered = [
                res
                for res in filtered
                if requester in res.get("nome_solicitante", "").lower()
            ]

        # Date range filters
        if self.date_filter_start:
            filtered = [
                res
                for res in filtered
                if res.get("data_reserva", "").replace("-", "")
                >= self.date_filter_start.replace("-", "")
            ]
        if self.date_filter_end:
            filtered = [
                res
                for res in filtered
                if res.get("data_reserva", "").replace("-", "")
                <= self.date_filter_end.replace("-", "")
            ]

        # Building filter using room info
        if self.building_filter != "all":
            filtered = [
                res
                for res in filtered
                if res.get("sala_predio") == self.building_filter
            ]

        return filtered

    @rx.var
    def displayed_reservations(self) -> list[dict]:
        """Computed reservations displayed for current page"""
        filtered = self.filtered_reservations
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        return filtered[start:end]

    @rx.var
    def total_pages(self) -> int:
        """Computed total pages for pagination"""
        total_filtered = len(self.filtered_reservations)
        if total_filtered == 0:
            return 1
        return (total_filtered + self.page_size - 1) // self.page_size

    @rx.var
    def upcoming_reservations(self) -> list[dict]:
        """Computed upcoming reservations (next 7 days)"""
        today = date.today().isoformat()
        reservations_in_range = [
            res for res in self.reservations if res.get("data_reserva", "") >= today
        ]
        return sorted(
            reservations_in_range,
            key=lambda x: x.get("data_reserva", ""),
            reverse=False,
        )

    @rx.var
    def todays_reservations(self) -> list[dict]:
        """Computed today's reservations"""
        today = date.today().isoformat()
        return [
            res for res in self.reservations if res.get("data_reserva", "") == today
        ]

    @rx.var
    def reservations_by_room(self) -> dict[str, list[dict]]:
        """Computed reservations grouped by room"""
        grouped = {}
        for res in self.reservations:
            room_name = res.get("sala_nome", "Unknown")
            if room_name not in grouped:
                grouped[room_name] = []
            grouped[room_name].append(res)
        return grouped

    @rx.var
    def conflict_summary(self) -> dict[str, int]:
        """Computed conflict statistics"""
        approved = sum(1 for r in self.reservations if r.get("status") == "Aprovada")
        pending = sum(1 for r in self.reservations if r.get("status") == "Pendente")
        cancelled = sum(1 for r in self.reservations if r.get("status") == "Cancelada")

        return {"approved": approved, "pending": pending, "cancelled": cancelled}

    @rx.var
    def available_time_blocks(self) -> list[str]:
        """Computed available time blocks for scheduling"""
        blocks = ["M1", "M2", "T1", "T2", "N1", "N2"]  # Matutino, Tarde, Noite
        return blocks

    async def load_reservations(self):
        """
        Load all reservations from database

        Following loading pattern with user feedback
        """
        if self.loading_reservations:
            yield rx.toast.info("Already loading reservations...")
            return

        self.loading_reservations = True
        self.error = ""
        yield

        try:
            # Use async service layer
            reservation_data = await ReservationService.get_all_reservations()

            # Defensive reassignment
            self.reservations = reservation_data
            self.reservations = list(self.reservations)

            # Reset pagination
            self.page = 1

            yield rx.toast.success(
                f"Loaded {len(reservation_data)} reservations successfully"
            )

        except Exception as e:
            self.error = f"Failed to load reservations: {str(e)}"
            yield rx.toast.error(f"Failed to load reservations: {e}")

        finally:
            self.loading_reservations = False

    def set_search_query(self, value: str):
        """Update search query and reset to page 1"""
        self.search_query = value.strip()
        self.page = 1

    def set_status_filter(self, value: str):
        """Update status filter and reset to page 1"""
        self.status_filter = value
        self.page = 1

    def set_requester_filter(self, value: str):
        """Update requester filter and reset to page 1"""
        self.requester_filter = value.strip()
        self.page = 1

    def set_date_filters(self, start_date: str, end_date: str):
        """Update date range filters and reset to page 1"""
        self.date_filter_start = start_date
        self.date_filter_end = end_date
        self.page = 1

    def set_building_filter(self, value: str):
        """Update building filter and reset to page 1"""
        self.building_filter = value
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
        self.status_filter = "all"
        self.requester_filter = ""
        self.date_filter_start = ""
        self.date_filter_end = ""
        self.building_filter = "all"
        self.page = 1
        yield rx.toast.info("Filters reset")

    def show_create_form(self):
        """Show create reservation form"""
        self.show_create_form = True
        self.editing_reservation = None
        self.conflicts_checked = False
        self.conflicts_found = []
        self._clear_form()

    def hide_create_form(self):
        """Hide create reservation form"""
        self.show_create_form = False
        self.editing_reservation = None
        self.conflicts_checked = False
        self.conflicts_found = []
        self._clear_form()

    def start_editing_reservation(self, reservation: dict):
        """Start editing a reservation"""
        self.editing_reservation = reservation
        self.show_create_form = True
        self.conflicts_checked = False
        self.conflicts_found = []

        # Populate form with reservation data
        self.form_title = reservation.get("titulo_evento", "")
        self.form_description = reservation.get("descrição", "")
        self.form_date = reservation.get("data_reserva", "")
        self.form_time_block = reservation.get("bloqueio_horário", "")
        self.form_duration = reservation.get("duração_horas", 1)
        self.form_attendees = reservation.get("número_participantes", 1)
        self.form_room_id = reservation.get("sala_id")
        self.form_requester_name = reservation.get("nome_solicitante", "")
        self.form_requester_email = reservation.get("email_solicitante", "")
        self.form_purpose = reservation.get("finalidade", "")

    async def check_conflicts(self):
        """
        Check for scheduling conflicts for current form data

        Following loading pattern
        """
        if self.loading_conflicts:
            yield rx.toast.info("Already checking conflicts...")
            return

        # Client-side validation first
        if not self.form_date or not self.form_time_block or not self.form_room_id:
            yield rx.toast.error("Please select date, time block, and room first")
            return

        self.loading_conflicts = True
        self.conflicts_checked = False
        yield

        try:
            # Prepare conflict check data
            conflict_data = {
                "data_reserva": self.form_date,
                "bloqueio_horário": self.form_time_block,
                "duração_horas": self.form_duration,
                "sala_id": self.form_room_id,
            }

            # Check for conflicts
            conflicts = await ReservationService.check_conflicts(conflict_data)

            # Defensive reassignment
            self.conflicts_found = conflicts
            self.conflicts_found = list(self.conflicts_found)
            self.conflicts_checked = True

            if conflicts:
                yield rx.toast.warning(f"Found {len(conflicts)} potential conflicts")
            else:
                yield rx.toast.success("No conflicts found - booking available")

        except Exception as e:
            yield rx.toast.error(f"Conflict check failed: {e}")

        finally:
            self.loading_conflicts = False

    async def create_reservation(self):
        """
        Create new reservation with conflict checking

        Following validation and loading patterns
        """
        if self.loading_create:
            yield rx.toast.info("Already creating reservation...")
            return

        # Client-side validation
        if not self._validate_form():
            return

        # Check conflicts if not already checked
        if not self.conflicts_checked:
            yield rx.toast.warning("Please check for conflicts first")
            return

        if self.conflicts_found:
            yield rx.toast.error("Cannot create reservation - conflicts exist")
            return

        self.loading_create = True
        yield

        try:
            # Prepare reservation data
            reservation_data = {
                "titulo_evento": self.form_title,
                "descrição": self.form_description,
                "data_reserva": self.form_date,
                "bloqueio_horário": self.form_time_block,
                "duração_horas": self.form_duration,
                "número_participantes": self.form_attendees,
                "sala_id": self.form_room_id,
                "nome_solicitante": self.form_requester_name,
                "email_solicitante": self.form_requester_email,
                "finalidade": self.form_purpose,
                "status": "Pendente",
            }

            # Create via service
            result = await ReservationService.create_reservation(reservation_data)

            if result and result.get("success"):
                # Add to local state defensively
                new_reservation = result.get("reservation", reservation_data)
                self.reservations.append(new_reservation)
                self.reservations = list(self.reservations)

                # Reset form and UI
                self.hide_create_form()
                yield rx.toast.success(
                    f"Reservation '{new_reservation.get('titulo_evento')}' created successfully"
                )
            else:
                error_msg = (
                    result.get("error", "Failed to create reservation")
                    if result
                    else "Failed to create reservation"
                )
                yield rx.toast.error(error_msg)

        except Exception as e:
            yield rx.toast.error(f"Reservation creation failed: {e}")

        finally:
            self.loading_create = False

    async def update_reservation(self):
        """
        Update existing reservation
        """
        if self.loading_update or not self.editing_reservation:
            return

        if not self._validate_form():
            return

        self.loading_update = True
        yield

        try:
            # Prepare updated data
            reservation_data = {
                "titulo_evento": self.form_title,
                "descrição": self.form_description,
                "data_reserva": self.form_date,
                "bloqueio_horário": self.form_time_block,
                "duração_horas": self.form_duration,
                "número_participantes": self.form_attendees,
                "sala_id": self.form_room_id,
                "nome_solicitante": self.form_requester_name,
                "email_solicitante": self.form_requester_email,
                "finalidade": self.form_purpose,
            }

            # Update via service
            result = await ReservationService.update_reservation(
                self.editing_reservation["id"], reservation_data
            )

            if result and result.get("success"):
                # Update local state
                res_id = self.editing_reservation["id"]
                for i, res in enumerate(self.reservations):
                    if res["id"] == res_id:
                        self.reservations[i] = {**res, **reservation_data}
                        break

                self.reservations = list(self.reservations)
                self.hide_create_form()
                yield rx.toast.success(
                    f"Reservation '{reservation_data['titulo_evento']}' updated successfully"
                )
            else:
                error_msg = (
                    result.get("error", "Failed to update reservation")
                    if result
                    else "Failed to update reservation"
                )
                yield rx.toast.error(error_msg)

        except Exception as e:
            yield rx.toast.error(f"Reservation update failed: {e}")

        finally:
            self.loading_update = False

    async def delete_reservation(self, reservation_id: int):
        """
        Delete reservation
        """
        if self.loading_delete:
            return

        self.loading_delete = True
        yield

        try:
            result = await ReservationService.delete_reservation(reservation_id)

            if result and result.get("success"):
                # Remove from local state defensively
                self.reservations = [
                    r for r in self.reservations if r["id"] != reservation_id
                ]
                self.reservations = list(self.reservations)

                yield rx.toast.success("Reservation deleted successfully")
            else:
                error_msg = (
                    result.get("error", "Failed to delete reservation")
                    if result
                    else "Failed to delete reservation"
                )
                yield rx.toast.error(error_msg)

        except Exception as e:
            yield rx.toast.error(f"Reservation deletion failed: {e}")

        finally:
            self.loading_delete = False

    async def approve_reservation(self, reservation_id: int):
        """
        Approve a pending reservation
        """
        try:
            result = await ReservationService.update_reservation_status(
                reservation_id, "Aprovada"
            )

            if result and result.get("success"):
                # Update local state
                for i, res in enumerate(self.reservations):
                    if res["id"] == reservation_id:
                        self.reservations[i] = {**res, "status": "Aprovada"}
                        break

                self.reservations = list(self.reservations)
                yield rx.toast.success("Reservation approved")
            else:
                yield rx.toast.error("Failed to approve reservation")

        except Exception as e:
            yield rx.toast.error(f"Approval failed: {e}")

    async def cancel_reservation(self, reservation_id: int):
        """
        Cancel a reservation
        """
        try:
            result = await ReservationService.update_reservation_status(
                reservation_id, "Cancelada"
            )

            if result and result.get("success"):
                # Update local state
                for i, res in enumerate(self.reservations):
                    if res["id"] == reservation_id:
                        self.reservations[i] = {**res, "status": "Cancelada"}
                        break

                self.reservations = list(self.reservations)
                yield rx.toast.success("Reservation cancelled")
            else:
                yield rx.toast.error("Failed to cancel reservation")

        except Exception as e:
            yield rx.toast.error(f"Cancellation failed: {e}")

    def _validate_form(self) -> bool:
        """Validate reservation form data"""
        errors = []

        # Title validation
        if not self.form_title.strip():
            errors.append("Event title is required")
        elif len(self.form_title.strip()) < 3:
            errors.append("Event title must be at least 3 characters")

        # Date validation
        if not self.form_date:
            errors.append("Date is required")

        # Time block validation
        if not self.form_time_block:
            errors.append("Time block is required")

        # Room validation
        if not self.form_room_id:
            errors.append("Room selection is required")

        # Update error states
        self.form_title_error = (
            "Event title is required" if not self.form_title.strip() else ""
        )
        self.form_date_error = "Date is required" if not self.form_date else ""
        self.form_time_block_error = (
            "Time block is required" if not self.form_time_block else ""
        )
        self.form_room_error = (
            "Room selection is required" if not self.form_room_id else ""
        )

        if errors:
            yield rx.toast.error(f"Validation failed: {', '.join(errors[:2])}")
            return False

        return True

    def _clear_form(self):
        """Clear all form data and errors"""
        self.form_title = ""
        self.form_description = ""
        self.form_date = ""
        self.form_time_block = ""
        self.form_duration = 1
        self.form_attendees = 1
        self.form_room_id = None
        self.form_requester_name = ""
        self.form_requester_email = ""
        self.form_purpose = ""

        self.form_title_error = ""
        self.form_date_error = ""
        self.form_time_block_error = ""
        self.form_room_error = ""
