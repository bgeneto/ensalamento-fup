"""
Reusable Page footer UI element
"""

import streamlit as st


@st.cache_data
def _get_footer_html() -> str:
    """Generate the footer HTML string (cached)."""
    from datetime import datetime
    from src.config.settings import settings

    year = datetime.now().year
    app_version = settings.APP_VERSION
    app_name = settings.APP_NAME

    return f"""
    <div style="text-align: center; color: #999; font-size: 0.85rem; padding: 0rem 0;">
        <p><strong>{app_name}</strong></p>
        <p>Versão {app_version} • Beta 1</p>
        <p style="font-size: 0.75rem;">© 2025-{year} bgeneto • Faculdade UnB Planaltina</p>
    </div>
    """


def show():
    """Render the standard footer for the application."""
    st.markdown("---")
    st.markdown(_get_footer_html(), unsafe_allow_html=True)
