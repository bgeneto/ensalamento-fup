"""Low-level HTTP client for SIGAA."""

from __future__ import annotations

from typing import Optional
from urllib.parse import quote, urljoin

from .http_session import SigaaHttpSession
from .page import SigaaPage


class SigaaHttpClient:
    """GET/POST client with explicit cookies and manual redirects."""

    def __init__(self, session: SigaaHttpSession) -> None:
        self.session = session

    def get(self, path_or_url: str) -> SigaaPage:
        return self._request("GET", path_or_url)

    def post(self, path_or_url: str, post_values: dict[str, str]) -> SigaaPage:
        body = self.encode_form_body(post_values)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        return self._request("POST", path_or_url, body=body, headers=headers)

    def follow_all_redirects(self, page: SigaaPage) -> SigaaPage:
        redirect_history = list(page.redirect_history)
        current_page = page

        while current_page.status_code in {301, 302, 303, 307, 308}:
            location = current_page.response_headers.get("Location")
            if not location:
                break

            next_url = urljoin(current_page.url, location)
            redirect_history.append(
                {
                    "status_code": str(current_page.status_code),
                    "from": current_page.url,
                    "to": next_url,
                }
            )
            current_page = self._request(
                "GET",
                next_url,
                redirect_history=redirect_history,
            )

        return current_page

    def encode_form_body(self, post_values: dict[str, str]) -> str:
        return "&".join(
            f"{self._encode_rfc3986(key)}={self._encode_rfc3986(value)}"
            for key, value in post_values.items()
        )

    def _request(
        self,
        method: str,
        path_or_url: str,
        *,
        body: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        redirect_history: Optional[list[dict[str, str]]] = None,
    ) -> SigaaPage:
        url = urljoin(self.session.base_url + "/", path_or_url)
        request_headers = self.session.apply_request_headers(url, headers)
        response = self.session.transport.request(
            method=method,
            url=url,
            headers=request_headers,
            data=body,
            allow_redirects=False,
            timeout=self.session.timeout,
        )
        return self.session.process_response(
            url,
            response,
            request_method=method,
            request_headers=request_headers,
            request_body=body,
            redirect_history=redirect_history,
        )

    @staticmethod
    def _encode_rfc3986(value: str) -> str:
        return quote(str(value), safe="-_.~")
