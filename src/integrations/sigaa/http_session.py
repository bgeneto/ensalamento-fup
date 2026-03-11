"""HTTP session helpers for SIGAA requests."""

from __future__ import annotations

import threading
from typing import Optional
from urllib.parse import urlparse

import requests

from .cookies import SigaaCookieJar
from .page import SigaaPage

_LOCK_REGISTRY: dict[str, threading.RLock] = {}
_LOCK_REGISTRY_GUARD = threading.Lock()


def _get_request_lock(hostname: str) -> threading.RLock:
    with _LOCK_REGISTRY_GUARD:
        if hostname not in _LOCK_REGISTRY:
            _LOCK_REGISTRY[hostname] = threading.RLock()
        return _LOCK_REGISTRY[hostname]


class SigaaHttpSession:
    """Orchestrates headers, cookies and response processing."""

    def __init__(
        self,
        base_url: str,
        cookie_jar: Optional[SigaaCookieJar] = None,
        *,
        timeout: int = 20,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.cookie_jar = cookie_jar or SigaaCookieJar()
        self.timeout = timeout
        self.transport = requests.Session()
        self.request_lock = _get_request_lock(urlparse(self.base_url).hostname or "")

    def apply_request_headers(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, str]:
        """Return request headers with explicit cookies applied."""
        parsed = urlparse(url)
        request_headers = {
            "User-Agent": "SIGAA-HTTP/1.0 (+https://github.com/GeovaneSchmitz/sigaa-api)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Cache-Control": "max-age=0",
        }
        if headers:
            request_headers.update(headers)

        cookie_header = self.cookie_jar.get_cookie_header(
            parsed.hostname or "",
            parsed.path or "/",
        )
        if cookie_header:
            request_headers["Cookie"] = cookie_header

        return request_headers

    def process_response(
        self,
        url: str,
        response: requests.Response,
        *,
        request_method: str,
        request_headers: dict[str, str],
        request_body: Optional[str],
        redirect_history: Optional[list[dict[str, str]]] = None,
    ) -> SigaaPage:
        """Store cookies and return a normalized page object."""
        raw_headers = getattr(response.raw, "headers", None)
        set_cookie_headers: list[str] = []
        if raw_headers is not None:
            if hasattr(raw_headers, "getlist"):
                set_cookie_headers = list(raw_headers.getlist("Set-Cookie"))
            elif hasattr(raw_headers, "get_all"):
                set_cookie_headers = list(raw_headers.get_all("Set-Cookie"))
        if not set_cookie_headers and response.headers.get("Set-Cookie"):
            set_cookie_headers = [response.headers["Set-Cookie"]]

        if set_cookie_headers:
            self.cookie_jar.store_from_set_cookie_headers(
                urlparse(url).hostname or "",
                set_cookie_headers,
            )

        return SigaaPage(
            url=response.url,
            request_method=request_method,
            request_headers=request_headers,
            request_body=request_body,
            response_headers=dict(response.headers),
            status_code=response.status_code,
            body=response.text,
            redirect_history=redirect_history or [],
        )
