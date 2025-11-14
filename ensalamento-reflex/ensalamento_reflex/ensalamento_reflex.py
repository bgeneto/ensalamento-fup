"""Main Ensalamento Reflex application - Sistema de Ensalamento FUP/UnB.

This is the main entry point for the Reflex application that replaces
the Streamlit-based frontend while preserving all existing business logic.
"""

import reflex as rx
from core.states.auth_state import AuthState
from core.states.navigation_state import NavigationState
from core.states.room_state import RoomState
from core.states.reservation_state import ReservationState
from core.states.allocation_state import AllocationState


# ============================================================================
# LAYOUT COMPONENTS
# ============================================================================

def sidebar() -> rx.Component:
    """Application sidebar with navigation."""
    return rx.box(
        rx.vstack(
            # Logo section
            rx.vstack(
                rx.heading("🎓", font_size="2xl"),
                rx.text("Ensalamento FUP", font_size="4", weight="bold"),
                spacing="2",
                padding="2",
                border_bottom="1px solid #e0e0e0",
            ),
            
            # Navigation menu
            rx.vstack(
                rx.button(
                    "🏠 Dashboard",
                    width="100%",
                    on_click=NavigationState.go_to_dashboard,
                    variant="surface",
                ),
                rx.button(
                    "✅ Ensalamento",
                    width="100%",
                    on_click=NavigationState.go_to_allocation,
                    variant="surface",
                ),
                rx.button(
                    "🏢 Inventário",
                    width="100%",
                    on_click=NavigationState.go_to_inventory,
                    variant="surface",
                ),
                rx.button(
                    "📅 Reservas",
                    width="100%",
                    on_click=NavigationState.go_to_reservations,
                    variant="surface",
                ),
                spacing="2",
                padding="2",
            ),
            
            # User section at bottom
            rx.spacer(),
            rx.divider(),
            rx.vstack(
                rx.text(
                    AuthState.display_name,
                    font_size="4",
                    weight="bold",
                ),
                rx.button(
                    "🚪 Sair",
                    width="100%",
                    on_click=AuthState.logout,
                    color_scheme="red",
                    variant="soft",
                ),
                spacing="2",
                padding="2",
            ),
            
            spacing="0",
            height="100vh",
            width="200px",
            background="linear-gradient(180deg, #f9f9f9 0%, #f0f0f0 100%)",
            border_right="1px solid #e0e0e0",
            box_shadow="0 2px 4px rgba(0,0,0,0.1)",
            overflow_y="auto",
        ),
        position="fixed",
        left="0",
        top="0",
        height="100vh",
        width="200px",
        z_index="100",
    )


def header() -> rx.Component:
    """Application header with user info and page title."""
    return rx.box(
        rx.hstack(
            rx.text(
                f"Olá, {AuthState.display_name}!",
                font_size="lg",
                weight="bold",
            ),
            rx.spacer(),
            rx.text(
                NavigationState.current_page_title,
                font_size="5",
                color="gray",
            ),
            width="100%",
            padding="2",
            background="white",
            border_bottom="1px solid #e0e0e0",
        ),
        width="100%",
    )


def main_layout(title: str, content: rx.Component) -> rx.Component:
    """Main application layout with sidebar and content area."""
    return rx.hstack(
        sidebar(),
        rx.vstack(
            header(),
            rx.box(
                content,
                flex="1",
                padding="4",
                overflow_y="auto",
            ),
            width="100%",
            height="100vh",
            spacing="0",
        ),
        width="100vw",
        height="100vh",
        spacing="0",
    )


# ============================================================================
# PAGE: LOGIN
# ============================================================================

def login_page() -> rx.Component:
    """Login page component."""
    return rx.center(
        rx.vstack(
            # Header
            rx.vstack(
                rx.heading("🎓 Ensalamento FUP", size="8"),
                rx.text(
                    "Sistema de Alocação de Salas",
                    color="gray",
                    font_size="5",
                ),
                spacing="2",
                text_align="center",
                margin_bottom="4",
            ),

            # Login card
            rx.card(
                rx.vstack(
                    rx.text("Faça login para continuar", weight="bold", margin_bottom="1rem"),
                    
                    # Username field
                    rx.input(
                        placeholder="Usuário",
                        value=AuthState.login_username,
                        on_change=AuthState.set_login_username,
                        type="text",
                        width="100%",
                    ),
                    
                    # Password field
                    rx.input(
                        placeholder="Senha",
                        value=AuthState.login_password,
                        on_change=AuthState.set_login_password,
                        type="password",
                        width="100%",
                    ),
                    
                    # Error message
                    rx.cond(
                        AuthState.login_error != "",
                        rx.box(
                            rx.text(
                                AuthState.login_error,
                                color="red",
                                font_size="4",
                            ),
                            padding="2",
                            background="rgba(255,0,0,0.1)",
                            border_radius="6px",
                            width="100%",
                        ),
                    ),
                    
                    # Login button
                    rx.button(
                        rx.cond(
                            AuthState.loading_login,
                            rx.spinner(),
                            rx.text("Entrar"),
                        ),
                        on_click=AuthState.login,
                        width="100%",
                    ),
                    
                    # Demo credentials hint
                    rx.box(
                        rx.text(
                            "Credenciais de teste: admin / admin ou coord / coord",
                            font_size="xs",
                            color="gray",
                            text_align="center",
                        ),
                        padding="2",
                        background="rgba(0,0,255,0.05)",
                        border_radius="6px",
                        width="100%",
                    ),
                    
                    spacing="2",
                    width="100%",
                ),
                width="400px",
                padding="4",
            ),
            
            spacing="4",
            height="100vh",
            justify_content="center",
            align_items="center",
        ),
        width="100vw",
        height="100vh",
    )


# ============================================================================
# PAGE: DASHBOARD
# ============================================================================

def dashboard_page() -> rx.Component:
    """Dashboard page with overview statistics."""
    return main_layout(
        "Dashboard",
        rx.vstack(
            # Page title
            rx.heading("Dashboard", size="7"),
            rx.text("Bem-vindo ao Sistema de Ensalamento FUP", color="gray"),
            
            # Statistics grid
            rx.grid(
                rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("building-2", size=20, color="blue"),
                            rx.heading("Salas", size="4"),
                            spacing="2",
                        ),
                        rx.text(
                            "Total de salas cadastradas",
                            color="gray",
                            font_size="xs",
                        ),
                        spacing="1",
                    ),
                    width="100%",
                ),
                rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("calendar", size=20, color="green"),
                            rx.heading("Alocações", size="4"),
                            spacing="2",
                        ),
                        rx.text(
                            "Alocações realizadas",
                            color="gray",
                            font_size="xs",
                        ),
                        spacing="1",
                    ),
                    width="100%",
                ),
                rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("bookmark", size=20, color="orange"),
                            rx.heading("Reservas", size="4"),
                            spacing="2",
                        ),
                        rx.text(
                            "Reservas ativas",
                            color="gray",
                            font_size="xs",
                        ),
                        spacing="1",
                    ),
                    width="100%",
                ),
                columns="3",
                spacing="4",
                width="100%",
                margin_bottom="4",
            ),
            
            # Recent activity
            rx.card(
                rx.vstack(
                    rx.heading("Informações do Sistema", size="5"),
                    rx.divider(),
                    rx.vstack(
                        rx.text(
                            "• Sistema de Alocação de Salas FUP/UnB",
                            font_size="4",
                        ),
                        rx.text(
                            "• Usuário: admin@fup.unb.br",
                            font_size="4",
                        ),
                        rx.text(
                            "• Ambiente: Desenvolvimento",
                            font_size="4",
                        ),
                        spacing="2",
                    ),
                    spacing="2",
                    width="100%",
                ),
                width="100%",
            ),
            
            spacing="4",
            width="100%",
        ),
    )


# ============================================================================
# PAGE: ALLOCATION
# ============================================================================

def allocation_page() -> rx.Component:
    """Room allocation management page."""
    return main_layout(
        "Ensalamento",
        rx.vstack(
            rx.heading("Gerenciamento de Alocação", size="7"),
            rx.text("Execute alocação autônoma de salas", color="gray"),
            
            rx.card(
                rx.vstack(
                    rx.heading("Executar Ensalamento", size="5"),
                    rx.divider(),
                    rx.vstack(
                        rx.text(
                            "Inicie o processo de alocação automática de salas para os cursos do semestre.",
                            color="gray",
                        ),
                        rx.button(
                            rx.cond(
                                AllocationState.loading_allocation,
                                rx.spinner(),
                                rx.text("Iniciar Ensalamento"),
                            ),
                            width="200px",
                        ),
                        spacing="4",
                    ),
                    spacing="2",
                    width="100%",
                ),
                width="100%",
            ),
            
            spacing="4",
            width="100%",
        ),
    )


# ============================================================================
# PAGE: INVENTORY (Room Management)
# ============================================================================

def inventory_page() -> rx.Component:
    """Room inventory management page."""
    return main_layout(
        "Inventário",
        rx.vstack(
            rx.heading("Gerenciamento de Salas", size="7"),
            rx.text("Gestão do inventário de salas disponíveis", color="gray"),
            
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.heading("Salas Cadastradas", size="5"),
                        rx.spacer(),
                        rx.button("+ Adicionar Sala", size="4"),
                        width="100%",
                    ),
                    rx.divider(),
                    rx.text(
                        "Nenhuma sala carregada ainda. Use o botão acima para adicionar uma sala.",
                        color="gray",
                        font_size="4",
                    ),
                    spacing="2",
                    width="100%",
                ),
                width="100%",
            ),
            
            spacing="4",
            width="100%",
        ),
    )


# ============================================================================
# PAGE: RESERVATIONS
# ============================================================================

def reservations_page() -> rx.Component:
    """Reservation management page."""
    return main_layout(
        "Reservas",
        rx.vstack(
            rx.heading("Gerenciamento de Reservas", size="7"),
            rx.text("Controle de reservas de salas", color="gray"),
            
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.heading("Reservas Ativas", size="5"),
                        rx.spacer(),
                        rx.button("+ Nova Reserva", size="4"),
                        width="100%",
                    ),
                    rx.divider(),
                    rx.text(
                        "Nenhuma reserva encontrada.",
                        color="gray",
                        font_size="4",
                    ),
                    spacing="2",
                    width="100%",
                ),
                width="100%",
            ),
            
            spacing="4",
            width="100%",
        ),
    )


# ============================================================================
# PAGE ROUTING
# ============================================================================

def index() -> rx.Component:
    """Main app entry point with conditional routing."""
    return rx.cond(
        AuthState.is_logged_in,
        # Show app layout if authenticated
        rx.match(
            NavigationState.current_page,
            ("dashboard", dashboard_page()),
            ("allocation", allocation_page()),
            ("inventory", inventory_page()),
            ("reservations", reservations_page()),
            # Default to dashboard
            dashboard_page(),
        ),
        # Show login page if not authenticated
        login_page(),
    )


# ============================================================================
# APP INITIALIZATION
# ============================================================================

app = rx.App(
    theme=rx.theme(
        accent_color="blue",
        gray_color="slate",
        radius="medium",
    )
)

app.add_page(index, title="Ensalamento FUP")
