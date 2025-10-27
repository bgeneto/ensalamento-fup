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
) -> bool:
    """
    Initialize page with authentication and configuration.

    Args:
        page_title: Streamlit page title (e.g., "Home - Ensalamento")
        page_icon: Streamlit page icon (e.g., "🏠")
        layout: Streamlit layout, defaults to "wide"
        key_suffix: Unique suffix for this page's auth keys (e.g., "home", "professores")

    Returns:
        bool: True if authentication succeeds, False otherwise (page should stop)

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
    # AUTHENTICATION CHECK
    # ============================================================================
    # Retrieve authenticator from session state (set by main.py)
    authenticator = st.session_state.get("authenticator")

    if authenticator is None:
        st.warning("👈 Por favor, faça login na página inicial para acessar o sistema.")
        st.page_link("main.py", label="Voltar para o início ↩", icon="🏠")
        # navigate back to main page where login widget is located
        st.switch_page("main.py")
        return False

    # Generate unique keys for this page
    auth_key = f"authenticator-{key_suffix}"
    logout_key = f"logout-{key_suffix}"

    # Call login with unrendered location to maintain session (required for page refresh fix)
    try:
        authenticator.login(location="unrendered", key=auth_key)
    except Exception as exc:
        st.error(f"❌ Erro de autenticação: {exc}")
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
    elif auth_status is False:
        st.error("❌ Acesso negado.")
        return False
    else:
        # Not authenticated - redirect to main page
        st.warning("👈 Por favor, faça login na página inicial para acessar o sistema.")
        st.page_link("main.py", label="Voltar para o início ↩", icon="🏠")
        # navigate back to main page where login widget is located
        st.switch_page("main.py")
        return False

    # ============================================================================
    # PAGE CONFIG
    # ============================================================================

    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout=layout,
    )

    # Authentication successful
    return True
