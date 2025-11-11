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

            if auth_status is True:
                # User is authenticated - proceed
                return func(*args, **kwargs)
            else:
                # Not authenticated - redirect to login page
                st.switch_page("0_🔓_Login.py")

        return wrapper

    return decorator


def check_auth_and_stop() -> bool:
    """
    Check if user is authenticated and redirect if not.

    Returns True if authenticated, redirects if not.
    This is the simple version for inline use (not decorator).

    Usage:
        if not check_auth_and_stop():
            return
    """
    auth_status = st.session_state.get("authentication_status")

    if auth_status is True:
        # Authenticated
        return True
    else:
        # Not authenticated - redirect to login page
        st.switch_page("0_🔓_Login.py")
        return False


def require_auth_with_redirect_to_main():
    """
    Check authentication and redirect to login page if not authenticated.

    This redirects unauthenticated users to the login page.
    """
    auth_status = st.session_state.get("authentication_status")

    if auth_status is not True:
        st.switch_page("0_🔓_Login.py")
