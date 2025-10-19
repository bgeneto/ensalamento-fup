"""
Public Home Page - Sistema de Ensalamento FUP/UnB
Landing page for public access and login
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


def main():
    """Main entry point for the public home page"""

    # Check if system is authenticated
    if st.session_state.get("authentication_status") is True:
        username = st.session_state.get("username")
        user_role = AuthServiceRefactored.get_user_role(username) if username else None

        if user_role == "admin":
            # Redirect admin users to dashboard
            st.switch_page("pages/1_Dashboard.py")
            return
        else:
            # For now, also redirect - could show different interface for professors later
            st.switch_page("pages/1_Dashboard.py")
            return

    # Show public interface
    render_public_home()


def render_public_home():
    """Render the public home page"""
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
        if st.page_link("pages/5_Schedule.py", label="📅 Ver Grade de Horários"):
            pass

    with col2:
        if st.page_link(
            "pages/home_public.py", label="🔍 Buscar Salas Disponíveis", disabled=True
        ):
            pass

    # Admin access section
    st.markdown("---")
    st.markdown("### 🔐 **Acesso Administrador**")
    st.info(
        "🔒 **Acesso restrito** - Faça login para gerenciar reservas, usuários e configurações do sistema."
    )

    # Show login form directly on this page
    render_login_form()


def render_login_form():
    """Render login form"""
    # Check system initialization
    status = check_initialization()

    if not status["is_initialized"]:
        st.title("🚀 Inicialização do Sistema")
        st.info("O sistema precisa ser inicializado antes do primeiro uso.")

        if st.button("🚀 Inicializar Sistema", type="primary"):
            initialize_system()
        return

    # Use Brazilian Portuguese labels
    fields = {
        "Form name": "Login",
        "Username": "Nome de Usuário",
        "Password": "Senha",
        "Login": "Entrar",
        "Captcha": "Captcha",
    }

    try:
        authenticator = AuthServiceRefactored.get_authenticator()

        # Initialize streamlit-authenticator session state if needed
        if "logout" not in st.session_state:
            st.session_state["logout"] = False
        if "authentication_status" not in st.session_state:
            st.session_state["authentication_status"] = None

        authenticator.login(location="main", fields=fields, clear_on_submit=True)

        # Handle authentication status
        if st.session_state.get("authentication_status") is False:
            st.error("❌ Usuário e/ou senha incorretos")
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
