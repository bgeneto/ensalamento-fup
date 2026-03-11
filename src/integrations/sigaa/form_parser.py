"""HTML form parsing helpers for SIGAA pages."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

from .page import SigaaPage


@dataclass
class ParsedSigaaForm:
    """Normalized HTML form extracted from a SIGAA page."""

    action_url: str
    fields: dict[str, str]
    submit_buttons: dict[str, str]


class HtmlFormParser:
    """Parse HTML forms into transport-ready structures."""

    def parse_form(self, page: SigaaPage, selector: str) -> ParsedSigaaForm:
        form = page.soup.select_one(selector)
        if form is None:
            raise ValueError(f"SIGAA: Form `{selector}` not found.")

        action_url = urljoin(page.url, form.get("action") or page.url)
        fields: dict[str, str] = {}
        submit_buttons: dict[str, str] = {}

        for input_el in form.select("input[name]"):
            name = input_el.get("name")
            if not name:
                continue
            input_type = (input_el.get("type") or "text").lower()
            value = input_el.get("value", "")
            if input_type in {"submit", "button", "reset", "image", "file"}:
                submit_buttons[name] = value
                continue
            if input_type in {"checkbox", "radio"} and not input_el.has_attr("checked"):
                continue
            fields[name] = value

        for textarea in form.select("textarea[name]"):
            name = textarea.get("name")
            if name:
                fields[name] = textarea.text or ""

        for select in form.select("select[name]"):
            name = select.get("name")
            if not name:
                continue
            selected = select.select_one("option[selected]")
            if selected is None:
                selected = select.select_one("option")
            fields[name] = selected.get("value", "") if selected is not None else ""

        return ParsedSigaaForm(
            action_url=action_url,
            fields=fields,
            submit_buttons=submit_buttons,
        )
