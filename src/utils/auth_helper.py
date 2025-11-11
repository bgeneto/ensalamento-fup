"""
Authentication helper utilities for Streamlit pages.

Provides robust authentication checking and page protection decorators
that work correctly with streamlit-authenticator cookies.
"""

import streamlit as st
from typing import Callable, Any


def require_auth():
    """
    Decorator to protect a page/function with authentication requirement.

    Properly handles session state initialization from streamlit-authenticator cookies.
    Unlike a simple boolean check, this ensures the auth state is fully initialized.

    Usage:
        @require_auth()
        def render_page():
            st.write("This page is protected")
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Check authentication status
            # None means not yet checked, False means invalid credentials, True means authenticated
            auth_status = st.session_state.get("authentication_status")

            if auth_status is None:
                # Authentication check hasn't been run yet
                # This shouldn't happen if 0_🔓_Login.py ran the authenticator properly,
                # but we handle it gracefully
                st.warning(
                    "⏳ Inicializando autenticação... Por favor, recarregue a página."
                )
                st.stop()
            elif auth_status is False:
                # User tried to login but credentials were invalid
                st.error("❌ Usuário ou senha inválidos.")
                st.stop()
            elif auth_status is True:
                # User is authenticated - proceed
                return func(*args, **kwargs)
            else:
                # Unexpected state
                st.error(
                    "❌ Estado de autenticação inválido. Por favor, recarregue a página."
                )
                st.stop()

        return wrapper

    return decorator


def check_auth_and_stop() -> bool:
    """
    Check if user is authenticated and stop page if not.

    Returns True if authenticated, False if not (after stopping).
    This is the simple version for inline use (not decorator).

    Usage:
        if not check_auth_and_stop():
            st.stop()
    """
    auth_status = st.session_state.get("authentication_status")

    if auth_status is None:
        # Session state not initialized yet
        # This can happen on very first load - just show a loading message
        st.info(
            "⏳ Autenticando... Se esta mensagem persistir, por favor faça login na página inicial."
        )
        st.stop()
    elif auth_status is False:
        st.error("❌ Usuário ou senha inválidos.")
        st.stop()
    elif auth_status is True:
        # Authenticated
        return True

    return False


def require_auth_with_redirect_to_main():
    """
    Check authentication and provide link to main page if not authenticated.

    This version is more user-friendly - instead of just stopping,
    it directs users to the main login page.
    """
    auth_status = st.session_state.get("authentication_status")

    if auth_status is not True:
        st.warning(
            "🔐 Esta página requer autenticação. "
            "Por favor, volte à página inicial (**Home**) e faça login."
        )

        if auth_status is False:
            st.error("❌ Último acesso foi negado. Credenciais inválidas.")

        st.stop()
