"""Main Ensalamento Reflex application - Sistema de Ensalamento FUP/UnB."""

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
                rx.text("Ensalamento FUP", font_size="sm", weight="bold"),
                spacing="2",
                padding="1rem",
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
                    "📚 Ensalamento",
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
                    "📋 Reservas",
                    width="100%",
                    on_click=NavigationState.go_to_reservations,
                    variant="surface",
                ),
                spacing="2",
                padding="1rem",
            ),
            
            # User section at bottom
            rx.spacer(),
            rx.divider(),
            rx.vstack(
                rx.text(
                    AuthState.display_name,
                    font_size="sm",
                    weight="semibold",
                ),
                rx.button(
                    "🚪 Sair",
                    width="100%",
                    on_click=AuthState.logout,
                    color_scheme="red",
                    variant="soft",
                ),
                spacing="2",
                padding="1rem",
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
    """Application header with user info."""
    return rx.box(
        rx.hstack(
            rx.text(
                f"Olá, {AuthState.display_name}!",
                font_size="sm",
                weight="semibold",
            ),
            rx.spacer(),
            rx.button(
                "🔔",
                variant="ghost",
            ),
            rx.button(
                "⚙️",
                variant="ghost",
            ),
            spacing="3",
            padding="1rem 2rem",
            align_items="center",
        ),
        width="100%",
        border_bottom="1px solid #e0e0e0",
        background="white",
    )


def main_layout(title: str, content: rx.Component) -> rx.Component:
    """Main layout with sidebar, header, and content area."""
    return rx.box(
        rx.hstack(
            sidebar(),
            rx.vstack(
                header(),
                rx.box(
                    rx.vstack(
                        rx.heading(title, size="4"),
                        content,
                        spacing="4",
                        padding="2rem",
                    ),
                    width="100%",
                    margin_left="200px",
                    overflow="auto",
                    flex="1",
                ),
                spacing="0",
                width="100%",
                height="100vh",
                overflow="hidden",
            ),
            spacing="0",
            width="100%",
            height="100vh",
        ),
        width="100%",
        height="100vh",
    )


# ============================================================================
# LOGIN PAGE
# ============================================================================

def login_page() -> rx.Component:
    """Professional login page with branding."""
    return rx.box(
        rx.vstack(
            # Logo and title
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
                    color="gray.600",
                    text_align="center",
                ),
                spacing="2",
                width="100%",
                margin_bottom="6",
            ),
            
            # Login form
            rx.card(
                rx.vstack(
                    rx.text(
                        "Entrar no Sistema",
                        font_size="lg",
                        weight="semibold",
                        text_align="center",
                    ),
                    rx.divider(),
                    
                    # Username
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
                    
                    # Password
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
                    
                    # Error message
                    rx.cond(
                        AuthState.login_error != "",
                        rx.callout(
                            rx.hstack(
                                rx.icon("alert_circle", size=16),
                                rx.text(AuthState.login_error, font_size="sm"),
                            ),
                            icon_spacing="2",
                            icon="alert_circle",
                            color_scheme="red",
                            role="status",
                        ),
                    ),
                    
                    # Login button
                    rx.button(
                        "Entrar",
                        width="100%",
                        size="2",
                        on_click=AuthState.login,
                        loading=AuthState.loading_login,
                        disabled=AuthState.loading_login,
                    ),
                    
                    # Dev hint
                    rx.text(
                        "Demo: admin/admin",
                        font_size="xs",
                        color="gray.400",
                        text_align="center",
                    ),
                    
                    spacing="4",
                    width="100%",
                ),
                width="400px",
                padding="2rem",
            ),
            
            spacing="6",
            align_items="center",
            justify_content="center",
            min_height="100vh",
            background="linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            width="100%",
        ),
        width="100%",
        height="100vh",
    )


# ============================================================================
# DASHBOARD PAGE
# ============================================================================

def dashboard_page() -> rx.Component:
    """Dashboard with overview and quick actions."""
    return main_layout(
        "Dashboard",
        rx.vstack(
            rx.text(
                "Bem-vindo ao Sistema de Ensalamento FUP!",
                font_size="lg",
                color="gray.600",
            ),
            
            # Quick stats
            rx.hstack(
                rx.stat(
                    rx.stat_label("Total de Salas"),
                    rx.stat_number(rx.cond(RoomState.total_rooms > 0, RoomState.total_rooms, "—")),
                    rx.stat_help_text("Em funcionamento"),
                ),
                rx.stat(
                    rx.stat_label("Reservas Ativas"),
                    rx.stat_number(rx.cond(ReservationState.total_reservations > 0, ReservationState.total_reservations, "—")),
                    rx.stat_help_text("Semestre atual"),
                ),
                rx.stat(
                    rx.stat_label("Alocações"),
                    rx.stat_number("—"),
                    rx.stat_help_text("Última execução"),
                ),
                spacing="4",
                width="100%",
            ),
            
            # Quick actions
            rx.text("Ações Rápidas", font_size="md", weight="semibold", margin_top="2rem"),
            rx.hstack(
                rx.button(
                    "Executar Ensalamento",
                    on_click=lambda: AllocationState.run_autonomous_allocation(20251),
                    loading=AllocationState.loading_allocation,
                ),
                rx.button(
                    "Ver Inventário",
                    on_click=NavigationState.go_to_inventory,
                    variant="soft",
                ),
                rx.button(
                    "Gerenciar Reservas",
                    on_click=NavigationState.go_to_reservations,
                    variant="soft",
                ),
                spacing="3",
            ),
            
            spacing="4",
        ),
    )


# ============================================================================
# ALLOCATION PAGE
# ============================================================================

def allocation_page() -> rx.Component:
    """Room allocation module page."""
    return main_layout(
        "Ensalamento",
        rx.vstack(
            rx.text(
                "Execute o processo automático de alocação de salas.",
                font_size="sm",
                color="gray.600",
            ),
            
            rx.card(
                rx.vstack(
                    rx.text("Alocação Autônoma", font_size="md", weight="semibold"),
                    rx.divider(),
                    
                    rx.vstack(
                        rx.text("Semestre: 2025-1", font_size="sm"),
                        rx.text("Demandas: —", font_size="sm"),
                        rx.text("Status: Aguardando...", font_size="sm"),
                        spacing="2",
                    ),
                    
                    rx.hstack(
                        rx.button(
                            "Executar Alocação",
                            on_click=lambda: AllocationState.run_autonomous_allocation(20251),
                            loading=AllocationState.loading_allocation,
                        ),
                        rx.button(
                            "Importar Dados",
                            on_click=lambda: AllocationState.import_semester_data(20251),
                            loading=AllocationState.loading_import,
                            variant="soft",
                        ),
                        spacing="3",
                    ),
                    
                    # Progress bar
                    rx.cond(
                        AllocationState.loading_allocation | AllocationState.loading_import,
                        rx.vstack(
                            rx.progress(
                                value=AllocationState.allocation_progress / 100
                                if AllocationState.loading_allocation
                                else AllocationState.import_progress / 100,
                            ),
                            rx.text(
                                rx.cond(
                                    AllocationState.loading_allocation,
                                    f"Progresso: {AllocationState.allocation_progress}%",
                                    f"Progresso: {AllocationState.import_progress}%",
                                ),
                                font_size="sm",
                                color="gray.500",
                            ),
                            spacing="2",
                        ),
                    ),
                    
                    spacing="4",
                    width="100%",
                ),
            ),
            
            spacing="4",
        ),
    )


# ============================================================================
# INVENTORY PAGE
# ============================================================================

def inventory_page() -> rx.Component:
    """Room inventory management page."""
    return main_layout(
        "Inventário de Salas",
        rx.vstack(
            rx.text(
                "Gerencie o inventário de salas disponíveis.",
                font_size="sm",
                color="gray.600",
            ),
            
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.input(
                            placeholder="Buscar sala...",
                            on_change=RoomState.set_search_query,
                            width="100%",
                        ),
                        rx.button("+ Nova Sala", on_click=RoomState.toggle_dialog),
                        spacing="2",
                    ),
                    
                    rx.text(
                        rx.cond(
                            RoomState.total_rooms > 0,
                            f"Total: {RoomState.total_rooms} salas",
                            "Nenhuma sala carregada. Clique em 'Carregar' para buscar.",
                        ),
                        font_size="sm",
                        color="gray.500",
                    ),
                    
                    rx.button(
                        "Carregar Salas",
                        on_click=RoomState.load_rooms,
                        width="100%",
                        margin_top="1rem",
                    ),
                    
                    spacing="3",
                    width="100%",
                ),
            ),
            
            spacing="4",
        ),
    )


# ============================================================================
# RESERVATIONS PAGE
# ============================================================================

def reservations_page() -> rx.Component:
    """Reservations management page."""
    return main_layout(
        "Gerenciar Reservas",
        rx.vstack(
            rx.text(
                "Gerencie reservas de salas para eventos especiais.",
                font_size="sm",
                color="gray.600",
            ),
            
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.input(
                            placeholder="Buscar reserva...",
                            on_change=ReservationState.set_search_query,
                            width="100%",
                        ),
                        rx.button("+ Nova Reserva", on_click=ReservationState.toggle_dialog),
                        spacing="2",
                    ),
                    
                    rx.text(
                        rx.cond(
                            ReservationState.total_reservations > 0,
                            f"Total: {ReservationState.total_reservations} reservas",
                            "Nenhuma reserva carregada. Clique em 'Carregar' para buscar.",
                        ),
                        font_size="sm",
                        color="gray.500",
                    ),
                    
                    rx.button(
                        "Carregar Reservas",
                        on_click=ReservationState.load_reservations,
                        width="100%",
                        margin_top="1rem",
                    ),
                    
                    spacing="3",
                    width="100%",
                ),
            ),
            
            spacing="4",
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
        rx.cond(
            NavigationState.current_page == "dashboard",
            dashboard_page(),
            rx.cond(
                NavigationState.current_page == "allocation",
                allocation_page(),
                rx.cond(
                    NavigationState.current_page == "inventory",
                    inventory_page(),
                    rx.cond(
                        NavigationState.current_page == "reservations",
                        reservations_page(),
                        dashboard_page(),
                    ),
                ),
            ),
        ),
        # Show login page if not authenticated
        login_page(),
    )


# ============================================================================
# APP INITIALIZATION
# ============================================================================

app = rx.App()
app.add_page(index)
