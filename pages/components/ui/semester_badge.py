"""
Reusable Semester Selector UI element for sidebar display
"""

import streamlit as st


def show():
    """Render the semester selector in the sidebar."""

    # Get available semesters
    from src.utils.cache_helpers import get_semester_options
    from src.utils.semester_ui_sync import (
        initialize_global_semester,
        render_semester_selector,
    )

    semester_options = get_semester_options()

    if not semester_options:
        st.sidebar.error("❌ Nenhum semestre encontrado. Importe dados primeiro.")
        return

    # Initialize global semester (prevents duplicate initialization across components)
    current_semester_id = initialize_global_semester()

    # Render centralized semester selector in sidebar
    render_semester_selector(
        semester_options,
        current_semester_id,
        key="sidebar_global_semester_selector",
        show_label=True,
        feedback_key=None,  # Use built-in success message
        use_sidebar=True,  # Render to sidebar
        width="stretch",
    )
