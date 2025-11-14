"""
Main Layout Component - Reflex Implementation
Provides the overall application layout with navigation and content areas
"""

import reflex as rx

from ...states.auth_state import AuthState
from ...states.navigation_state import NavigationState


def main_layout(content: rx.Component) -> rx.Component:
    """
    Main application layout with sidebar navigation and content area

    Args:
        content: The main page content component

    Returns:
        Fully laid out application component
    """
    return rx.hstack(
        # Sidebar navigation
        sidebar_navigation(),
        # Main content area
        rx.box(
            rx.vstack(
                # Header
                app_header(),
                # Page content
                rx.box(content, flex="1", padding="6", min_height="80vh"),
                # Footer
                app_footer(),
                spacing="0",
                width="100%",
            ),
            flex="1",
            height="100vh",
            width="100%",
        ),
        width="100vw",
        height="100vh",
        spacing="0",
    )


def sidebar_navigation() -> rx.Component:
    """Sidebar with navigation menu"""
    return rx.box(
        rx.vstack(
            # Logo/title
            rx.heading("🎓 Ensalamento", size="md", padding="4"),
            # Navigation items
            navigation_item("Dashboard", "dashboard", "home"),
            navigation_item("Rooms", "inventory", "building"),
            navigation_item("Allocation", "allocation", "check_circle"),
            navigation_item("Professors", "professors", "person"),
            navigation_item("Reservations", "reservations", "calendar"),
            navigation_item("Settings", "settings", "settings"),
            # Spacer
            rx.spacer(),
            # User section
            rx.divider(),
            rx.vstack(
                rx.text(AuthState.display_name, font_weight="bold"),
                rx.cond(
                    AuthState.is_logged_in,
                    rx.button(
                        "Logout",
                        on_click=AuthState.logout,
                        size="sm",
                        color_scheme="red",
                        width="100%",
                    ),
                    rx.text("Not logged in", size="sm", color="gray"),
                ),
                padding="4",
                spacing="2",
                align="start",
                width="100%",
            ),
            width="250px",
            padding="4",
            spacing="2",
            align="start",
        ),
        # Styling
        height="100%",
        bg="gray.50",
        border_right="1px solid var(--gray-6)",
    )


def navigation_item(label: str, page_key: str, icon: str) -> rx.Component:
    """Individual navigation item component"""
    return rx.button(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(label),
            align="center",
            width="100%",
            justify="start",
        ),
        on_click=lambda: NavigationState.navigate_to(page_key),
        variant="ghost",
        width="100%",
        justify="start",
        # Highlight current page
        bg=rx.cond(NavigationState.current_page == page_key, "blue.100", "transparent"),
        color=rx.cond(NavigationState.current_page == page_key, "blue.700", "gray.700"),
    )


def app_header() -> rx.Component:
    """Application header with title and breadcrumbs"""
    return rx.hstack(
        # Logo/title
        rx.heading("🎓 Sistema de Ensalamento FUP", size="lg"),
        # Spacer
        rx.spacer(),
        # Breadcrumbs
        breadcrumbs_display(),
        width="100%",
        padding="4",
        bg="white",
        border_bottom="1px solid var(--gray-6)",
        align="center",
    )


def breadcrumbs_display() -> rx.Component:
    """Display breadcrumbs navigation"""
    return rx.cond(
        NavigationState.breadcrumbs.length() > 0,
        rx.hstack(
            # Breadcrumb items
            rx.foreach(
                NavigationState.breadcrumbs,
                lambda crumb: rx.hstack(
                    rx.button(
                        crumb["label"],
                        on_click=lambda: NavigationState.navigate_to(crumb["page"]),
                        variant="ghost",
                        size="sm",
                    ),
                    rx.text("/", color="gray.500", margin="0 1"),
                ),
            ),
            # Back button if applicable
            rx.cond(
                NavigationState.can_go_back,
                rx.button(
                    "← Back",
                    on_click=NavigationState.go_back,
                    size="sm",
                    variant="outline",
                ),
                rx.box(),  # Empty space
            ),
            spacing="1",
            align="center",
        ),
        rx.box(),  # No breadcrumbs to show
    )


def app_footer() -> rx.Component:
    """Application footer"""
    return rx.box(
        rx.center(
            rx.text(
                "© 2025 Sistema de Ensalamento FUP/UnB - Developed with Reflex",
                size="sm",
                color="gray.500",
            )
        ),
        padding="2",
        bg="gray.50",
        border_top="1px solid var(--gray-6)",
        width="100%",
    )
