"""
Room Reservations Page

Display and manage sporadic/recurrent room reservations.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Tuple
from st_aggrid import AgGrid, GridOptionsBuilder
from pages.components.auth import initialize_page

# Initialize page with authentication and configuration
if not initialize_page(
    page_title="Reservas - Ensalamento",
    page_icon="📅",
    layout="wide",
    key_suffix="reservas",
):
    st.stop()

# ============================================================================
# IMPORTS
# ============================================================================
