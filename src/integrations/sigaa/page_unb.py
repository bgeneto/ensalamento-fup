"""UnB-specific helpers for SIGAA pages."""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin

from .form_parser import ParsedSigaaForm
from .page import SigaaPage


class UnBSigaaPage(SigaaPage):
    """SIGAA page with UnB-specific JSF helper parsing."""

    def parse_jsfcljs(self, javascript_code: str) -> ParsedSigaaForm:
        """Convert a `jsfcljs(...)` onclick expression to a submit payload."""
        if "getElementById" not in javascript_code:
            raise ValueError("SIGAA: Form not found in jsfcljs expression.")

        form_match = re.search(
            r"document\.getElementById\('([^']+)'\)", javascript_code
        )
        if not form_match:
            raise ValueError("SIGAA: Form id not found in jsfcljs expression.")

        form = self.soup.select_one(f"form#{form_match.group(1)}")
        if form is None:
            raise ValueError("SIGAA: Referenced form not found.")

        action = form.get("action")
        if not action:
            raise ValueError("SIGAA: Referenced form does not define action.")

        fields: dict[str, str] = {}
        for input_el in form.select("input[name]"):
            if input_el.get("type") == "submit":
                continue
            fields[input_el["name"]] = input_el.get("value", "")

        payload_match = re.search(
            r"jsfcljs\s*\(\s*document\.getElementById\s*\(\s*'[^']+'\s*\)\s*,\s*({[^}]+})\s*,\s*'[^']*'\s*\)",
            javascript_code,
        )
        if not payload_match:
            raise ValueError("SIGAA: jsfcljs payload not found.")

        payload = json.loads(payload_match.group(1).replace("'", '"'))
        fields.update({str(key): str(value) for key, value in payload.items()})

        return ParsedSigaaForm(
            action_url=urljoin(self.url, action),
            fields=fields,
            submit_buttons={},
        )
