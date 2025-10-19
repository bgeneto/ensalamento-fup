"""
Application settings and configuration management.

Loads configuration from .env file and provides access to all settings.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        """Initialize settings from .env file."""
        # Load .env file
        env_file = Path(__file__).parent.parent.parent / ".env"
        load_dotenv(env_file)

        # Database Configuration
        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL", "sqlite:///./data/ensalamento.db"
        )

        # Ensure data directory exists
        db_path = self.DATABASE_URL.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # API Configuration
        self.SISTEMA_OFERTA_API_URL: Optional[str] = os.getenv("SISTEMA_OFERTA_API_URL")
        self.SISTEMA_OFERTA_API_KEY: Optional[str] = os.getenv("SISTEMA_OFERTA_API_KEY")

        # Email Configuration (Brevo)
        self.BREVO_API_KEY: Optional[str] = os.getenv("BREVO_API_KEY")
        self.BREVO_FROM_EMAIL: Optional[str] = os.getenv("BREVO_FROM_EMAIL")

        # Streamlit Configuration
        self.STREAMLIT_SERVER_PORT: int = int(os.getenv("STREAMLIT_SERVER_PORT", 8501))
        self.STREAMLIT_SERVER_ADDRESS: str = os.getenv(
            "STREAMLIT_SERVER_ADDRESS", "0.0.0.0"
        )
        self.STREAMLIT_LOGGER_LEVEL: str = os.getenv("STREAMLIT_LOGGER_LEVEL", "info")

        # Security
        self.SECRET_KEY: str = os.getenv(
            "SECRET_KEY", "your-secret-key-change-in-production"
        )

        # Project Paths
        self.PROJECT_ROOT = Path(__file__).parent.parent.parent
        self.DATA_DIR = self.PROJECT_ROOT / "data"
        self.LOGS_DIR = self.PROJECT_ROOT / "logs"

        # Create necessary directories
        self.DATA_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)

        # Application Settings
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    def __repr__(self) -> str:
        """String representation of settings."""
        return f"<Settings: {self.ENVIRONMENT} - DB: {self.DATABASE_URL}>"


# Global settings instance
settings = Settings()
