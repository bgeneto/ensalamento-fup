"""
Ensalamento Reflex - Room Allocation Management System
Main Reflex application entry point

Following the architecture documented in docs/Reflex_Architecture_Document.md
"""

# Import our application components and states
import reflex as rx
from ensalamento_reflex.core.components.layout.main_layout import main_layout
from ensalamento_reflex.core.states.auth_state import AuthState
from ensalamento_reflex.core.states.navigation_state import NavigationState


def app_content() -> rx.Component:
    """
    Main application content with authentication routing

    Follows the authentication pattern from our documentation:
    - Authenticated users see the full app
    - Unauthenticated users see the login page
    """
    return rx.cond(
        AuthState.is_logged_in,
        # Authenticated content
        main_layout(page_router()),
        # Login page for unauthenticated users
        login_page(),
    )


def login_page() -> rx.Component:
    """
    Login page component following reactive form patterns

    Implements client-side validation and async login
    """
    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading("🎓 Ensalamento FUP", size="xl"),
                rx.text("Entre com suas credenciais", margin_bottom="4"),
                # Login form following validation patterns
                rx.vstack(
                    rx.input(
                        placeholder="Username",
                        value=AuthState.login_username,
                        on_change=AuthState.set_login_username,
                        width="100%",
                    ),
                    rx.input(
                        type="password",
                        placeholder="Password",
                        value=AuthState.login_password,
                        on_change=AuthState.set_login_password,
                        width="100%",
                    ),
                    rx.button(
                        "Login",
                        on_click=AuthState.login,
                        loading=AuthState.login_loading,
                        width="100%",
                        disabled=AuthState.login_loading,
                    ),
                    # Error display following toast pattern
                    rx.cond(
                        AuthState.login_error != "",
                        rx.callout(
                            AuthState.login_error,
                            icon="alert_triangle",
                            color_scheme="red",
                        ),
                    ),
                    spacing="3",
                    width="300px",
                ),
                spacing="6",
                align="center",
            ),
            width="400px",
            padding="6",
        ),
        height="100vh",
    )


def page_router() -> rx.Component:
    """
    Route to appropriate page based on navigation state

    Implements SPA routing without page reloads
    """
    # Import page components (will be created in Phases 3-4)
    try:
        from ensalamento_reflex.core.components.pages.alloc_page import allocation_page
        from ensalamento_reflex.core.components.pages.dashboard import dashboard_page
        from ensalamento_reflex.core.components.pages.inventory import inventory_page
        from ensalamento_reflex.core.components.pages.professors import professors_page
        from ensalamento_reflex.core.components.pages.reservations import (
            reservations_page,
        )
    except ImportError:
        # Fallback for early development
        def placeholder_page(page_name: str) -> rx.Component:
            return rx.center(
                rx.vstack(
                    rx.heading(f"🚧 {page_name} Page", size="xl"),
                    rx.text("Under development - coming in Phase 3", color="gray"),
                    rx.button(
                        "← Back to Dashboard",
                        on_click=lambda: NavigationState.navigate_to("dashboard"),
                    ),
                    spacing="4",
                    align="center",
                ),
                height="60vh",
            )

    # Route based on navigation state
    return rx.match(
        NavigationState.current_page,
        (
            "dashboard",
            (
                dashboard_page()
                if "dashboard_page" in locals()
                else placeholder_page("Dashboard")
            ),
        ),
        (
            "allocation",
            (
                allocation_page()
                if "allocation_page" in locals()
                else placeholder_page("Allocation")
            ),
        ),
        (
            "inventory",
            (
                inventory_page()
                if "inventory_page" in locals()
                else placeholder_page("Inventory")
            ),
        ),
        (
            "professors",
            (
                professors_page()
                if "professors_page" in locals()
                else placeholder_page("Professors")
            ),
        ),
        (
            "reservations",
            (
                reservations_page()
                if "reservations_page" in locals()
                else placeholder_page("Reservations")
            ),
        ),
        # Default fallback
        placeholder_page("Dashboard"),
    )


# Application configuration following production patterns
def create_app() -> rx.App:
    """Create and configure the Reflex application"""
    app = rx.App(
        theme=rx.theme(accent_color="blue", gray_color="slate", radius="large"),
        # Global styles if needed
        style={
            "font_family": "Inter, sans-serif",
        },
    )

    # Add main page
    app.add_page(app_content, title="Ensalamento FUP")

    return app


# Create the application instance
app = create_app()

if __name__ == "__main__":
    # Development mode - direct execution
    app.run(host="0.0.0.0", port=8000, reload=True)  # Auto-reload on changes
