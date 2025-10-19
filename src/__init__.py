"""
Sistema de Ensalamento FUP/UnB - Main Package
"""

__version__ = "0.1.0"
__author__ = "FUP/UnB"

from src.config.database import DatabaseSession, get_db_engine

__all__ = ["DatabaseSession", "get_db_engine"]
