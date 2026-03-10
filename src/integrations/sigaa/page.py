"""Page abstraction for SIGAA HTML responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Mapping, Optional

from bs4 import BeautifulSoup


@dataclass
class SigaaPage:
    """Representation of a single HTML response from SIGAA."""

    url: str
    request_method: str
    request_headers: dict[str, str]
    request_body: Optional[str]
    response_headers: Mapping[str, str]
    status_code: int
    body: str
    redirect_history: list[dict[str, Any]] = field(default_factory=list)

    @cached_property
    def soup(self) -> BeautifulSoup:
        return BeautifulSoup(self.body, "lxml")

    @cached_property
    def view_state(self) -> Optional[str]:
        element = self.soup.select_one("input[name='javax.faces.ViewState']")
        if element is None:
            return None
        return element.get("value")
