"""Exceptions used by the SIGAA integration layer."""

from __future__ import annotations

from typing import Any, Dict, Optional


class SigaaHttpError(RuntimeError):
    """Low-level HTTP error while talking to SIGAA."""


class SigaaScrapingError(RuntimeError):
    """High-level scraping or parsing error."""

    def __init__(
        self,
        message: str,
        *,
        probe: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.probe = probe or {}


class SigaaSemanticRejectionError(SigaaScrapingError):
    """SIGAA responded, but the response is semantically unusable."""
