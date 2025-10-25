"""
Reusable Semester Badge UI element for sidebar display
"""

import streamlit as st


@st.cache_data
def _get_semester_badge_html(semester_name: str) -> str:
    """Generate the semester badge HTML string (cached)."""
    return f"""
    <div style="background: linear-gradient(135deg, #c67b5c 0%, #a0563f 100%); color: white; padding: 0.5rem; border-radius: 0.375rem; text-align: center; margin: 0.5rem 0; font-size: 0.875rem; font-weight: 600;">
        📅 Semestre: {semester_name}
    </div>
    """


def show():
    """Render the current semester badge in the sidebar."""
    # Get current global semester
    global_semester_id = st.session_state.get("global_semester_id")

    if global_semester_id is None:
        # Initialize with most recent semester if not set
        from src.utils.cache_helpers import get_semester_options

        semester_options = get_semester_options()
        if semester_options:
            global_semester_id = semester_options[0][0]  # Most recent semester ID
            st.session_state.global_semester_id = global_semester_id

    # Get semester name for display
    if global_semester_id:
        from src.utils.cache_helpers import get_semester_options

        semester_options = get_semester_options()
        semester_name_map = {sem_id: sem_name for sem_id, sem_name in semester_options}

        semester_name = semester_name_map.get(
            global_semester_id, f"Semestre {global_semester_id}"
        )
        st.sidebar.markdown(
            _get_semester_badge_html(semester_name), unsafe_allow_html=True
        )
    else:
        # Fallback if no semesters available
        st.sidebar.markdown(
            _get_semester_badge_html("Nenhum Semestre"), unsafe_allow_html=True
        )
