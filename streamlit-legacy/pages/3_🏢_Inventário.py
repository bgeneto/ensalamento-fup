"""
Inventory Management Page - Room/Building/Campus CRUD

Comprehensive inventory management for physical space allocation infrastructure.
Includes CRUD operations for campuses, buildings, and rooms.

Refactored with modular components for better maintainability.
"""

# Import the auth and setup module
from pages.components.auth import initialize_page
from pages.components.inventory.tab_campus import render_campus_tab
from pages.components.inventory.tab_buildings import render_buildings_tab
from pages.components.inventory.tab_rooms import render_rooms_tab
from pages.components.inventory.tab_associations import render_associations_tab
from pages.components.ui import page_footer

# Initialize page with authentication and configuration
if not initialize_page(
    page_title="Inventário - Ensalamento",
    page_icon="🏢",
    layout="wide",
    key_suffix="inventario",
):
    st.stop()

# ============================================================================
# PAGE HEADER
# ============================================================================
import streamlit as st

st.title("🏢 Gerenciamento de Inventário")
st.markdown(
    "Gerencie campi, prédios, salas e características da infraestrutura física."
)

# ============================================================================
# TABS STRUCTURE
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs(
    ["🚪 Salas", "🔗 Assoc. Características", "🏢 Prédios", "🏫 Campi"]
)

# =============================================================================
# TAB 1: CAMPUS MANAGEMENT
# =============================================================================

with tab1:
    render_rooms_tab()

# =============================================================================
# TAB 2: BUILDING MANAGEMENT
# =============================================================================

with tab2:
    render_associations_tab()

# =============================================================================
# TAB 3: ROOM MANAGEMENT
# =============================================================================

with tab3:
    render_buildings_tab()

# =============================================================================
# TAB 4: ROOM CHARACTERISTICS ASSOCIATIONS
# =============================================================================

with tab4:
    render_campus_tab()

# Page Footer
page_footer.show()
