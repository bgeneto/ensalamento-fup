"""
Schedule View Page - Sistema de Ensalamento FUP/UnB
Public and admin view of room schedules and allocations
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


def main():
    """Main entry point for the schedule page"""

    # Check authentication
    is_authenticated = st.session_state.get("authentication_status") is True
    username = st.session_state.get("username") if is_authenticated else None
    user_role = AuthServiceRefactored.get_user_role(username) if username else None
    is_admin = user_role == "admin"

    # Configure page based on authentication
    if is_authenticated and is_admin:
        # Admin view with sidebar navigation
        with st.sidebar:
            st.markdown(f"👤 **Administrador:** {username}")
            st.markdown(f"🛠️ **Função:** {user_role}")
            st.markdown("### 🧭 Navegação Rápida")

            if st.button("🏠 Dashboard", use_container_width=True):
                st.switch_page("pages/1_Dashboard.py")

            if st.button("👨‍👨‍👦‍👦 Usuários", use_container_width=True):
                st.switch_page("pages/2_Admin_Users.py")

            if st.button("🏫 Salas", use_container_width=True):
                st.switch_page("pages/3_Admin_Rooms.py")

            if st.button("📊 Alocações", use_container_width=True):
                st.switch_page("pages/4_Admin_Allocations.py")

            st.markdown("---")
            # Logout button
            authenticator = AuthServiceRefactored.get_authenticator()
            authenticator.logout("🏃 Sair", "sidebar", use_container_width=True)

    # Main schedule content
    st.title("📅 Grade de Horários")
    st.caption("Consulte a grade completa de horários das salas")

    # Placeholder for schedule view
    st.info("🔄 Página de grade de horários em desenvolvimento")
    st.markdown("- Visualização unificada de aulas e reservas")
    st.markdown("- Filtros por sala, professor ou disciplina")
    st.markdown("- Exportação para PDF")


if __name__ == "__main__":
    main()
