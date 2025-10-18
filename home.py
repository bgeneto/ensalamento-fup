"""
Main entry point for Sistema de Ensalamento FUP/UnB
Streamlit multipage application
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

# Using default Streamlit styling only


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


def render_home_dashboard():
    """Render the home dashboard"""
    st.title("🏫 Sistema de Ensalamento FUP/UnB")
    st.caption("Sistema integrado de gestão de salas e reservas")

    # Check system status
    status = check_initialization()

    if not status["is_initialized"]:
        st.error("🚨 Sistema não inicializado")
        st.info("Por favor, inicialize o sistema para começar a usar.")

        if st.button(
            "🚀 Inicializar Sistema", type="primary", use_container_width=True
        ):
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

    # Quick access section
    st.header("🚀 Acesso Rápido")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("📅 **Visualizar Grade**\n\nConsulte a grade de horários das salas")

    with col2:
        st.info("🔍 **Buscar Salas**\n\nEncontre salas disponíveis")

    with col3:
        st.info("📝 **Fazer Reserva**\n\nReserve uma sala para seu evento")

    # Recent activity
    st.header("📈 Atividade Recente")
    st.info("📋 Funcionalidade de atividade recente será implementada em breve.")

    # System information
    with st.expander("ℹ️ Informações do Sistema"):
        st.json(
            {
                "Versão": "1.0.0",
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


def main():
    """Main application entry point"""
    # Initialize session state
    if "page" not in st.session_state:
        st.session_state.page = "home"

    # Render navigation sidebar
    render_navigation()

    # Render main content based on current page
    if st.session_state.page == "home":
        render_home_dashboard()
    elif st.session_state.page == "schedule":
        st.info("📅 Página de Grade de Horários - Em desenvolvimento")
        if st.button("Voltar"):
            st.session_state.page = "home"
            st.rerun()
    elif st.session_state.page == "search":
        st.info("🔍 Página de Busca de Salas - Em desenvolvimento")
        if st.button("Voltar"):
            st.session_state.page = "home"
            st.rerun()
    elif st.session_state.page == "reserve":
        st.info("📝 Página de Reservas - Em desenvolvimento")
        if st.button("Voltar"):
            st.session_state.page = "home"
            st.rerun()
    elif st.session_state.page == "my_reservations":
        st.info("📋 Página de Minhas Reservas - Em desenvolvimento")
        if st.button("Voltar"):
            st.session_state.page = "home"
            st.rerun()
    elif st.session_state.page == "admin_login":
        st.info("🔐 Página de Login Administrador - Em desenvolvimento")
        if st.button("Voltar"):
            st.session_state.page = "home"
            st.rerun()
    else:
        render_home_dashboard()

    # Footer
    st.markdown("---")
    st.markdown("Sistema de Ensalamento FUP/UnB v1.0.0 | Desenvolvido com Streamlit")


if __name__ == "__main__":
    main()
