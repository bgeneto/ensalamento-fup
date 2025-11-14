"""
Allocation Page - Reactive Allocation Management UI
Complete working allocation interface using allocation_state.py

Following UI patterns from docs/Reflex_Architecture_Document.md
"""

import reflex as rx

from ...states.allocation_state import AllocationState


def allocation_page() -> rx.Component:
    """
    Main allocation dashboard page with reactive components

    Features:
    - Real-time allocation progress
    - Configuration settings
    - Results display with conflict analysis
    - Import demand data functionality
    """
    return rx.vstack(
        # Page header with controls
        _allocation_header(),
        # Statistics row
        _allocation_stats_row(),
        # Main content area
        rx.hstack(
            # Left side - Configuration and controls
            rx.vstack(
                _allocation_config_card(),
                _demand_import_card(),
                spacing="4",
                flex="0 0 400px",
            ),
            # Right side - Results and progress
            rx.vstack(
                _allocation_progress_card(),
                _allocation_results_card(),
                spacing="4",
                flex="1",
            ),
            spacing="6",
            width="100%",
            height="70vh",
            align="start",
        ),
        spacing="6",
        padding="6",
        height="100vh",
    )


def _allocation_header() -> rx.Component:
    """Page header with title and main allocation button"""
    return rx.hstack(
        rx.vstack(
            rx.heading("🏢 Room Allocation Engine", size="xl"),
            rx.text("Reactive allocation with real-time progress", color="gray.600"),
            spacing="1",
            align="start",
        ),
        rx.button(
            "🚀 Run Allocation",
            on_click=lambda: AllocationState.run_autonomous_allocation(
                AllocationState.current_semester_id
            ),
            loading=AllocationState.is_allocating,
            loading_text="Allocating...",
            size="lg",
            color_scheme="blue",
            disabled=AllocationState.is_allocating,
        ),
        justify="between",
        align="center",
        width="100%",
    )


def _allocation_stats_row() -> rx.Component:
    """Statistics row showing key metrics"""
    return rx.grid(
        # Completed allocations
        rx.stat(
            rx.stat_label("Completed Allocations"),
            rx.stat_number(
                f"{AllocationState.recent_allocation_summary['allocations_completed']}"
            ),
            rx.stat_help_text("Last run"),
            rx.stat_arrow(
                (
                    "increase"
                    if AllocationState.recent_allocation_summary["status"] == "Success"
                    else None
                ),
                AllocationState.allocation_completion_percentage,
            ),
        ),
        # Conflicts detected
        rx.stat(
            rx.stat_label("Conflicts Detected"),
            rx.stat_number(f"{AllocationState.conflict_count}"),
            rx.stat_help_text("Scheduling conflicts"),
            rx.stat_arrow(
                "decrease" if AllocationState.conflict_count == 0 else "warning",
                -AllocationState.conflict_count,
            ),
        ),
        # Completion percentage
        rx.meter(
            value=round(AllocationState.allocation_completion_percentage),
            min=0,
            max=100,
            high=90,
            label="Allocation Completion",
        ),
        # Execution time
        rx.stat(
            rx.stat_label("Execution Time"),
            rx.stat_number(".1f"),
            rx.stat_help_text("Last run duration"),
        ),
        columns="2" if rx.use_media_query("(max-width: 768px)") else "4",
        spacing="4",
        width="100%",
    )


def _allocation_config_card() -> rx.Component:
    """Configuration card for allocation settings"""
    return rx.card(
        rx.vstack(
            rx.heading("⚙️ Configuration", size="md"),
            rx.divider(),
            # Hard rules toggle
            rx.hstack(
                rx.checkbox(
                    "Enable Hard Rules",
                    checked=AllocationState.include_hard_rules,
                    on_change=lambda val: AllocationState.set_allocation_config(
                        val,
                        AllocationState.include_soft_preferences,
                        AllocationState.max_iterations,
                    ),
                ),
                rx.tooltip(
                    "Hard rules: Time conflicts, capacity limits",
                    rx.icon("info", size=16, color="gray.500"),
                ),
                justify="between",
                width="100%",
            ),
            # Soft preferences toggle
            rx.hstack(
                rx.checkbox(
                    "Enable Soft Preferences",
                    checked=AllocationState.include_soft_preferences,
                    on_change=lambda val: AllocationState.set_allocation_config(
                        AllocationState.include_hard_rules,
                        val,
                        AllocationState.max_iterations,
                    ),
                ),
                rx.tooltip(
                    "Soft preferences: Room preferences, professor needs",
                    rx.icon("info", size=16, color="gray.500"),
                ),
                justify="between",
                width="100%",
            ),
            # Max iterations slider
            rx.vstack(
                rx.text(
                    f"Max Iterations: {AllocationState.max_iterations}",
                    font_weight="bold",
                ),
                rx.slider(
                    value=AllocationState.max_iterations,
                    min=10,
                    max=500,
                    step=10,
                    on_change=lambda val: AllocationState.set_allocation_config(
                        AllocationState.include_hard_rules,
                        AllocationState.include_soft_preferences,
                        int(val),
                    ),
                    width="100%",
                ),
                rx.text(
                    "Higher values improve results but take longer",
                    size="sm",
                    color="gray.600",
                ),
                spacing="2",
                align="stretch",
            ),
            # Reset button
            rx.button(
                "Reset to Defaults",
                on_click=AllocationState.reset_to_defaults,
                size="sm",
                variant="outline",
                color_scheme="gray",
            ),
            spacing="4",
            align="start",
        ),
        width="100%",
    )


def _demand_import_card() -> rx.Component:
    """Demand import card for data management"""
    return rx.card(
        rx.vstack(
            rx.heading("📥 Import Demand Data", size="md"),
            rx.divider(),
            # Current semester info
            rx.text(
                f"Current Semester: {AllocationState.current_semester_id}",
                font_weight="bold",
            ),
            # Import button
            rx.button(
                "📡 Import from API",
                on_click=lambda: AllocationState.import_demand_data(
                    AllocationState.current_semester_id
                ),
                loading=AllocationState.loading_import,
                loading_text="Importing...",
                width="100%",
                disabled=AllocationState.loading_import,
            ),
            # Import progress bar
            rx.cond(
                AllocationState.loading_import or AllocationState.import_progress > 0,
                rx.meter(
                    value=AllocationState.import_progress,
                    min=0,
                    max=100,
                    label="Import Progress",
                ),
            ),
            spacing="3",
            align="start",
        ),
        width="100%",
    )


def _allocation_progress_card() -> rx.Component:
    """Live allocation progress display"""
    return rx.card(
        rx.vstack(
            rx.heading("⚡ Live Progress", size="md"),
            rx.divider(),
            rx.cond(
                AllocationState.is_allocating,
                # Active progress display
                rx.vstack(
                    rx.meter(
                        value=AllocationState.allocation_progress,
                        min=0,
                        max=100,
                        label="Allocation Progress",
                    ),
                    rx.text(
                        "Running autonomous allocation algorithm...", color="blue.600"
                    ),
                    spacing="2",
                    align="center",
                ),
                # Idle progress display
                rx.vstack(
                    rx.meter(value=0, min=0, max=100, label="Ready"),
                    rx.text("Allocation engine ready", color="gray.600"),
                    spacing="2",
                    align="center",
                ),
            ),
            spacing="3",
            align="start",
        ),
        width="100%",
    )


def _allocation_results_card() -> rx.Component:
    """Allocation results display"""
    return rx.card(
        rx.vstack(
            rx.heading("📊 Allocation Results", size="md"),
            rx.divider(),
            # Results conditional display
            rx.cond(
                AllocationState.allocation_result,
                # Show results
                rx.vstack(
                    rx.hstack(
                        rx.badge(
                            AllocationState.recent_allocation_summary["status"],
                            color_scheme=(
                                "green"
                                if AllocationState.recent_allocation_summary["status"]
                                == "Success"
                                else "red"
                            ),
                        ),
                        rx.spacer(),
                        rx.text(
                            f"ID: {AllocationState.last_allocation_id}",
                            color="gray.600",
                        ),
                        justify="between",
                        width="100%",
                    ),
                    rx.divider(),
                    # Key metrics
                    rx.grid(
                        rx.stat(
                            rx.stat_label("Completions"),
                            rx.stat_number(
                                f"{AllocationState.recent_allocation_summary['allocations_completed']}"
                            ),
                        ),
                        rx.stat(
                            rx.stat_label("Execution Time"),
                            rx.stat_number(".1f"),
                        ),
                        rx.stat(
                            rx.stat_label("Conflicts Found"),
                            rx.stat_number(f"{AllocationState.conflict_count}"),
                            color=rx.cond(
                                AllocationState.conflict_count == 0, "green", "orange"
                            ),
                        ),
                        columns="3",
                        spacing="4",
                    ),
                    # Action buttons
                    rx.hstack(
                        rx.button(
                            "📊 Export Results",
                            on_click=lambda: AllocationState.export_allocation_results(
                                AllocationState.current_semester_id, "pdf"
                            ),
                            size="sm",
                        ),
                        rx.button(
                            "🔄 Refresh Progress",
                            on_click=lambda: AllocationState.refresh_allocation_progress(
                                AllocationState.current_semester_id
                            ),
                            size="sm",
                            variant="outline",
                        ),
                        rx.spacer(),
                        rx.button(
                            "🗑️ Clear Results",
                            on_click=AllocationState.clear_allocation_result,
                            size="sm",
                            color_scheme="red",
                            variant="soft",
                        ),
                        justify="between",
                        width="100%",
                    ),
                    spacing="4",
                    align="start",
                ),
                # No results message
                rx.center(
                    rx.vstack(
                        rx.icon("bar_chart", size=48, color="gray.400"),
                        rx.text("No allocation results", color="gray.600"),
                        rx.text(
                            "Run an allocation to see results here",
                            size="sm",
                            color="gray.500",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    height="200px",
                ),
            ),
            spacing="3",
            align="start",
        ),
        width="100%",
    )
