"""
Main entry point for Sistema de Ensalamento FUP/UnB
Streamlit multipage application with authentication
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Set page configuration
st.set_page_config(
    page_title="Sistema de Ensalamento FUP/UnB",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Import services after path setup
from src.services.auth_service import AuthService
from config import APP_VERSION


def check_initialization():
    """Check if system is properly initialized"""
    try:
        from src.services.setup_service import SetupService

        status = SetupService.get_setup_status()
        return status
    except Exception as e:
        return {
            "is_initialized": False,
            "error": str(e),
            "completion_percentage": 0,
            "ready_for_use": False,
            "database_stats": {},
        }


def initialize_system():
    """Initialize the system if not already done"""
    try:
        from src.services.setup_service import SetupService
        from src.services.auth_service import AuthService

        with st.spinner("Inicializando banco de dados..."):
            # Initialize database schema
            if not SetupService.initialize_database():
                st.error("❌ Falha ao inicializar o banco de dados")
                return False

        with st.spinner("Populando dados iniciais..."):
            # Seed initial data
            if not SetupService.seed_all_data():
                st.error("❌ Falha ao popular dados iniciais")
                return False

        with st.spinner("Criando usuário administrador..."):
            # Create initial admin user
            if not AuthService.create_initial_admin():
                st.error("❌ Falha ao criar usuário administrador")
                return False

        st.success("✅ Sistema inicializado com sucesso!")
        st.rerun()
        return True

    except Exception as e:
        st.error(f"❌ Erro durante inicialização: {str(e)}")
        return False


def render_public_dashboard():
    """Render the public dashboard for anonymous users"""
    st.title("🏫 Sistema de Ensalamento FUP/UnB")
    st.caption("Sistema integrado de gestão de salas e reservas")

    st.markdown("---")
    st.markdown("### 🏫 **Visualizar Horários e Reservas**")
    st.info(
        "✅ **Acesso público** - Não é necessário fazer login para visualizar a grade de horários."
    )

    # Access buttons for public features
    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "📅 Ver Grade de Horários", type="primary", use_container_width=True
        ):
            st.session_state.public_page = "schedule"
            st.rerun()

    with col2:
        if st.button("🔍 Buscar Salas Disponíveis", use_container_width=True):
            st.session_state.public_page = "search"
            st.rerun()

    # Show schedule if selected
    if st.session_state.get("public_page") == "schedule":
        st.markdown("---")
        render_public_schedule()

    if st.session_state.get("public_page") == "search":
        st.markdown("---")
        render_public_search()

    # Login access
    st.markdown("---")
    st.markdown("### 🔐 **Acesso Administrador**")

    st.info(
        "🔒 **Acesso restrito** - Faça login para gerenciar reservas, usuários e configurações do sistema."
    )

    if st.button("🔐 Entrar como Administrador", use_container_width=True):
        st.session_state.show_login = True
        st.rerun()

    # Show login form when requested
    if st.session_state.get("show_login"):
        render_login_page()


def render_public_schedule():
    """Render public schedule view"""
    st.subheader("📅 Grade de Horários - Visualização Pública")
    st.caption("Consulte os horários das aulas e reservas")

    # Placeholder for schedule view
    st.info("🔄 Visualização de grade em desenvolvimento")
    st.markdown("- Mostra aulas semestrais e reservas especiais")
    st.markdown("- Filtros por sala, data e tipo")
    st.markdown("- Interface amigável para consulta rápida")


def render_public_search():
    """Render public room search"""
    st.subheader("🔍 Buscar Salas Disponíveis")
    st.caption("Encontre salas livres para reserva")

    # Placeholder for search functionality
    st.info("🔄 Busca de salas em desenvolvimento")
    st.markdown("- Calendário com disponibilidade")
    st.markdown("- Filtros por capacidade, equipamentos")
    st.markdown("- Visualização de conflitos")


def render_admin_dashboard():
    """Render the admin dashboard for authenticated admin users"""
    st.title("🏫 Sistema de Ensalamento FUP/UnB - Painel Administrativo")
    st.caption("Sistema integrado de gestão de salas e reservas")

    # Check system status
    status = check_initialization()

    if not status["is_initialized"]:
        st.error("🚨 Sistema não inicializado")
        st.info("Por favor, inicialize o sistema primeiro.")

        if st.button("🚀 Inicializar Sistema", type="primary"):
            initialize_system()
        return

    # Display system status
    st.header("📊 Status do Sistema")

    col1, col2, col3, col4 = st.columns(4)

    stats = status.get("database_stats", {})

    with col1:
        st.metric("Salas", stats.get("salas", 0))

    with col2:
        st.metric("Semestres", stats.get("semestres", 0))

    with col3:
        st.metric("Alocações", stats.get("alocacoes_semestrais", 0))

    with col4:
        st.metric("Reservas", stats.get("reservas_esporadicas", 0))

    # System readiness indicator
    completion = status.get("completion_percentage", 0)
    ready = status.get("ready_for_use", False)

    if ready:
        st.success("✅ Pronto para uso")
    elif completion >= 50:
        st.warning("⚠️ Configuração parcial")
    else:
        st.error("❌ Configuração incompleta")

    st.progress(completion / 100)
    st.write(f"Progresso: {completion:.1f}%")

    # Admin quick access section
    st.header("🚀 Painel de Controle Administrativo")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("📝 **Gerenciar Reservas**\n\nCriar e editar reservas de salas")

    with col2:
        st.info("👥 **Gerenciar Usuários**\n\nAdministrar acessos ao sistema")

    with col3:
        st.info("🏢 **Gerenciar Inventário**\n\nSalas, prédios e configurações")

    # System information
    with st.expander("ℹ️ Informações do Sistema"):
        st.json(
            {
                "Versão": APP_VERSION,
                "Status": "Pronto" if ready else "Em configuração",
                "Banco de Dados": "SQLite",
                "Framework": "Streamlit",
                "Estatísticas": stats,
            }
        )


def render_navigation():
    """Render sidebar navigation"""
    with st.sidebar:
        st.markdown("### 🧭 Navegação")

        # Main navigation
        if st.button("🏠 Página Inicial", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

        if st.button("📅 Grade de Horários", use_container_width=True):
            st.session_state.page = "schedule"
            st.rerun()

        if st.button("🔍 Buscar Salas", use_container_width=True):
            st.session_state.page = "search"
            st.rerun()

        st.markdown("---")

        # User actions
        st.markdown("### 👤 Ações do Usuário")

        if st.button("📝 Fazer Reserva", use_container_width=True):
            st.session_state.page = "reserve"
            st.rerun()

        if st.button("📋 Minhas Reservas", use_container_width=True):
            st.session_state.page = "my_reservations"
            st.rerun()

        # Admin section (placeholder)
        st.markdown("---")
        st.markdown("### ⚙️ Administração")

        if st.button("🔐 Login Administrador", use_container_width=True):
            st.session_state.page = "admin_login"
            st.rerun()

        st.markdown("---")

        # System status in sidebar
        status = check_initialization()
        completion = status.get("completion_percentage", 0)

        st.markdown("### 📊 Status do Sistema")

        # Progress bar
        st.progress(completion / 100)
        st.write(f"Concluído: {completion:.1f}%")

        if status.get("ready_for_use", False):
            st.success("✅ Sistema pronto")
        else:
            st.warning("⚠️ Configuração necessária")


def render_login_page():
    """Render login page for unauthenticated users"""
    # Check system status
    status = check_initialization()

    if not status["is_initialized"]:
        st.title("🚀 Inicialização do Sistema")
        st.info("O sistema precisa ser inicializado antes do primeiro uso.")

        if st.button("🚀 Inicializar Sistema", type="primary"):
            initialize_system()
        return

    # Show login widget
    st.title("🔐 Acesso ao Sistema")

    # Use Brazilian Portuguese labels
    fields = {
        "Form name": "Login",
        "Username": "Nome de Usuário",
        "Password": "Senha",
        "Login": "Entrar",
        "Captcha": "Captcha",
    }

    try:
        authenticator = AuthService.get_authenticator()

        # Initialize streamlit-authenticator session state if needed
        if "logout" not in st.session_state:
            st.session_state["logout"] = False
        if "authentication_status" not in st.session_state:
            st.session_state["authentication_status"] = None

        authenticator.login(location="main", fields=fields, clear_on_submit=True)

        # Handle authentication status
        if st.session_state.get("authentication_status") is False:
            st.error("❌ Usuário/senha incorreta")
        elif st.session_state.get("authentication_status") is None:
            st.warning("🔑 Entre com seu usuário e senha")

        # Handle logout if user clicked logout
        if st.session_state.get("logout"):
            # Clear authentication-related session state
            if "authentication_status" in st.session_state:
                del st.session_state["authentication_status"]
            if "username" in st.session_state:
                del st.session_state["username"]
            if "role" in st.session_state:
                del st.session_state["role"]
            if "logout" in st.session_state:
                del st.session_state["logout"]

            # Reset logout flag
            st.session_state["logout"] = False
            st.rerun()

    except Exception as e:
        st.error(f"❌ Erro no sistema de autenticação: {str(e)}")
        st.info("Se este é o primeiro uso, inicialize o sistema.")


def render_authenticated_app():
    """Render the main app for authenticated users (admin only)"""
    authenticator = AuthService.get_authenticator()

    # Get user information
    username = st.session_state.get("username")
    user_role = AuthService.get_user_role(username) if username else None

    # Only allow admin users
    if user_role != "admin":
        st.error("🔒 Acesso negado. Apenas administradores têm acesso ao sistema.")
        authenticator.logout("🏃‍ Sair", "main")
        return

    # Handle logout
    with st.sidebar:
        st.markdown(f"👤 **Administrador:** {username}")
        st.markdown(f"🛠️ **Função:** {user_role}")

        # Logout button
        authenticator.logout("🏃 Sair", "sidebar", use_container_width=True)

    # Initialize session state for navigation
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"

    # Render main navigation for admin
    render_admin_navigation()

    # Render page content
    if st.session_state.page == "dashboard":
        render_admin_dashboard()
    elif st.session_state.page == "schedule":
        render_schedule_page()
    elif st.session_state.page == "search":
        render_search_page()
    elif st.session_state.page == "reserve":
        render_reserve_page()
    elif st.session_state.page == "user_management":
        render_admin_user_management()
    elif st.session_state.page == "inventory":
        render_admin_inventory()
    elif st.session_state.page == "allocations":
        render_admin_allocations()
    else:
        render_admin_dashboard()


def render_main_navigation():
    """Render main navigation sidebar"""
    with st.sidebar:
        st.markdown("### 🧭 Navegação Principal")

        # Public pages - always available
        if st.button("🏠 Página Inicial", use_container_width=True):
            st.session_state.page = "home"

        if st.button("📅 Grade de Horários", use_container_width=True):
            st.session_state.page = "schedule"

        if st.button("🔍 Buscar Salas", use_container_width=True):
            st.session_state.page = "search"

        st.markdown("### 👤 Minha Conta")

        # User-specific pages (logged in users only)
        if st.button("📝 Fazer Reserva", use_container_width=True):
            st.session_state.page = "reserve"

        if st.button("📋 Minhas Reservas", use_container_width=True):
            st.session_state.page = "my_reservations"

        # Admin-only section
        username = st.session_state.get("username")
        user_role = AuthService.is_admin(username) if username else False
        user_role = "admin" if user_role else "professor"

        if user_role == "admin":
            st.markdown("### ⚙️ Administração")

            if st.button("👥 Gerenciar Usuários", use_container_width=True):
                st.session_state.page = "admin_user_management"

            if st.button("🏢 Gerenciar Inventário", use_container_width=True):
                st.session_state.page = "admin_inventory"

            if st.button("📊 Gerenciar Alocações", use_container_width=True):
                st.session_state.page = "admin_allocations"


def render_schedule_page():
    """Render schedule viewing page"""
    st.title("📅 Grade de Horários")
    st.caption("Consulte a grade completa de horários das salas")

    # Placeholder - will be implemented
    st.info("🔄 Página de grade de horários em desenvolvimento")
    st.markdown("- Visualização unificada de aulas e reservas")
    st.markdown("- Filtros por sala, professor ou disciplina")
    st.markdown("- Exportação para PDF")


def render_search_page():
    """Render room search page"""
    st.title("🔍 Buscar Salas")
    st.caption("Encontre salas disponíveis com filtros específicos")

    # Placeholder - will be implemented
    st.info("🔄 Página de busca em desenvolvimento")
    st.markdown("- Filtros por data, horário, tipo de sala")
    st.markdown("- Características especiais (projetor, acessibilidade, etc.)")
    st.markdown("- Capacidade e localização")


def render_reserve_page():
    """Render room reservation page"""
    st.title("📝 Fazer Reserva")
    st.caption("Reserve uma sala ou espaço para seu evento")

    # Placeholder - will be implemented
    st.info("🔄 Sistema de reservas em desenvolvimento")
    st.markdown("- Seleção de data e blocos de horário")
    st.markdown("- Verificação de conflitos em tempo real")
    st.markdown("- Aprovação automática ou manual")


def render_admin_user_management():
    """Render admin user management"""
    st.title("👥 Gerenciamento de Usuários")
    st.caption("Administre usuários e permissões do sistema")

    try:
        from src.pages.admin import usuarios

        usuarios.render_usuarios_page()
    except Exception as e:
        st.error(f"Erro ao carregar gerenciamento de usuários: {e}")


def render_admin_inventory():
    """Render admin inventory management"""
    st.title("🏢 Gerenciamento de Inventário")
    st.caption("Gerencie salas, prédios e características")

    st.info("🔄 Módulo de inventário em desenvolvimento")
    # This will be implemented with imports from admin pages


def render_admin_allocations():
    """Render admin allocation management"""
    st.title("📊 Gerenciamento de Alocações")
    st.caption("Controle e otimize o ensalamento semestral")

    st.info("🔄 Módulo de alocações em desenvolvimento")
    # This will be implemented with imports from admin pages


def render_admin_navigation():
    """Render navigation sidebar for admin users"""
    with st.sidebar:
        st.markdown("### 📊 **Painel Administrativo**")

        if st.button("🏠 Dashboard", use_container_width=True):
            st.session_state.page = "dashboard"

        st.markdown("### 👁️ **Consulta**")

        if st.button("📅 Ver Grade de Horários", use_container_width=True):
            st.session_state.page = "schedule"

        if st.button("🔍 Buscar Salas", use_container_width=True):
            st.session_state.page = "search"

        st.markdown("### ⚙️ **Administração**")

        if st.button("📝 Gerenciar Reservas", use_container_width=True):
            st.session_state.page = "reserve"

        if st.button("👥 Gerenciar Usuários", use_container_width=True):
            st.session_state.page = "user_management"

        if st.button("🏢 Gerenciar Inventário", use_container_width=True):
            st.session_state.page = "inventory"

        if st.button("📊 Gerenciar Alocações", use_container_width=True):
            st.session_state.page = "allocations"


def main():
    """Main application entry point with authentication"""

    # Handle authentication first
    if st.session_state.get("authentication_status") is True:
        # User is authenticated - show admin interface
        render_authenticated_app()
    else:
        # User is not authenticated - show public interface
        render_public_dashboard()

    # Footer
    st.markdown("---")
    st.markdown(
        f"Sistema de Ensalamento FUP/UnB v{APP_VERSION} | Desenvolvido por bgeneto © 2025"
    )


if __name__ == "__main__":
    main()
