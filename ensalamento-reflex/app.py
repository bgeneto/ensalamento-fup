"""Main Ensalamento Reflex application."""

import reflex as rx
from ensalamento_reflex.core.states.auth_state import AuthState
from ensalamento_reflex.core.states.navigation_state import NavigationState


def login_page() -> rx.Component:
    """Login page component."""
    return rx.center(
        rx.card(
            rx.vstack(
                # Header
                rx.heading("🎓 Sistema de Ensalamento FUP", size="6"),
                rx.text("Entre com suas credenciais", margin_bottom="6"),
                # Login form
                rx.vstack(
                    rx.input(
                        placeholder="Nome de usuário",
                        value=AuthState.login_username,
                        on_change=AuthState.set_login_username,
                        width="100%",
                    ),
                    rx.input(
                        type="password",
                        placeholder="Senha",
                        value=AuthState.login_password,
                        on_change=AuthState.set_login_password,
                        width="100%",
                    ),
                    rx.button(
                        "Entrar",
                        on_click=AuthState.login,
                        loading=AuthState.loading,
                        width="100%",
                    ),
                    # Error display
                    rx.cond(
                        AuthState.login_error != "",
                        rx.callout(
                            AuthState.login_error,
                            icon="alert_triangle",
                            color_scheme="red",
                            width="100%",
                        ),
                    ),
                    spacing="3",
                    width="300px",
                ),
                # Development note
                rx.text(
                    "Para desenvolvimento: admin/admin ou coord/coord",
                    font_size="xs",
                    color="gray.500",
                    text_align="center",
                    margin_top="4",
                ),
                spacing="6",
                align="center",
            ),
            width="400px",
            padding="8",
        ),
        height="100vh",
    )


def dashboard_page() -> rx.Component:
    """Dashboard page component."""
    return rx.container(
        rx.vstack(
            # Header
            rx.heading("Dashboard", size="7"),
            rx.text("Bem-vindo ao Sistema de Ensalamento FUP", color="gray.600"),
            # Navigation test
            rx.vstack(
                rx.heading("Navegação", size="5"),
                rx.hstack(
                    rx.button("Ensalamento", on_click=NavigationState.go_to_allocation),
                    rx.button("Inventário", on_click=NavigationState.go_to_inventory),
                    rx.button("Professores", on_click=NavigationState.go_to_professors),
                    rx.button("Reservas", on_click=NavigationState.go_to_reservations),
                    spacing="3",
                ),
                rx.divider(),
                # Current page info
                rx.hstack(
                    rx.text(f"Página atual: {NavigationState.current_page_title}"),
                    rx.button(
                        "Voltar",
                        on_click=NavigationState.go_back,
                        disabled=~NavigationState.can_go_back,
                    ),
                    rx.button("Sair", on_click=AuthState.logout, color_scheme="red"),
                    spacing="3",
                ),
                width="100%",
                spacing="4",
            ),
            spacing="6",
            align="start",
            width="100%",
        ),
        padding="6",
        max_width="1200px",
    )


def allocation_page() -> rx.Component:
    """Allocation page placeholder."""
    return rx.container(
        rx.vstack(
            rx.heading("Ensalamento", size="7"),
            rx.text("Página de alocação - será implementado na Phase 2"),
            rx.button("Voltar ao Dashboard", on_click=NavigationState.go_to_dashboard),
            spacing="4",
            align="start",
        ),
        padding="6",
    )


def inventory_page() -> rx.Component:
    """Inventory page placeholder."""
    return rx.container(
        rx.vstack(
            rx.heading("Inventário", size="7"),
            rx.text("Página de inventário - será implementado na Phase 2"),
            rx.button("Voltar ao Dashboard", on_click=NavigationState.go_to_dashboard),
            spacing="4",
            align="start",
        ),
        padding="6",
    )


def professors_page() -> rx.Component:
    """Professors page placeholder."""
    return rx.container(
        rx.vstack(
            rx.heading("Professores", size="7"),
            rx.text("Página de professores - será implementado na Phase 2"),
            rx.button("Voltar ao Dashboard", on_click=NavigationState.go_to_dashboard),
            spacing="4",
            align="start",
        ),
        padding="6",
    )


def reservations_page() -> rx.Component:
    """Reservations page placeholder."""
    return rx.container(
        rx.vstack(
            rx.heading("Reservas", size="7"),
            rx.text("Página de reservas - será implementado na Phase 2"),
            rx.button("Voltar ao Dashboard", on_click=NavigationState.go_to_dashboard),
            spacing="4",
            align="start",
        ),
        padding="6",
    )


def page_router() -> rx.Component:
    """Route to appropriate page based on navigation state."""
    return rx.match(
        NavigationState.current_page,
        ("dashboard", dashboard_page()),
        ("allocation", allocation_page()),
        ("inventory", inventory_page()),
        ("professors", professors_page()),
        ("reservations", reservations_page()),
        # Default fallback
        dashboard_page(),
    )


def app_content() -> rx.Component:
    """Main application content with authentication guard."""
    return rx.cond(
        AuthState.is_logged_in,
        # Authenticated content
        page_router(),
        # Login page
        login_page(),
    )


# Create the application
app = rx.App(theme=rx.theme(accent_color="blue", gray_color="slate", radius="large"))

# Add main page
app.add_page(app_content, title="Sistema de Ensalamento FUP")
