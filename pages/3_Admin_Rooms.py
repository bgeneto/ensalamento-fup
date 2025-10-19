"""
Admin Rooms Management Page - Sistema de Ensalamento FUP/UnB
Administrative interface for managing rooms, types, and characteristics
"""

import streamlit as st
import sys
import os
import logging
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Setup logging
logger = logging.getLogger(__name__)

# Import services and error handling
from src.services.auth_service_refactored import AuthServiceRefactored
from src.utils.error_handler import DatabaseErrorHandler


# Wrap the entire page execution in try/catch to handle DetachedInstanceError
# that may occur during Streamlit page initialization
try:
    # Move imports inside try block to catch import errors
    from src.pages.admin.salas import render_salas_page

    def main():
        """Main entry point for the admin rooms page"""

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

            if st.button("🏠 Dashboard", use_container_width=True):
                st.switch_page("pages/1_Dashboard.py")

            if st.button("👨‍👨‍👦‍👦 Usuários", use_container_width=True):
                st.switch_page("pages/2_Admin_Users.py")

            if st.button("📊 Alocações", use_container_width=True):
                st.switch_page("pages/4_Admin_Allocations.py")

            st.markdown("---")
            # Logout button
            authenticator = AuthServiceRefactored.get_authenticator()
            authenticator.logout("🏃 Sair", "sidebar", use_container_width=True)

        # Main content - delegate to existing rooms page
        try:
            render_salas_page()
        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__

            # Check for various DetachedInstance error patterns
            if DatabaseErrorHandler.is_detached_instance_error(e):
                st.error("❌ Erro na conexão com o banco de dados.")
                st.info("📊 **Para resolver este problema:**")
                st.markdown("1. **Atualize a página** (pressione F5)")
                st.markdown("2. **Limpe o cache do navegador** se o problema persistir")
                st.markdown("3. **Feche e reabra o navegador** se necessário")
                if st.button("🔄 Atualizar Página Agora", type="primary"):
                    st.rerun()
            else:
                # For other errors, show simplified message
                st.error("❌ Erro ao carregar página de salas.")
                st.warning(
                    "Entre em contato com o administrador se o problema persistir."
                )

                # Debug info for developer (expandable)
                with st.expander("ℹ️ Detalhes técnicos (para administrador)"):
                    st.code(f"Erro: {error_str}\nTipo: {error_type}")

    def run_page():
        """Safe wrapper to run the page and handle all exceptions"""
        try:
            main()
        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__

            logger.exception(f"Error in Admin Rooms page: {e}")

            if DatabaseErrorHandler.is_detached_instance_error(e):
                st.error("❌ Erro na conexão com o banco de dados.")
                st.info("📊 **Para resolver este problema:**")
                st.markdown("1. **Atualize a página** (pressione F5)")
                st.markdown("2. **Limpe o cache do navegador** se o problema persistir")
                st.markdown("3. **Feche e reabra o navegador** se necessário")
                if st.button("🔄 Atualizar Página Agora", type="primary"):
                    st.rerun()
            else:
                st.error("❌ Erro crítico na página.")
                st.error("Por favor, recarregue a página ou contate o administrador.")
                with st.expander("ℹ️ Detalhes do erro"):
                    st.code(f"{error_type}: {error_str}")

    run_page()

except Exception as e:
    # Catch ANY exception during page loading, including DetachedInstanceError
    error_str = str(e)
    error_type = type(e).__name__

    logger.exception(f"Critical error loading Admin Rooms page: {e}")

    if DatabaseErrorHandler.is_detached_instance_error(e):
        st.error("❌ Erro na conexão com o banco de dados.")
        st.info("📊 **Para resolver este problema:**")
        st.markdown("1. **Atualize a página** (pressione F5)")
        st.markdown("2. **Limpe o cache do navegador** se o problema persistir")
        st.markdown("3. **Feche e reabra o navegador** se necessário")
        if st.button("🔄 Atualizar Página Agora", type="primary"):
            st.rerun()
    else:
        st.error("❌ Erro ao carregar a página.")
        st.info("Tente refrescar a página ou entre em contato com o administrador.")
        with st.expander("ℹ️ Detalhes técnicos"):
            st.code(f"{error_type}: {error_str}")
