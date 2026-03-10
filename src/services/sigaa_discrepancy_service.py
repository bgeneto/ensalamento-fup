"""
Service for comparing local semester demands against the public SIGAA class listing.

This module is intentionally defensive:
- it drives the public JSF form with Selenium and Chromium headless;
- it preserves diagnostics when the browser flow is rejected by SIGAA;
- it compares schedules using normalized day/time pairs;
- it uses fuzzy-but-explainable professor matching based on token overlap and
  string similarity.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import os
import re
import shutil
import tempfile
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from bs4 import BeautifulSoup

from src.utils.sigaa_parser import SigaaScheduleParser

try:
    from selenium import webdriver
    from selenium.common.exceptions import (
        ElementClickInterceptedException,
        NoSuchElementException,
        TimeoutException as SeleniumTimeoutException,
        WebDriverException,
    )
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.select import Select
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:  # pragma: no cover - depends on runtime installation
    webdriver = None
    ChromeOptions = None
    ChromeService = None
    By = None
    EC = None
    Select = None
    WebDriverWait = None
    ElementClickInterceptedException = Exception
    NoSuchElementException = Exception
    SeleniumTimeoutException = TimeoutError
    WebDriverException = Exception


class SigaaScrapingError(RuntimeError):
    """Raised when the public SIGAA listing cannot be fetched reliably."""


@dataclass
class SigaaTurmaRecord:
    """Normalized representation of a SIGAA class row."""

    codigo_disciplina: str
    nome_disciplina: str
    turma: str
    professores: List[str]
    professores_raw: str
    horario_texto: str
    horario_componentes: List[Tuple[str, str]]
    vagas: Optional[int]

    @property
    def turma_normalizada(self) -> str:
        return SigaaDiscrepancyService.normalize_turma_value(self.turma)

    @property
    def schedule_key_set(self) -> set[str]:
        return {
            SigaaDiscrepancyService.format_schedule_component(day, time_range)
            for day, time_range in self.horario_componentes
        }

    @property
    def unique_key(self) -> Tuple[str, str, str]:
        return (
            self.codigo_disciplina,
            self.turma_normalizada,
            self.horario_texto,
        )


class SigaaDiscrepancyService:
    """Fetches public SIGAA turma data and compares it with local demands."""

    BASE_URL = os.getenv(
        "SIGAA_PUBLIC_TURMAS_URL",
        "https://sigaa.unb.br/sigaa/public/turmas/listar.jsf",
    )
    DEFAULT_NIVEL = os.getenv("SIGAA_PUBLIC_NIVEL", "G")
    DEFAULT_DEPTO_ID = os.getenv("SIGAA_PUBLIC_DEPTO_ID", "666")
    SELENIUM_TIMEOUT_SECONDS = int(
        os.getenv(
            "SIGAA_SELENIUM_TIMEOUT_SECONDS", os.getenv("SIGAA_PUBLIC_TIMEOUT", "45")
        )
    )
    SELENIUM_HEADLESS = os.getenv("SIGAA_SELENIUM_HEADLESS", "1") != "0"
    SELENIUM_HEADLESS_ARGUMENT = os.getenv(
        "SIGAA_SELENIUM_HEADLESS_ARGUMENT", "--headless"
    )
    SELENIUM_WINDOW_SIZE = os.getenv("SIGAA_SELENIUM_WINDOW_SIZE", "1600,2200")
    SELENIUM_CHROMIUM_BINARY = os.getenv("SIGAA_CHROMIUM_BINARY")
    SELENIUM_CHROMEDRIVER_PATH = os.getenv("SIGAA_CHROMEDRIVER_PATH")
    SELENIUM_SUBMIT_STRATEGIES: Sequence[str] = (
        "native_click",
        "javascript_click",
        "form_submit_with_button",
    )

    DAY_ORDER = {"SEG": 2, "TER": 3, "QUA": 4, "QUI": 5, "SEX": 6, "SAB": 7}
    SCHEDULE_PATTERN = re.compile(
        r"\b(SEG|TER|QUA|QUI|SEX|SAB)\s+(\d{2}:\d{2}\s*-\s*\d{2}:\d{2})\b",
        flags=re.IGNORECASE,
    )
    CODE_PATTERN = re.compile(r"\b([A-Z]{3,}\d{3,})\b")
    STOPWORDS = {"DA", "DE", "DI", "DO", "DOS", "DAS", "E"}

    def __init__(self) -> None:
        self.schedule_parser = SigaaScheduleParser()

    @staticmethod
    def _get_field(obj: Any, key: str, default: Any = None) -> Any:
        if hasattr(obj, key):
            return getattr(obj, key)
        if isinstance(obj, dict):
            return obj.get(key, default)
        return default

    @staticmethod
    def _clean_text(value: Any) -> str:
        if value is None:
            return ""
        return " ".join(str(value).replace("\xa0", " ").split())

    @staticmethod
    def _remove_accents(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))

    @classmethod
    def normalize_turma_value(cls, turma: Any) -> str:
        value = cls._clean_text(turma)
        if not value:
            return ""
        if value.isdigit():
            return str(int(value))
        return value.upper()

    @classmethod
    def _normalize_name(cls, name: str) -> str:
        value = cls._remove_accents(name or "").upper()
        value = re.sub(r"\([^)]*\)", " ", value)
        value = re.sub(r"[^A-Z0-9\s]", " ", value)
        return " ".join(value.split())

    @classmethod
    def _tokenize_name(cls, name: str) -> List[str]:
        normalized = cls._normalize_name(name)
        return [tok for tok in normalized.split() if tok and tok not in cls.STOPWORDS]

    @classmethod
    def _name_similarity(cls, left: str, right: str) -> float:
        norm_left = cls._normalize_name(left)
        norm_right = cls._normalize_name(right)

        if not norm_left or not norm_right:
            return 0.0
        if norm_left == norm_right:
            return 1.0

        left_token_list = cls._tokenize_name(left)
        right_token_list = cls._tokenize_name(right)
        left_tokens = set(left_token_list)
        right_tokens = set(right_token_list)

        if not left_tokens or not right_tokens:
            return SequenceMatcher(None, norm_left, norm_right).ratio()

        overlap = len(left_tokens & right_tokens)
        smaller_overlap = overlap / max(min(len(left_tokens), len(right_tokens)), 1)
        seq_ratio = SequenceMatcher(None, norm_left, norm_right).ratio()

        left_tail = left_token_list[-1] if left_token_list else ""
        right_tail = right_token_list[-1] if right_token_list else ""
        surname_bonus = 0.08 if left_tail and left_tail == right_tail else 0.0

        return min(1.0, (0.6 * smaller_overlap) + (0.4 * seq_ratio) + surname_bonus)

    @classmethod
    def _professor_list_similarity(
        cls, local_professors: Sequence[str], sigaa_professors: Sequence[str]
    ) -> float:
        if not local_professors or not sigaa_professors:
            return 0.0

        def directional_score(source: Sequence[str], target: Sequence[str]) -> float:
            scores = []
            for source_name in source:
                best = max(
                    cls._name_similarity(source_name, target_name)
                    for target_name in target
                )
                scores.append(best)
            return sum(scores) / len(scores)

        return min(
            directional_score(local_professors, sigaa_professors),
            directional_score(sigaa_professors, local_professors),
        )

    @classmethod
    def _extract_professor_names_from_sigaa(cls, raw_text: str) -> List[str]:
        lines = [
            cls._clean_text(line)
            for line in (raw_text or "").replace("\r", "\n").split("\n")
            if cls._clean_text(line)
        ]

        names: List[str] = []
        buffer: List[str] = []

        for line in lines:
            has_workload = bool(re.search(r"\(\d+h\)", line, flags=re.IGNORECASE))
            line_without_workload = re.sub(
                r"\(\d+h\)", "", line, flags=re.IGNORECASE
            ).strip()

            if line_without_workload:
                buffer.append(line_without_workload)

            if has_workload and buffer:
                names.append(" ".join(buffer))
                buffer = []

        if buffer:
            names.append(" ".join(buffer))

        if names:
            return names

        fallback = cls._clean_text(raw_text)
        return [fallback] if fallback else []

    @classmethod
    def _split_local_professors(cls, raw_text: str) -> List[str]:
        return [
            cls._clean_text(name)
            for name in str(raw_text or "").split(",")
            if cls._clean_text(name)
        ]

    @classmethod
    def _parse_schedule_components(cls, horario_texto: str) -> List[Tuple[str, str]]:
        components = []
        for day_name, time_range in cls.SCHEDULE_PATTERN.findall(horario_texto or ""):
            normalized_day = day_name.upper()
            normalized_range = time_range.replace(" ", "")
            components.append((normalized_day, normalized_range))

        seen = set()
        deduplicated = []
        for component in components:
            if component in seen:
                continue
            seen.add(component)
            deduplicated.append(component)

        return sorted(
            deduplicated,
            key=lambda item: (cls.DAY_ORDER.get(item[0], 99), item[1]),
        )

    @staticmethod
    def format_schedule_component(day_name: str, time_range: str) -> str:
        return f"{day_name} {time_range}"

    def _build_local_schedule_components(
        self, horario_sigaa_bruto: str
    ) -> List[Tuple[str, str]]:
        groups = self.schedule_parser.get_block_groups_with_names(
            horario_sigaa_bruto or ""
        )
        components = []
        for group in groups:
            day_name = self._clean_text(group.get("day_name"))
            time_range = self.schedule_parser.get_time_range_for_blocks(
                group.get("blocks", [])
            )
            if day_name and time_range:
                components.append((day_name, time_range))

        return sorted(
            components,
            key=lambda item: (self.DAY_ORDER.get(item[0], 99), item[1]),
        )

    @classmethod
    def _format_schedule_list(cls, components: Sequence[Tuple[str, str]]) -> str:
        return " | ".join(
            cls.format_schedule_component(day, time_range)
            for day, time_range in components
        )

    @staticmethod
    def _extract_int(value: str) -> Optional[int]:
        digits = re.sub(r"\D", "", value or "")
        return int(digits) if digits else None

    @classmethod
    def semester_name_to_year_period(cls, semester_name: str) -> Tuple[int, int]:
        cleaned = cls._clean_text(semester_name)
        match = re.fullmatch(r"(\d{4})[-.](\d+)", cleaned)
        if not match:
            raise ValueError(
                f"Semestre '{semester_name}' inválido para consulta no SIGAA. Use o formato AAAA-N."
            )

        year = int(match.group(1))
        period = int(match.group(2))
        return year, period

    @staticmethod
    def _http_headers() -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def _candidate_page_urls(self) -> List[str]:
        return [
            self.BASE_URL,
            f"{self.BASE_URL}?aba=p-ensino",
        ]

    def _response_contains_results_table(self, html: str) -> bool:
        soup = BeautifulSoup(html, "lxml")
        return bool(
            soup.select_one("#turmasAbertas table.listagem")
            or soup.select_one("table.listagem tr.agrupador")
        )

    @staticmethod
    def _resolve_executable(
        configured_path: str | None, candidates: Sequence[str]
    ) -> Optional[str]:
        if configured_path:
            return shutil.which(configured_path) or (
                configured_path if os.path.exists(configured_path) else None
            )

        for candidate in candidates:
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
            if os.path.exists(candidate):
                return candidate

        return None

    @classmethod
    def _build_selenium_options(cls) -> Any:
        if ChromeOptions is None:
            raise SigaaScrapingError("Selenium não está instalado no ambiente.")

        options = ChromeOptions()
        if cls.SELENIUM_HEADLESS:
            options.add_argument(cls.SELENIUM_HEADLESS_ARGUMENT)
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=" + cls.SELENIUM_WINDOW_SIZE)
        options.add_argument("--lang=pt-BR")
        options.add_argument("--disable-features=Translate")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-extensions")
        options.add_argument("--remote-debugging-pipe")
        options.add_argument("--disable-crash-reporter")
        options.add_argument("--disable-breakpad")

        binary_location = cls._resolve_executable(
            cls.SELENIUM_CHROMIUM_BINARY,
            (
                "chromium",
                "chromium-browser",
                "google-chrome",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/usr/bin/google-chrome",
            ),
        )
        if binary_location:
            options.binary_location = binary_location

        return options

    @classmethod
    def _build_selenium_service(cls, log_path: str | None = None) -> Any:
        if ChromeService is None:
            raise SigaaScrapingError("Selenium não está instalado no ambiente.")

        driver_path = cls._resolve_executable(
            cls.SELENIUM_CHROMEDRIVER_PATH,
            (
                "chromedriver",
                "/usr/bin/chromedriver",
                "/usr/lib/chromium/chromedriver",
            ),
        )
        if driver_path:
            return ChromeService(
                executable_path=driver_path,
                service_args=["--verbose"],
                log_output=log_path,
            )
        return ChromeService(service_args=["--verbose"], log_output=log_path)

    @staticmethod
    def _safe_read_text(path: str | None, max_chars: int = 6000) -> str:
        if not path or not os.path.exists(path):
            return ""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            return ""
        if len(content) <= max_chars:
            return content
        return content[-max_chars:]

    def _fill_sigaa_form(
        self,
        driver: Any,
        year: int,
        period: int,
        depto_value: str,
        nivel_value: str,
    ) -> None:
        if WebDriverWait is None or By is None or Select is None or EC is None:
            raise SigaaScrapingError("Selenium não está instalado no ambiente.")

        wait = WebDriverWait(driver, self.SELENIUM_TIMEOUT_SECONDS)
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'form#formTurma, form[name="formTurma"]')
            )
        )

        Select(driver.find_element(By.NAME, "formTurma:inputNivel")).select_by_value(
            nivel_value
        )
        Select(driver.find_element(By.NAME, "formTurma:inputDepto")).select_by_value(
            str(depto_value)
        )
        year_input = driver.find_element(By.NAME, "formTurma:inputAno")
        year_input.clear()
        year_input.send_keys(str(year))
        Select(driver.find_element(By.NAME, "formTurma:inputPeriodo")).select_by_value(
            str(period)
        )

    def _submit_sigaa_form(self, driver: Any, submit_strategy: str) -> None:
        if WebDriverWait is None or By is None or EC is None:
            raise SigaaScrapingError("Selenium não está instalado no ambiente.")

        wait = WebDriverWait(driver, self.SELENIUM_TIMEOUT_SECONDS)
        button = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[type="submit"][value="Buscar"]')
            )
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
            button,
        )

        if submit_strategy == "native_click":
            wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'input[type="submit"][value="Buscar"]')
                )
            )
            button.click()
            return

        if submit_strategy == "javascript_click":
            driver.execute_script("arguments[0].click();", button)
            return

        if submit_strategy == "form_submit_with_button":
            driver.execute_script(
                """
                const button = arguments[0];
                const form = button.form;
                const hidden = document.createElement('input');
                hidden.type = 'hidden';
                hidden.name = button.name;
                hidden.value = button.value;
                form.appendChild(hidden);
                form.submit();
                """,
                button,
            )
            return

        raise SigaaScrapingError(
            f"Estratégia de submit Selenium inválida: {submit_strategy}"
        )

    def _wait_for_selenium_result(self, driver: Any) -> None:
        if WebDriverWait is None:
            raise SigaaScrapingError("Selenium não está instalado no ambiente.")

        wait = WebDriverWait(driver, self.SELENIUM_TIMEOUT_SECONDS)
        wait.until(
            lambda current_driver: self._response_contains_results_table(
                current_driver.page_source
            )
            or current_driver.current_url.endswith("/home.jsf")
            or current_driver.current_url.endswith("/public/")
        )

    def _build_selenium_diagnostic(
        self,
        driver: Any,
        attempt_url: str,
        submit_strategy: str,
        html: str,
        cookies_before_submit: Sequence[str],
    ) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")
        view_state = ""
        view_state_input = soup.select_one("input[name='javax.faces.ViewState']")
        if view_state_input:
            view_state = self._clean_text(view_state_input.get("value"))

        cookies_after_submit = [
            cookie.get("name", "")
            for cookie in driver.get_cookies()
            if cookie.get("name")
        ]

        return {
            "strategy": "Selenium",
            "submit_strategy": submit_strategy,
            "attempt_url": attempt_url,
            "final_url": driver.current_url,
            "page_title": self._clean_text(driver.title),
            "cookie_names_before_submit": list(cookies_before_submit),
            "cookie_names_after_submit": cookies_after_submit,
            "has_results_table": self._response_contains_results_table(html),
            "has_form_turma": bool(
                soup.select_one("form#formTurma")
                or soup.select_one("form[name='formTurma']")
            ),
            "view_state": view_state,
        }

    def _fetch_with_selenium(
        self,
        year: int,
        period: int,
        depto_value: str,
        nivel_value: str,
    ) -> Tuple[str, Dict[str, Any]]:
        if webdriver is None:
            raise SigaaScrapingError("Selenium não está instalado no ambiente.")

        diagnostics: List[Dict[str, Any]] = []

        for page_url in self._candidate_page_urls():
            for submit_strategy in self.SELENIUM_SUBMIT_STRATEGIES:
                driver = None
                browser_runtime_dir = tempfile.mkdtemp(prefix="sigaa-selenium-")
                service_log_path = os.path.join(browser_runtime_dir, "chromedriver.log")
                try:
                    chrome_options = self._build_selenium_options()
                    chrome_options.add_argument(
                        f"--user-data-dir={os.path.join(browser_runtime_dir, 'profile')}"
                    )
                    chrome_options.add_argument(
                        f"--data-path={os.path.join(browser_runtime_dir, 'data-path')}"
                    )
                    chrome_options.add_argument(
                        f"--disk-cache-dir={os.path.join(browser_runtime_dir, 'cache')}"
                    )

                    driver = webdriver.Chrome(
                        service=self._build_selenium_service(service_log_path),
                        options=chrome_options,
                    )
                    driver.set_page_load_timeout(self.SELENIUM_TIMEOUT_SECONDS)
                    driver.get(page_url)

                    self._fill_sigaa_form(
                        driver, year, period, str(depto_value), nivel_value
                    )
                    cookies_before_submit = [
                        cookie.get("name", "")
                        for cookie in driver.get_cookies()
                        if cookie.get("name")
                    ]

                    try:
                        self._submit_sigaa_form(driver, submit_strategy)
                    except ElementClickInterceptedException:
                        if submit_strategy != "javascript_click":
                            self._submit_sigaa_form(driver, "javascript_click")
                            submit_strategy = "javascript_click"
                        else:
                            raise

                    self._wait_for_selenium_result(driver)
                    final_html = driver.page_source
                    diagnostic = self._build_selenium_diagnostic(
                        driver,
                        page_url,
                        submit_strategy,
                        final_html,
                        cookies_before_submit,
                    )

                    if diagnostic["has_results_table"]:
                        return final_html, diagnostic

                    diagnostics.append(diagnostic)

                except (
                    SeleniumTimeoutException,
                    NoSuchElementException,
                    WebDriverException,
                    ValueError,
                ) as exc:
                    diagnostic: Dict[str, Any] = {
                        "strategy": "Selenium",
                        "submit_strategy": submit_strategy,
                        "attempt_url": page_url,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                    chromedriver_log = self._safe_read_text(service_log_path)
                    if chromedriver_log:
                        diagnostic["chromedriver_log"] = chromedriver_log
                    if driver is not None:
                        diagnostic["final_url"] = driver.current_url
                        diagnostic["page_title"] = self._clean_text(driver.title)
                        diagnostic["cookie_names_after_submit"] = [
                            cookie.get("name", "")
                            for cookie in driver.get_cookies()
                            if cookie.get("name")
                        ]
                    diagnostics.append(diagnostic)
                finally:
                    if driver is not None:
                        driver.quit()
                    shutil.rmtree(browser_runtime_dir, ignore_errors=True)

        raise SigaaScrapingError(
            "Selenium não conseguiu obter a tabela de turmas do SIGAA. "
            f"Diagnóstico: {diagnostics}"
        )

    def fetch_sigaa_turmas_html(
        self,
        year: int,
        period: int,
        depto_id: str | None = None,
        nivel: str | None = None,
    ) -> Tuple[str, Dict[str, Any]]:
        depto_value = depto_id or self.DEFAULT_DEPTO_ID
        nivel_value = nivel or self.DEFAULT_NIVEL
        return self._fetch_with_selenium(year, period, str(depto_value), nivel_value)

    def parse_sigaa_turmas_html(self, html: str) -> List[SigaaTurmaRecord]:
        soup = BeautifulSoup(html, "lxml")
        table = soup.select_one("#turmasAbertas table.listagem") or soup.select_one(
            "table.listagem"
        )
        if not table:
            raise SigaaScrapingError(
                "A tabela pública de turmas do SIGAA não foi encontrada na resposta HTML."
            )

        records: List[SigaaTurmaRecord] = []
        current_code = ""
        current_name = ""

        for row in table.find_all("tr"):
            classes = row.get("class", [])
            row_text = self._clean_text(row.get_text(" ", strip=True))
            if not row_text:
                continue

            if "agrupador" in classes:
                match = re.search(r"([A-Z]{3,}\d{3,})\s*-\s*(.+)", row_text)
                if match:
                    current_code = match.group(1).strip().upper()
                    current_name = self._clean_text(match.group(2))
                continue

            cells = row.find_all("td")
            if len(cells) < 4 or not current_code:
                continue

            turma = self._clean_text(cells[0].get_text(" ", strip=True))
            professores_raw = cells[2].get_text("\n", strip=True)
            horario_texto = self._clean_text(cells[3].get_text(" ", strip=True))
            vagas = (
                self._extract_int(cells[4].get_text(" ", strip=True))
                if len(cells) > 4
                else None
            )

            if not turma or not horario_texto:
                continue

            records.append(
                SigaaTurmaRecord(
                    codigo_disciplina=current_code,
                    nome_disciplina=current_name,
                    turma=turma,
                    professores=self._extract_professor_names_from_sigaa(
                        professores_raw
                    ),
                    professores_raw=self._clean_text(professores_raw),
                    horario_texto=horario_texto,
                    horario_componentes=self._parse_schedule_components(horario_texto),
                    vagas=vagas,
                )
            )

        return records

    def _build_local_records(
        self, local_demands: Iterable[Any]
    ) -> List[Dict[str, Any]]:
        records = []
        for demanda in local_demands:
            horario_sigaa_bruto = self._get_field(demanda, "horario_sigaa_bruto", "")
            schedule_components = self._build_local_schedule_components(
                horario_sigaa_bruto
            )

            record = {
                "id": self._get_field(demanda, "id"),
                "codigo_disciplina": self._clean_text(
                    self._get_field(demanda, "codigo_disciplina", "")
                ).upper(),
                "nome_disciplina": self._clean_text(
                    self._get_field(demanda, "nome_disciplina", "")
                ),
                "turma": self._clean_text(
                    self._get_field(demanda, "turma_disciplina", "")
                ),
                "turma_normalizada": self.normalize_turma_value(
                    self._get_field(demanda, "turma_disciplina", "")
                ),
                "professores_raw": self._clean_text(
                    self._get_field(demanda, "professores_disciplina", "")
                ),
                "professores": self._split_local_professors(
                    self._get_field(demanda, "professores_disciplina", "")
                ),
                "horario_sigaa_bruto": horario_sigaa_bruto,
                "horario_componentes": schedule_components,
                "horario_humano": self._format_schedule_list(schedule_components),
                "schedule_key_set": {
                    self.format_schedule_component(day, time_range)
                    for day, time_range in schedule_components
                },
            }
            records.append(record)

        return records

    def _schedule_overlap_score(
        self,
        local_schedule: Sequence[Tuple[str, str]],
        sigaa_schedule: Sequence[Tuple[str, str]],
    ) -> float:
        local_keys = {
            self.format_schedule_component(day, time_range)
            for day, time_range in local_schedule
        }
        sigaa_keys = {
            self.format_schedule_component(day, time_range)
            for day, time_range in sigaa_schedule
        }

        if not local_keys or not sigaa_keys:
            return 0.0

        return len(local_keys & sigaa_keys) / max(len(local_keys | sigaa_keys), 1)

    def _select_best_sigaa_candidate(
        self, local_record: Dict[str, Any], candidates: Sequence[SigaaTurmaRecord]
    ) -> Tuple[Optional[SigaaTurmaRecord], float]:
        if not candidates:
            return None, 0.0

        exact_turma_candidates = [
            candidate
            for candidate in candidates
            if candidate.turma_normalizada == local_record["turma_normalizada"]
        ]
        pool = exact_turma_candidates or list(candidates)

        best_candidate: Optional[SigaaTurmaRecord] = None
        best_score = -1.0

        for candidate in pool:
            professor_similarity = self._professor_list_similarity(
                local_record["professores"], candidate.professores
            )
            schedule_overlap = self._schedule_overlap_score(
                local_record["horario_componentes"], candidate.horario_componentes
            )
            turma_score = (
                1.0
                if candidate.turma_normalizada == local_record["turma_normalizada"]
                else 0.0
            )

            if exact_turma_candidates:
                total_score = (
                    (0.65 * turma_score)
                    + (0.20 * professor_similarity)
                    + (0.15 * schedule_overlap)
                )
            else:
                total_score = (
                    (0.50 * professor_similarity)
                    + (0.35 * schedule_overlap)
                    + (0.15 * turma_score)
                )

            if total_score > best_score:
                best_score = total_score
                best_candidate = candidate

        minimum_score = 0.55 if exact_turma_candidates else 0.60
        if best_score < minimum_score:
            return None, best_score

        return best_candidate, best_score

    def compare_local_demands_to_sigaa(
        self,
        semester_name: str,
        local_demands: Sequence[Any],
        depto_id: str | None = None,
        nivel: str | None = None,
    ) -> Dict[str, Any]:
        year, period = self.semester_name_to_year_period(semester_name)
        html, probe = self.fetch_sigaa_turmas_html(
            year, period, depto_id=depto_id, nivel=nivel
        )
        sigaa_records = self.parse_sigaa_turmas_html(html)
        local_records = self._build_local_records(local_demands)

        sigaa_by_code: Dict[str, List[SigaaTurmaRecord]] = {}
        for record in sigaa_records:
            sigaa_by_code.setdefault(record.codigo_disciplina, []).append(record)

        discrepancies: List[Dict[str, Any]] = []
        missing_in_sigaa: List[Dict[str, Any]] = []
        missing_in_local: List[Dict[str, Any]] = []
        matched_sigaa_keys: set[Tuple[str, str, str]] = set()
        status_by_demanda_id: Dict[int, str] = {}

        schedule_mismatch_count = 0
        professor_mismatch_count = 0
        turma_mismatch_count = 0

        for local_record in local_records:
            code = local_record["codigo_disciplina"]
            candidates = sigaa_by_code.get(code, [])
            matched_sigaa, match_score = self._select_best_sigaa_candidate(
                local_record, candidates
            )

            if not matched_sigaa:
                if local_record["id"] is not None:
                    status_by_demanda_id[int(local_record["id"])] = (
                        "❌ Ausente no SIGAA"
                    )
                missing_in_sigaa.append(
                    {
                        "Demanda ID": local_record["id"],
                        "Código": code,
                        "Disciplina": local_record["nome_disciplina"],
                        "Turma": local_record["turma"],
                        "Professores": local_record["professores_raw"],
                        "Horário (Sistema)": local_record["horario_humano"],
                        "Observação": "Nenhuma turma correspondente foi encontrada no SIGAA público para este código.",
                    }
                )
                continue

            matched_sigaa_keys.add(matched_sigaa.unique_key)

            professor_similarity = self._professor_list_similarity(
                local_record["professores"], matched_sigaa.professores
            )
            local_schedule_keys = local_record["schedule_key_set"]
            sigaa_schedule_keys = matched_sigaa.schedule_key_set

            issue_types: List[str] = []
            if local_record["turma_normalizada"] != matched_sigaa.turma_normalizada:
                turma_mismatch_count += 1
                issue_types.append("Turma")
            if local_schedule_keys != sigaa_schedule_keys:
                schedule_mismatch_count += 1
                issue_types.append("Horário")
            if professor_similarity < 0.78:
                professor_mismatch_count += 1
                issue_types.append("Professor")

            if issue_types:
                if local_record["id"] is not None:
                    status_by_demanda_id[int(local_record["id"])] = (
                        f"⚠️ {', '.join(issue_types)}"
                    )
                discrepancies.append(
                    {
                        "Demanda ID": local_record["id"],
                        "Código": code,
                        "Disciplina": local_record["nome_disciplina"]
                        or matched_sigaa.nome_disciplina,
                        "Tipos de Divergência": ", ".join(issue_types),
                        "Turma (Sistema)": local_record["turma"],
                        "Turma (SIGAA)": matched_sigaa.turma,
                        "Professores (Sistema)": local_record["professores_raw"],
                        "Professores (SIGAA)": matched_sigaa.professores_raw,
                        "Similaridade Professores": round(professor_similarity, 2),
                        "Horário (Sistema)": local_record["horario_humano"],
                        "Horário (SIGAA)": matched_sigaa.horario_texto,
                        "Somente no Sistema": " | ".join(
                            sorted(local_schedule_keys - sigaa_schedule_keys)
                        ),
                        "Somente no SIGAA": " | ".join(
                            sorted(sigaa_schedule_keys - local_schedule_keys)
                        ),
                        "Score de Match": round(match_score, 2),
                    }
                )
            elif local_record["id"] is not None:
                status_by_demanda_id[int(local_record["id"])] = "✅ Sem divergência"

        for record in sigaa_records:
            if record.unique_key in matched_sigaa_keys:
                continue
            missing_in_local.append(
                {
                    "Código": record.codigo_disciplina,
                    "Disciplina": record.nome_disciplina,
                    "Turma": record.turma,
                    "Professores": record.professores_raw,
                    "Horário (SIGAA)": record.horario_texto,
                }
            )

        return {
            "semester_name": semester_name,
            "query": {
                "year": year,
                "period": period,
                "depto_id": str(depto_id or self.DEFAULT_DEPTO_ID),
                "nivel": nivel or self.DEFAULT_NIVEL,
            },
            "probe": probe,
            "local_total": len(local_records),
            "sigaa_total": len(sigaa_records),
            "matched_count": len(local_records) - len(missing_in_sigaa),
            "discrepancy_count": len(discrepancies),
            "schedule_mismatch_count": schedule_mismatch_count,
            "professor_mismatch_count": professor_mismatch_count,
            "turma_mismatch_count": turma_mismatch_count,
            "missing_in_sigaa_count": len(missing_in_sigaa),
            "missing_in_local_count": len(missing_in_local),
            "status_by_demanda_id": status_by_demanda_id,
            "discrepancies": discrepancies,
            "missing_in_sigaa": missing_in_sigaa,
            "missing_in_local": missing_in_local,
        }
