"""
Admin Dashboard Page - Sistema de Ensalamento FUP/UnB
Main administrative dashboard with system overview and quick access
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import services after path setup
from src.services.auth_service_refactored import AuthServiceRefactored
from config import APP_VERSION
from src.pages.admin.usuarios import render_usuarios_page
from src.pages.admin.salas import render_salas_page
from src.pages.admin.alocacoes import render_alocacoes_page


def main():
    """Main entry point for the admin dashboard page"""

    # Check authentication - redirect to home if not authenticated
    if st.session_state.get("authentication_status") is not True:
        st.error("🔒 Acesso negado. Faça login primeiro.")
        st.page_link("pages/home_public.py", label="← Voltar para a página inicial")
        return

    # Check user role - must be admin
    username = st.session_state.get("username")
    user_role = AuthServiceRefactored.get_user_role(username) if username else None
    if user_role != "admin":
        st.error("🔒 Acesso negado. Apenas administradores têm acesso a esta área.")
        if st.button("🏠 Voltar ao Início"):
            st.switch_page("pages/home_public.py")
        return

    # Display user info in sidebar
    with st.sidebar:
        st.markdown(f"👤 **Administrador:** {username}")
        st.markdown(f"🛠️ **Função:** {user_role}")
        st.markdown("### 🧭 Navegação Rápida")

        if st.button("👨‍👨‍👦‍👦 Gerenciar Usuários", use_container_width=True):
            st.switch_page("pages/2_Admin_Users.py")

        if st.button("🏫 Gerenciar Salas", use_container_width=True):
            st.switch_page("pages/3_Admin_Rooms.py")

        if st.button("📊 Gerenciar Alocações", use_container_width=True):
            st.switch_page("pages/4_Admin_Allocations.py")

        if st.button("📅 Ver Grade de Horários", use_container_width=True):
            st.switch_page("pages/5_Schedule.py")

        st.markdown("---")
        # Logout button
        authenticator = AuthServiceRefactored.get_authenticator()
        authenticator.logout("🏃 Sair", "sidebar", use_container_width=True)

    # Main dashboard content
    try:
        render_admin_dashboard()
    except Exception as e:
        error_str = str(e)
        error_type = type(e).__name__

        # Check for various DetachedInstance error patterns
        if (
            "DetachedInstance" in error_str
            or "detached" in error_str.lower()
            or "not bound to a Session" in error_str
        ):
            st.error("❌ Erro na conexão com o banco de dados.")
            st.info("📊 **Para resolver este problema:**")
            st.markdown("1. **Atualize a página** (pressione F5)")
            st.markdown("2. **Limpe o cache do navegador** se o problema persistir")
            st.markdown("3. **Feche e reabra o navegador** se necessário")
            if st.button("🔄 Atualizar Página Agora", type="primary"):
                st.rerun()
        else:
            # For other errors, show simplified message
            st.error("❌ Erro ao carregar dashboard.")
            st.warning("Entre em contato com o administrador se o problema persistir.")

            # Debug info for developer (expandable)
            with st.expander("ℹ️ Detalhes técnicos (para administrador)"):
                st.code(f"Erro: {error_str}\nTipo: {error_type}")


def render_admin_dashboard():
    """Render the main admin dashboard"""
    st.title("🏫 Sistema de Ensalamento FUP/UnB - Painel Administrativo")
    st.caption("Sistema integrado de gestão de salas e reservas")

    # Check system initialization status
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
    st.caption(f"Progresso: {completion:.1f}%")

    # Admin quick access section
    st.header("🚀 Painel de Controle Administrativo")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(
            "👨‍👨‍👦‍👦 Gerenciar Usuários", type="primary", use_container_width=True
        ):
            st.switch_page("pages/2_Admin_Users.py")

    with col2:
        if st.button(
            "🏢 Gerenciar Inventário", type="primary", use_container_width=True
        ):
            st.switch_page("pages/3_Admin_Rooms.py")

    with col3:
        if st.button(
            "📊 Gerenciar Alocações", type="primary", use_container_width=True
        ):
            st.switch_page("pages/4_Admin_Allocations.py")

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
        from src.services.auth_service_refactored import AuthServiceRefactored

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
            if not AuthServiceRefactored.create_initial_admin():
                st.error("❌ Falha ao criar usuário administrador")
                return False

        st.success("✅ Sistema inicializado com sucesso!")
        st.rerun()
        return True

    except Exception as e:
        st.error(f"❌ Erro durante inicialização: {str(e)}")
        return False


if __name__ == "__main__":
    main()
