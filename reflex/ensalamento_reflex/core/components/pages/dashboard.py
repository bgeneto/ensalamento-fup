"""
Dashboard Page - Main application overview

Simple dashboard to demonstrate functionality and navigation
"""

import reflex as rx

from ...states.allocation_state import AllocationState
from ...states.navigation_state import NavigationState


def dashboard_page() -> rx.Component:
    """Main dashboard showing application overview and quick actions"""
    return rx.vstack(
        # Welcome header
        rx.hstack(
            rx.vstack(
                rx.heading("🏠 Dashboard", size="xl"),
                rx.text(
                    "Welcome to Ensalamento FUP Management System", color="gray.600"
                ),
                spacing="1",
                align="start",
            ),
            rx.spacer(),
            rx.vstack(
                rx.text(
                    f"Semester: {AllocationState.current_semester_id}",
                    font_weight="bold",
                ),
                rx.text("Status: Online", color="green.600"),
                spacing="1",
                align="end",
            ),
            justify="between",
            align="center",
            width="100%",
        ),
        rx.divider(),
        # Quick stats
        _quick_stats_section(),
        # Quick actions grid
        _quick_actions_section(),
        # System status
        _system_status_section(),
        spacing="6",
        padding="6",
        height="100vh",
    )


def _quick_stats_section() -> rx.Component:
    """Display key system statistics"""
    return rx.vstack(
        rx.heading("📊 System Overview", size="lg"),
        rx.grid(
            rx.stat(
                rx.stat_label("Rooms Available"),
                rx.stat_number("125"),
                rx.stat_help_text("Total capacity"),
            ),
            rx.stat(
                rx.stat_label("Allocations This Semester"),
                rx.stat_number(
                    f"{AllocationState.recent_allocation_summary['allocations_completed']}"
                    if AllocationState.recent_allocation_summary["status"]
                    != "No allocation run"
                    else "0"
                ),
                rx.stat_help_text("Completed allocations"),
            ),
            rx.stat(
                rx.stat_label("Pending Demand"),
                rx.stat_number("47"),
                rx.stat_help_text("Unallocated classes"),
            ),
            rx.stat(
                rx.stat_label("Success Rate"),
                rx.stat_number("87.3%"),
                rx.stat_help_text("Average allocation success"),
            ),
            columns="2" if rx.use_media_query("(max-width: 768px)") else "4",
            spacing="4",
            width="100%",
        ),
        spacing="4",
        align="start",
    )


def _quick_actions_section() -> rx.Component:
    """Quick action buttons for common tasks"""
    return rx.vstack(
        rx.heading("⚡ Quick Actions", size="lg"),
        rx.grid(
            # Allocation button
            rx.card(
                rx.vstack(
                    rx.heading("🏢 Room Allocation", size="md", color="blue.600"),
                    rx.text(
                        "Run automated room allocation", size="sm", color="gray.600"
                    ),
                    rx.button(
                        "🚀 Start Allocation",
                        on_click=lambda: NavigationState.navigate_to("allocation"),
                        color_scheme="blue",
                        size="sm",
                    ),
                    spacing="3",
                    align="center",
                ),
                width="100%",
                cursor="pointer",
                on_click=lambda: NavigationState.navigate_to("allocation"),
            ),
            # Inventory management
            rx.card(
                rx.vstack(
                    rx.heading("🏢 Room Inventory", size="md", color="green.600"),
                    rx.text("Manage rooms and facilities", size="sm", color="gray.600"),
                    rx.button(
                        "📋 View Rooms",
                        on_click=lambda: NavigationState.navigate_to("inventory"),
                        color_scheme="green",
                        size="sm",
                        variant="outline",
                    ),
                    spacing="3",
                    align="center",
                ),
                width="100%",
            ),
            # Professor management
            rx.card(
                rx.vstack(
                    rx.heading("👨‍🏫 Professors", size="md", color="purple.600"),
                    rx.text(
                        "Manage professor preferences", size="sm", color="gray.600"
                    ),
                    rx.button(
                        "👥 View Professors",
                        on_click=lambda: NavigationState.navigate_to("professors"),
                        color_scheme="purple",
                        size="sm",
                        variant="outline",
                    ),
                    spacing="3",
                    align="center",
                ),
                width="100%",
            ),
            # Reservations
            rx.card(
                rx.vstack(
                    rx.heading("📅 Reservations", size="md", color="orange.600"),
                    rx.text("Manage room reservations", size="sm", color="gray.600"),
                    rx.button(
                        "📆 View Reservations",
                        on_click=lambda: NavigationState.navigate_to("reservations"),
                        color_scheme="orange",
                        size="sm",
                        variant="outline",
                    ),
                    spacing="3",
                    align="center",
                ),
                width="100%",
            ),
            columns="1" if rx.use_media_query("(max-width: 768px)") else "2",
            spacing="4",
            width="100%",
        ),
        spacing="4",
        align="start",
    )


def _system_status_section() -> rx.Component:
    """System status and recent activity"""
    return rx.vstack(
        rx.heading("🔍 System Status", size="lg"),
        rx.hstack(
            # Database status
            rx.vstack(
                rx.hstack(
                    rx.icon("database", color="green.500", size=16),
                    rx.text("Database: Connected", font_weight="bold"),
                    spacing="2",
                    align="center",
                ),
                rx.text("Last sync: 2 minutes ago", size="sm", color="gray.600"),
                spacing="1",
                align="start",
            ),
            # API status
            rx.vstack(
                rx.hstack(
                    rx.icon("globe", color="green.500", size=16),
                    rx.text("SISTEMA DE OFERTA API: Online", font_weight="bold"),
                    spacing="2",
                    align="center",
                ),
                rx.text("Last import: 1 hour ago", size="sm", color="gray.600"),
                spacing="1",
                align="start",
            ),
            # Allocation engine status
            rx.vstack(
                rx.hstack(
                    rx.icon("cpu", color="green.500", size=16),
                    rx.text("Allocation Engine: Ready", font_weight="bold"),
                    spacing="2",
                    align="center",
                ),
                rx.text(
                    f"Algorithm: {AllocationState.recent_allocation_summary['status']}",
                    size="sm",
                    color="gray.600",
                ),
                spacing="1",
                align="start",
            ),
            spacing="6",
            width="100%",
            justify="start",
        ),
        spacing="4",
        align="start",
    )
