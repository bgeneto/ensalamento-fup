"""Main Ensalamento Reflex application."""

import reflex as rx
from core.states.auth_state import AuthState
from core.states.navigation_state import NavigationState


def login_page() -> rx.Component:
    """Professional login page component following Reflex auth patterns."""
    return rx.box(
        # Background container
        rx.vstack(
            # Logo and title section
            rx.vstack(
                rx.heading("🎓", font_size="4xl", text_align="center"),
                rx.heading(
                    "Sistema de Ensalamento FUP",
                    size="5",
                    weight="bold",
                    text_align="center",
                ),
                rx.text(
                    "Universidade de Brasília - Faculdade UnB Planaltina",
                    font_size="sm",
                    color="gray.500",
                    text_align="center",
                ),
                spacing="2",
                width="100%",
                margin_bottom="6",
            ),
            
            # Login form card
            rx.card(
                rx.vstack(
                    # Form title
                    rx.text(
                        "Entrar no Sistema",
                        font_size="lg",
                        weight="semibold",
                        text_align="center",
                    ),
                    rx.divider(),
                    
                    # Username field
                    rx.vstack(
                        rx.text("Nome de Usuário", font_size="sm", weight="medium"),
                        rx.input(
                            placeholder="seu_usuario",
                            value=AuthState.login_username,
                            on_change=AuthState.set_login_username,
                            width="100%",
                            size="2",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    
                    # Password field
                    rx.vstack(
                        rx.text("Senha", font_size="sm", weight="medium"),
                        rx.input(
                            type="password",
                            placeholder="••••••••",
                            value=AuthState.login_password,
                            on_change=AuthState.set_login_password,
                            width="100%",
                            size="2",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    
                    # Error message display
                    rx.cond(
                        AuthState.login_error != "",
                        rx.callout(
                            rx.hstack(
                                rx.icon("alert_circle", size=16),
                                rx.text(AuthState.login_error, font_size="sm"),
                                spacing="2",
                                width="100%",
                            ),
                            color_scheme="red",
                            width="100%",
                            padding="3",
                        ),
                    ),
                    
                    # Login button
                    rx.button(
                        "Entrar",
                        on_click=AuthState.login,
                        loading=AuthState.loading_login,
                        width="100%",
                        size="2",
                    ),
                    
                    # Development credentials hint
                    rx.box(
                        rx.vstack(
                            rx.text(
                                "Credenciais de Desenvolvimento:",
                                font_size="xs",
                                weight="bold",
                                color="blue.600",
                            ),
                            rx.unordered_list(
                                rx.list_item(
                                    rx.code("admin"),
                                    " / ",
                                    rx.code("admin"),
                                    " (Administrador)",
                                    font_size="xs",
                                ),
                                rx.list_item(
                                    rx.code("coord"),
                                    " / ",
                                    rx.code("coord"),
                                    " (Coordenador)",
                                    font_size="xs",
                                ),
                                margin_left="3",
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        background_color="blue.50",
                        padding="3",
                        border_radius="md",
                        border="1px solid",
                        border_color="blue.200",
                    ),
                    
                    spacing="4",
                    width="100%",
                ),
                width="360px",
                padding="6",
                box_shadow="0 4px 12px rgba(0, 0, 0, 0.1)",
            ),
            
            # Footer
            rx.text(
                "© 2025 Universidade de Brasília - Todos os direitos reservados",
                font_size="xs",
                color="gray.500",
                text_align="center",
                margin_top="6",
            ),
            
            # Layout properties
            spacing="4",
            align="center",
            justify="center",
            min_height="100vh",
            width="100%",
            padding="4",
            background="linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(6, 182, 212, 0.05) 100%)",
        ),
        width="100%",
        height="100vh",
        overflow="auto",
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
