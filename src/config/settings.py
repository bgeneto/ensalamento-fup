"""
Application settings and configuration management.

Loads configuration from .env file and provides access to all settings.
"""

import logging
import logging.handlers
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

        # Application Configuration
        self.APP_NAME: str = os.getenv("APP_NAME", "Sistema de Ensalamento FUP/UnB")
        self.APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
        self.BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8501")

        # Database Configuration
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ensalamento.db")

        # Ensure data directory exists
        db_path = self.DATABASE_URL.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Encryption
        self.ENCRYPTION_KEY: Optional[str] = os.getenv("ENCRYPTION_KEY")

        # API Configuration (Sistema de Oferta)
        self.OFERTA_API_BASE_URL: Optional[str] = os.getenv("OFERTA_API_BASE_URL")
        self.OFERTA_API_TIMEOUT: int = int(os.getenv("OFERTA_API_TIMEOUT", "10"))
        # Legacy support for old variable names
        self.SISTEMA_OFERTA_API_URL: Optional[str] = os.getenv(
            "SISTEMA_OFERTA_API_URL", self.OFERTA_API_BASE_URL
        )
        self.SISTEMA_OFERTA_API_KEY: Optional[str] = os.getenv("SISTEMA_OFERTA_API_KEY")

        # Email Configuration (Brevo)
        self.BREVO_API_KEY: Optional[str] = os.getenv("BREVO_API_KEY")
        self.BREVO_SENDER_EMAIL: Optional[str] = os.getenv("BREVO_SENDER_EMAIL")
        self.BREVO_SENDER_NAME: Optional[str] = os.getenv(
            "BREVO_SENDER_NAME", "Sistema de Ensalamento FUP/UnB"
        )
        # Legacy support
        self.BREVO_FROM_EMAIL: Optional[str] = os.getenv(
            "BREVO_FROM_EMAIL", self.BREVO_SENDER_EMAIL
        )

        # Initial Superadmin Configuration (for first-time setup)
        self.INITIAL_SUPERADMIN_EMAIL: Optional[str] = os.getenv(
            "INITIAL_SUPERADMIN_EMAIL"
        )
        self.INITIAL_SUPERADMIN_PASSWORD: Optional[str] = os.getenv(
            "INITIAL_SUPERADMIN_PASSWORD"
        )
        self.INITIAL_SUPERADMIN_NAME: Optional[str] = os.getenv(
            "INITIAL_SUPERADMIN_NAME", "Superadmin"
        )

        # Streamlit Configuration
        self.STREAMLIT_SERVER_PORT: int = int(
            os.getenv("STREAMLIT_SERVER_PORT", "8501")
        )
        self.STREAMLIT_SERVER_ADDRESS: str = os.getenv(
            "STREAMLIT_SERVER_ADDRESS", "0.0.0.0"
        )
        self.STREAMLIT_SERVER_HEADLESS: bool = (
            os.getenv("STREAMLIT_SERVER_HEADLESS", "true").lower() == "true"
        )
        self.STREAMLIT_SERVER_ENABLE_CORS: bool = (
            os.getenv("STREAMLIT_SERVER_ENABLE_CORS", "false").lower() == "true"
        )
        self.STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION: bool = (
            os.getenv("STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION", "false").lower()
            == "true"
        )
        self.STREAMLIT_BROWSER_GATHER_USAGE_STATS: bool = (
            os.getenv("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false").lower() == "true"
        )
        self.STREAMLIT_LOGGER_LEVEL: str = os.getenv("STREAMLIT_LOGGER_LEVEL", "info")

        # Security
        self.SECRET_KEY: str = os.getenv(
            "SECRET_KEY", "your-secret-key-change-in-production"
        )

        # Project Paths
        self.PROJECT_ROOT = Path(__file__).parent.parent.parent
        self.LOGS_DIR = self.PROJECT_ROOT / "logs"

        # Create necessary directories
        self.LOGS_DIR.mkdir(exist_ok=True)

        # Application Settings
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

        # Docker Configuration
        self.HOST_UID: int = int(os.getenv("HOST_UID", "1000"))

        # Configure logging based on DEBUG setting
        self._configure_logging()

    def _configure_logging(self) -> None:
        """Configure logging based on DEBUG setting."""
        # Set log level
        log_level = logging.DEBUG if self.DEBUG else logging.INFO

        # Create logs directory if it doesn't exist
        self.LOGS_DIR.mkdir(exist_ok=True)

        # Get root logger
        root_logger = logging.getLogger()

        # Clear existing handlers
        root_logger.handlers.clear()

        # Set level
        root_logger.setLevel(log_level)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Create custom filter to exclude SQLAlchemy logs
        class SQLAlchemyFilter(logging.Filter):
            def filter(self, record):
                return not record.name.startswith("sqlalchemy")

        sqlalchemy_filter = SQLAlchemyFilter()

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(sqlalchemy_filter)
        root_logger.addHandler(console_handler)

        # File handler with rotation (rotate daily, keep 7 days)
        file_handler = logging.handlers.TimedRotatingFileHandler(
            self.LOGS_DIR / "app.log",
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sqlalchemy_filter)
        root_logger.addHandler(file_handler)

        # Disable SQLAlchemy engine logging completely
        logging.getLogger("sqlalchemy.engine").setLevel(logging.CRITICAL)
        logging.getLogger("sqlalchemy").setLevel(logging.CRITICAL)

        # Suppress noisy third-party loggers that can cause log file feedback loops
        logging.getLogger("watchdog.observers.inotify_buffer").setLevel(logging.WARNING)
        logging.getLogger("watchdog.observers").setLevel(logging.WARNING)
        logging.getLogger("watchdog").setLevel(logging.WARNING)

        # Suppress other potentially noisy loggers in development
        logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
        logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(
            logging.WARNING
        )
        logging.getLogger("streamlit.runtime.scriptrunner.script_run_context").setLevel(
            logging.WARNING
        )

    def __repr__(self) -> str:
        """String representation of settings."""
        return f"<Settings: {self.ENVIRONMENT} - DB: {self.DATABASE_URL}>"


# Global settings instance
settings = Settings()
