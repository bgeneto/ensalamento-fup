"""
Config/Settings Page

Comprehensive app settings configuration for semesters, scoring weights, etc.
"""

import streamlit as st

# Import the auth and setup module
from pages.components.auth import initialize_page
from pages.components.config.tab_semester import render_semester_tab
from pages.components.config.tab_scoring import render_scoring_tab
from pages.components.ui import page_footer

# Initialize page with authentication and configuration
if not initialize_page(
    page_title="Configurações - Ensalamento",
    page_icon="⚙️",
    layout="centered",
    key_suffix="config",
):
    st.stop()

# ============================================================================
# PAGE HEADER
# ============================================================================

st.title("⚙️ Configurações do Sistema")
st.markdown(
    "Configure as definições globais do sistema, como semestres, pesos de pontuação e preferências."
)

# ============================================================================
# TABS STRUCTURE
# ============================================================================

tab1, tab2 = st.tabs(["📝 Semestres", "🎯 Pontuação"])

# =============================================================================
# TAB 1: SEMESTER MANAGEMENT
# =============================================================================

with tab1:
    render_semester_tab()

# =============================================================================
# TAB 2: SCORING CONFIGURATION
# =============================================================================

with tab2:
    render_scoring_tab()

# ============================================================================
# OTHER SETTINGS SECTIONS (to be added later)
# ============================================================================

# Page Footer
page_footer.show()
