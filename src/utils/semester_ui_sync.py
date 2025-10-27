"""
Semester UI Synchronization Utilities

Centralized utilities for managing global semester selection across all UI components.
Ensures synchronization between sidebar, main panel, and settings page semester selectors.

This module prevents the double initialization and race conditions that caused
the sidebar and main panel select boxes to become desynchronized.
"""

import streamlit as st
from typing import Dict, List, Tuple, Optional
from src.utils.cache_helpers import get_semester_options


def initialize_global_semester():
    """
    Initialize global semester session state (call once per session).

    This should be called before any UI components that need semester selection.
    Prevents duplicate initialization across components.

    Returns:
        int: The current or initialized global semester ID
    """
    semester_options = get_semester_options()

    current_semester_id = st.session_state.get("global_semester_id")
    if current_semester_id is None or (
        semester_options
        and current_semester_id not in [sem_id for sem_id, _ in semester_options]
    ):
        # Auto-default to most recent semester
        current_semester_id = semester_options[0][0] if semester_options else None
        st.session_state.global_semester_id = current_semester_id

    return current_semester_id


def set_global_semester(semester_id: int):
    """
    Centralized function to set the global semester and trigger synchronization.

    This function should be used whenever changing the global semester from any UI component.
    It handles session state updates and triggers proper synchronization.

    Args:
        semester_id: The semester ID to set as global
    """
    st.session_state.global_semester_id = semester_id
    st.rerun()


def _on_semester_change_callback():
    """
    Internal callback for semester selectbox on_change event.

    This is called automatically by Streamlit when the selectbox value changes.
    It updates the global semester and triggers a rerun.
    """
    # Get the new value from the widget's session state key
    widget_key = st.session_state.get("_current_semester_widget_key")

    if widget_key and widget_key in st.session_state:
        new_semester_id = st.session_state[widget_key]

        # Only update if actually changed
        current_global = st.session_state.get("global_semester_id")

        if new_semester_id != current_global:
            # Update global semester
            st.session_state.global_semester_id = new_semester_id

            # Store feedback message if feedback key is set
            feedback_key = st.session_state.get("_semester_feedback_key")
            if feedback_key:
                from src.utils.ui_feedback import set_session_feedback
                from src.utils.cache_helpers import get_semester_options

                semester_options = get_semester_options()
                semester_dict = {
                    sem_id: sem_name for sem_id, sem_name in semester_options
                }
                semester_name = semester_dict.get(
                    new_semester_id, f"ID {new_semester_id}"
                )

                set_session_feedback(
                    feedback_key,
                    True,
                    f"Semestre alterado para: {semester_name}",
                )

            # CRITICAL: Explicitly trigger rerun to sync all UI components
            st.rerun()


def render_semester_selector(
    options: List[Tuple[int, str]],
    current_id: Optional[int],
    key: str,
    show_label: bool = True,
    feedback_key: Optional[str] = None,
    width: Optional[int] = None,
    use_sidebar: bool = False,
):
    """
    Reusable semester selector component with consistent behavior.

    Args:
        options: List of (semester_id, semester_name) tuples
        current_id: Currently selected semester ID
        key: Unique key for the selectbox widget
        show_label: Whether to show the label
        feedback_key: Optional feedback key for session feedback
        width: Optional width specification (ignored, for backwards compatibility)
        use_sidebar: Whether to render in sidebar or main content

    Returns:
        int: The selected semester ID (from session state after callback)
    """
    semester_options_dict = {sem_id: sem_name for sem_id, sem_name in options}

    # Store metadata for callback BEFORE rendering widget
    st.session_state._current_semester_widget_key = key
    st.session_state._semester_feedback_key = feedback_key

    # CRITICAL: Use the widget's value from session state if it exists (after callback runs)
    # Otherwise use current_id for initial render
    if key in st.session_state:
        # Widget has been rendered before, use its value
        actual_value = st.session_state[key]
    else:
        # First render, use current_id
        actual_value = current_id

    # Determine index for current selection
    if actual_value is not None and actual_value in semester_options_dict:
        index = list(semester_options_dict.keys()).index(actual_value)
    else:
        # Default to first option
        actual_value = options[0][0] if options else None
        index = 0 if options else 0

    # Choose whether to render to main content or sidebar
    target = st.sidebar if use_sidebar else st

    # Render the selectbox with on_change callback
    label = "📅 Seleção Global do Semestre:" if show_label else ""
    selected_semester = target.selectbox(
        label=label,
        options=list(semester_options_dict.keys()),
        format_func=lambda x: semester_options_dict.get(x, f"Semestre {x}"),
        index=index,
        key=key,
        label_visibility="visible" if show_label else "collapsed",
        on_change=_on_semester_change_callback,  # CRITICAL: Use callback for immediate detection
    )

    # Return the current value from session state (updated by callback if changed)
    return st.session_state.get("global_semester_id", selected_semester)
