"""
Configuration file for Sistema de Ensalamento FUP/UnB
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.absolute()
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "ensalamento.db"

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")

# Authentication Configuration
AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "ensalamento_session")
AUTH_COOKIE_EXPIRY_DAYS = int(os.getenv("AUTH_COOKIE_EXPIRY_DAYS", "30"))

# Streamlit Configuration
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))
STREAMLIT_HOST = os.getenv("STREAMLIT_HOST", "0.0.0.0")

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.unb.br/ensalamento")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))

# Application Configuration
APP_NAME = "Sistema de Ensalamento FUP/UnB"
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Admin Configuration
DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")

# Timezone
TIMEZONE = "America/Sao_Paulo"

# Pagination
DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "50"))

# File Upload Limits
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))

# Email Configuration (for future notifications)
SMTP_SERVER = os.getenv("SMTP_SERVER", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)

# Sigaa Configuration
SIGAA_TIME_BLOCKS = {
    "M": ["M1", "M2", "M3", "M4", "M5", "M6"],
    "T": ["T1", "T2", "T3", "T4", "T5", "T6"],
    "N": ["N1", "N2", "N3", "N4", "N5", "N6"],
}

SIGAA_DAYS_MAPPING = {
    1: "DOM",
    2: "SEG",
    3: "TER",
    4: "QUA",
    5: "QUI",
    6: "SEX",
    7: "SAB",
}

# Room Capacity Tiers
CAPACITY_TIERS = {"pequena": 30, "media": 60, "grande": 120, "auditório": 200}

# Allocation Rules Priority
RULE_PRIORITIES = {"highest": 1, "high": 2, "medium": 3, "low": 4, "lowest": 5}
