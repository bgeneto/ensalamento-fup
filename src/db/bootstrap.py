"""Database bootstrap helpers for application startup."""

import logging
import os
from threading import Lock

from src.db.migrations import init_db, run_sql_migrations

logger = logging.getLogger(__name__)

_BOOTSTRAP_LOCK = Lock()
_BOOTSTRAP_COMPLETED = False
_BOOTSTRAP_FLAG = "DB_BOOTSTRAPPED"
_SKIP_FLAG = "SKIP_DB_MIGRATIONS"


def ensure_database_ready() -> bool:
    """Create missing tables and apply pending SQL migrations once per process."""
    global _BOOTSTRAP_COMPLETED

    if os.getenv(_SKIP_FLAG, "0") == "1":
        _BOOTSTRAP_COMPLETED = True
        logger.info("Skipping database bootstrap because %s=1", _SKIP_FLAG)
        return False

    if _BOOTSTRAP_COMPLETED or os.getenv(_BOOTSTRAP_FLAG, "0") == "1":
        _BOOTSTRAP_COMPLETED = True
        return False

    with _BOOTSTRAP_LOCK:
        if _BOOTSTRAP_COMPLETED or os.getenv(_BOOTSTRAP_FLAG, "0") == "1":
            _BOOTSTRAP_COMPLETED = True
            return False

        logger.info("Ensuring database tables and SQL migrations are up to date")
        init_db()
        run_sql_migrations()
        _initialize_scoring_configuration()

        os.environ[_BOOTSTRAP_FLAG] = "1"
        _BOOTSTRAP_COMPLETED = True
        return True


def _reset_database_bootstrap_state() -> None:
    """Reset module bootstrap state for tests."""
    global _BOOTSTRAP_COMPLETED

    _BOOTSTRAP_COMPLETED = False
    os.environ.pop(_BOOTSTRAP_FLAG, None)


def _initialize_scoring_configuration() -> None:
    """Refresh runtime scoring configuration after DB bootstrap."""
    try:
        from src.config.scoring_config import reload_scoring_config

        reload_scoring_config()
    except Exception:
        logger.exception("Failed to initialize scoring configuration")
