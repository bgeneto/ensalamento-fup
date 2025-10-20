"""Reusable helpers for Streamlit feedback messages with toast + TTL support."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import streamlit as st

DEFAULT_TTL_SECONDS = 6


def set_session_feedback(
    state_key: str,
    success: bool,
    message: str,
    ttl: int = DEFAULT_TTL_SECONDS,
    **extra: Any,
) -> Dict[str, Any]:
    """Store standardized feedback payload in Streamlit session state."""
    payload: Dict[str, Any] = {
        "success": success,
        "message": message,
        "timestamp": time.time(),
        "ttl": ttl,
        "displayed": False,
    }
    payload.update(extra)
    st.session_state[state_key] = payload
    return payload


def display_session_feedback(
    state_key: str,
    *,
    success_icon: str = "✅",
    error_icon: str = "❌",
) -> Optional[Dict[str, Any]]:
    """Render toast feedback with automatic TTL cleanup."""
    result = st.session_state.get(state_key)

    if not result:
        return None

    ttl = result.get("ttl", DEFAULT_TTL_SECONDS)
    timestamp = result.get("timestamp")

    if timestamp and (time.time() - timestamp) > ttl:
        st.session_state.pop(state_key, None)
        return None

    message = result.get("message")
    if not message:
        return result

    icon = success_icon if result.get("success") else error_icon

    if not result.get("displayed"):
        st.toast(message, icon=icon)
        result["displayed"] = True
        st.session_state[state_key] = result

    return result


def clear_session_feedback(state_key: str) -> None:
    """Remove a feedback payload from session state if present."""
    st.session_state.pop(state_key, None)
