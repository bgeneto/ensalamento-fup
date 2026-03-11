"""SIGAA public scraping integration package."""

from .errors import SigaaHttpError, SigaaScrapingError, SigaaSemanticRejectionError
from .public_turmas_client import SigaaPublicTurmasClient

__all__ = [
    "SigaaHttpError",
    "SigaaScrapingError",
    "SigaaSemanticRejectionError",
    "SigaaPublicTurmasClient",
]
