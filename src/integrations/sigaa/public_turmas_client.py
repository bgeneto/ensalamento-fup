"""High-level SIGAA public turmas scraper for UnB."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from .cookies import SigaaCookieJar
from .errors import SigaaScrapingError, SigaaSemanticRejectionError
from .form_parser import HtmlFormParser
from .http_client import SigaaHttpClient
from .http_session import SigaaHttpSession


@dataclass
class FetchAttempt:
    """Collects diagnostics for one HTTP attempt."""

    attempt_url: str
    parsed_action: Optional[str] = None
    submit_field: Optional[str] = None
    view_state: Optional[str] = None
    cookie_names: list[str] | None = None
    redirect_chain: list[dict[str, str]] | None = None
    final_url: Optional[str] = None
    has_form: bool = False
    has_result_table: bool = False
    fallback_reason: Optional[str] = None
    error: Optional[str] = None

    def to_probe(self) -> Dict[str, Any]:
        return {
            "strategy": "HTTP",
            "attempt_url": self.attempt_url,
            "parsed_action": self.parsed_action,
            "submit_field": self.submit_field,
            "view_state": self.view_state,
            "cookie_names": self.cookie_names or [],
            "redirect_chain": self.redirect_chain or [],
            "final_url": self.final_url,
            "has_form": self.has_form,
            "has_result_table": self.has_result_table,
            "fallback_reason": self.fallback_reason,
            "error": self.error,
        }


class SigaaPublicTurmasClient:
    """HTTP-first scraper for the public UnB SIGAA turmas page."""

    ENTRY_URLS = (
        "https://sigaa.unb.br/sigaa/public/turmas/listar.jsf",
        "https://sigaa.unb.br/sigaa/public/turmas/listar.jsf?aba=p-ensino",
    )

    def __init__(
        self,
        *,
        http_client: Optional[SigaaHttpClient] = None,
        form_parser: Optional[HtmlFormParser] = None,
    ) -> None:
        if http_client is None:
            session = SigaaHttpSession(
                "https://sigaa.unb.br",
                cookie_jar=SigaaCookieJar(),
            )
            http_client = SigaaHttpClient(session)
        self.http_client = http_client
        self.form_parser = form_parser or HtmlFormParser()

    def fetch_turmas_html(
        self,
        year: int,
        period: int,
        depto_id: str = "666",
        nivel: str = "G",
    ) -> Tuple[str, Dict[str, Any]]:
        """Fetch the raw HTML of the public SIGAA turmas table."""
        with self.http_client.session.request_lock:
            http_error: Optional[SigaaScrapingError] = None
            for entry_url in self.ENTRY_URLS:
                try:
                    return self._fetch_with_http(
                        entry_url=entry_url,
                        year=year,
                        period=period,
                        depto_id=depto_id,
                        nivel=nivel,
                    )
                except SigaaScrapingError as exc:
                    http_error = exc

            if http_error is not None:
                raise http_error
            raise SigaaScrapingError("Falha desconhecida ao consultar turmas no SIGAA.")

    def _fetch_with_http(
        self,
        *,
        entry_url: str,
        year: int,
        period: int,
        depto_id: str,
        nivel: str,
    ) -> Tuple[str, Dict[str, Any]]:
        attempt = FetchAttempt(attempt_url=entry_url)
        try:
            initial_page = self.http_client.get(entry_url)
            attempt.has_form = bool(initial_page.soup.select_one("form#formTurma"))
            attempt.view_state = initial_page.view_state
            attempt.cookie_names = self.http_client.session.cookie_jar.cookie_names()

            form = self.form_parser.parse_form(initial_page, "form#formTurma")
            attempt.parsed_action = form.action_url

            submit_field = self._select_submit_field(form.submit_buttons)
            if submit_field is None:
                raise SigaaScrapingError(
                    "Botão de busca do formulário público do SIGAA não foi encontrado.",
                    probe=attempt.to_probe(),
                )

            attempt.submit_field = submit_field

            post_values = dict(form.fields)
            post_values["formTurma:inputNivel"] = str(nivel)
            post_values["formTurma:inputDepto"] = str(depto_id)
            post_values["formTurma:inputAno"] = str(year)
            post_values["formTurma:inputPeriodo"] = str(period)
            post_values[submit_field] = form.submit_buttons[submit_field]

            response_page = self.http_client.post(form.action_url, post_values)
            final_page = self.http_client.follow_all_redirects(response_page)

            attempt.redirect_chain = final_page.redirect_history
            attempt.final_url = final_page.url
            attempt.has_form = bool(final_page.soup.select_one("form#formTurma"))
            attempt.has_result_table = self._has_results_table(final_page.body)

            if self._is_semantic_rejection(final_page):
                raise SigaaSemanticRejectionError(
                    "O fluxo HTTP do SIGAA terminou em uma página sem a tabela pública de turmas.",
                    probe=attempt.to_probe(),
                )

            return final_page.body, attempt.to_probe()
        except SigaaScrapingError:
            raise
        except Exception as exc:  # pragma: no cover - defensive path
            attempt.error = str(exc)
            raise SigaaScrapingError(
                f"Falha ao executar o scrape HTTP do SIGAA: {exc}",
                probe=attempt.to_probe(),
            ) from exc

    @staticmethod
    def _select_submit_field(submit_buttons: dict[str, str]) -> Optional[str]:
        for name, value in submit_buttons.items():
            if str(value).strip().lower() == "buscar":
                return name
        return next(iter(submit_buttons.keys()), None)

    @staticmethod
    def _has_results_table(html: str) -> bool:
        return (
            "#turmasAbertas" in html
            and 'table class="listagem"' in html
            or ('table class="listagem"' in html and "agrupador" in html)
        )

    @staticmethod
    def _is_semantic_rejection(page: Any) -> bool:
        parsed = urlparse(page.url)
        path = parsed.path or ""
        if path.endswith("/sigaa/public/home.jsf"):
            return True
        if path.endswith(
            "/sigaa/public/"
        ) and not SigaaPublicTurmasClient._has_results_table(page.body):
            return True
        return not SigaaPublicTurmasClient._has_results_table(page.body)
