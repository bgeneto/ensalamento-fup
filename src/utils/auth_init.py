"""
Shared authentication utilities for all pages.

This module provides utilities to check authentication status properly.
The key insight: streamlit-authenticator maintains auth state in st.session_state
from cookies. When 0_🔓_Login.py runs and calls authenticator.login(), it populates
st.session_state globally for all pages. Pages just need to check this state.
"""

import streamlit as st


def require_auth_or_redirect():
    """
    Check if user is authenticated. If not, show error and redirect instructions.

    This should be called at the TOP of every page (before page_config).
    Returns True if authenticated, stops execution if not.
    """
    auth_status = st.session_state.get("authentication_status")

    # If authentication_status is None or False, user is not authenticated
    if auth_status is not True:
        st.error("❌ Acesso negado. Faça login primeiro.")
        st.info("👈 Volte à página inicial (Home) no menu lateral para fazer login.")
        st.stop()
        return False

    return True
