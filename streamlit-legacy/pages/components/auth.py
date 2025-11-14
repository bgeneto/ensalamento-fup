"""
Reusable Authentication and Page Initialization Component

Provides a single, configurable function for handling authentication and page setup
across all login-protected pages in the application.

This eliminates code duplication and ensures consistent auth behavior.
"""

import streamlit as st


def initialize_page(
    page_title: str,
    page_icon: str,
    layout: str = "wide",
    key_suffix: str = "",
    requires_auth: bool = True,
) -> bool:
    """
    Initialize page with authentication and configuration.

    Args:
        page_title: Streamlit page title (e.g., "Home - Ensalamento")
        page_icon: Streamlit page icon (e.g., "🏠")
        layout: Streamlit layout, defaults to "wide"
        key_suffix: Unique suffix for this page's auth keys (e.g., "home", "professores")
        requires_auth: Whether this page requires authentication (default: True)

    Returns:
        bool: True if authentication succeeds (or not required), False otherwise (page should stop)

    Example usage:
        if not initialize_page(
            page_title="Professores - Ensalamento",
            page_icon="👨‍🏫",
            layout="wide",
            key_suffix="professores"
        ):
            st.stop()
    """

    # ============================================================================
    # AUTHENTICATION CHECK (only if required)
    # ============================================================================
    if requires_auth:
        # Retrieve authenticator from session state (set by 0_🔓_Login.py)
        authenticator = st.session_state.get("authenticator")

        if authenticator is None:
            st.switch_page("0_🔓_Login.py")
            return False

        # Generate unique keys for this page
        auth_key = f"authenticator-{key_suffix}"
        logout_key = f"logout-{key_suffix}"

        # Call login with unrendered location to maintain session (required for page refresh fix)
        try:
            authenticator.login(location="unrendered", key=auth_key)
        except Exception as exc:
            st.switch_page("0_🔓_Login.py")
            return False

        auth_status = st.session_state.get("authentication_status")

        if auth_status:
            # Show semester badge in sidebar
            from pages.components.ui.semester_badge import show as show_semester_badge

            show_semester_badge()

            # st.sidebar.markdown("---")

            # Show logout button in sidebar
            authenticator.logout(
                location="sidebar", key=logout_key, use_container_width=True
            )
        else:
            # Not authenticated - redirect to login page
            st.switch_page("0_🔓_Login.py")
            return False

    # ============================================================================
    # PAGE CONFIG
    # ============================================================================

    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout=layout,
    )

    # Authentication successful (or not required)
    return True
