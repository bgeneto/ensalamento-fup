"""Manual cookie management for SIGAA HTTP requests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable, List, Optional


@dataclass
class CookieEntry:
    """Representation of a single Set-Cookie entry."""

    name: str
    value: str
    domain: str
    path: Optional[str] = None
    expires_at: Optional[datetime] = None
    domain_flag: Optional[str] = None


class SigaaCookieJar:
    """Manual cookie jar modeled after the reference `sigaa-api` project."""

    def __init__(self) -> None:
        self._cookies: List[CookieEntry] = []

    def clear(self) -> None:
        self._cookies = []

    def cookie_names(self) -> list[str]:
        """Return the deduplicated list of stored cookie names."""
        seen: set[str] = set()
        names: list[str] = []
        for cookie in self._cookies:
            if cookie.name in seen:
                continue
            seen.add(cookie.name)
            names.append(cookie.name)
        return names

    def store_from_set_cookie_headers(
        self, domain: str, headers: Iterable[str]
    ) -> None:
        """Parse and store cookies from Set-Cookie headers."""
        for header in headers:
            parsed = self._parse_set_cookie(domain, header)
            if parsed is not None:
                self._cookies.insert(0, parsed)

    def get_cookie_header(self, domain: str, path: str) -> Optional[str]:
        """Return the Cookie header for a given request."""
        now = datetime.now(timezone.utc)
        valid = [
            cookie
            for cookie in self._cookies
            if self._matches_domain(cookie, domain)
            and self._matches_path(cookie, path)
            and (cookie.expires_at is None or cookie.expires_at >= now)
        ]
        if not valid:
            return None

        deduped: list[CookieEntry] = []
        seen: set[str] = set()
        for cookie in valid:
            if cookie.name in seen:
                continue
            seen.add(cookie.name)
            deduped.append(cookie)

        header = "; ".join(
            f"{cookie.name}={cookie.value}" for cookie in reversed(deduped)
        )
        return header or None

    def _parse_set_cookie(self, domain: str, header: str) -> Optional[CookieEntry]:
        parts = [part.strip() for part in header.split(";") if part.strip()]
        if not parts or "=" not in parts[0]:
            return None

        name, value = parts[0].split("=", 1)
        if not name:
            return None

        cookie = CookieEntry(name=name, value=value.strip('"'), domain=domain)
        max_age_found = False
        for flag in parts[1:]:
            lower_flag = flag.lower()
            if lower_flag.startswith("path="):
                cookie.path = flag[5:]
            elif lower_flag.startswith("domain="):
                cookie_domain = flag[7:].lstrip(".")
                if not ("." + domain).endswith("." + cookie_domain):
                    return None
                cookie.domain_flag = cookie_domain
            elif lower_flag.startswith("max-age="):
                max_age_found = True
                try:
                    seconds = int(flag[8:])
                except ValueError:
                    continue
                cookie.expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=seconds
                )
            elif not max_age_found and lower_flag.startswith("expires="):
                try:
                    expires = parsedate_to_datetime(flag[8:])
                except (TypeError, ValueError, IndexError):
                    continue
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                cookie.expires_at = expires.astimezone(timezone.utc)

        return cookie

    @staticmethod
    def _matches_domain(cookie: CookieEntry, domain: str) -> bool:
        expected_domain = cookie.domain_flag or cookie.domain
        return ("." + domain).endswith("." + expected_domain)

    @staticmethod
    def _matches_path(cookie: CookieEntry, path: str) -> bool:
        return not cookie.path or path.startswith(cookie.path)
