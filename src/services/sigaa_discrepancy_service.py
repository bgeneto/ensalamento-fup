"""SIGAA scraping and discrepancy comparison service."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd
from bs4 import BeautifulSoup

from src.integrations.sigaa import SigaaPublicTurmasClient, SigaaScrapingError
from src.utils.sigaa_parser import SigaaScheduleParser


@dataclass
class SigaaTurmaRecord:
    """One turma row parsed from the public SIGAA table."""

    codigo_disciplina: str
    nome_disciplina: str
    turma: str
    professores: List[str]
    professores_raw: str
    horario_texto: str
    horario_componentes: List[Tuple[str, str]]
    vagas: Optional[int] = None

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
    def unique_key(self) -> str:
        schedule_key = "|".join(sorted(self.schedule_key_set))
        return f"{self.codigo_disciplina}|{self.turma_normalizada}|{schedule_key}"


@dataclass
class LocalSuboffer:
    """One comparable local offer slice used for matching against SIGAA."""

    codigo_disciplina: str
    nome_disciplina: str
    turma: str
    turma_normalizada: str
    professores: List[str] = field(default_factory=list)
    cursos: List[str] = field(default_factory=list)
    horario_componentes: List[Tuple[str, str]] = field(default_factory=list)
    schedule_key_set: set[str] = field(default_factory=set)
    horario_sigaa_brutos: List[str] = field(default_factory=list)
    demanda_ids: List[int] = field(default_factory=list)

    @property
    def professores_raw(self) -> str:
        return ", ".join(self.professores)

    @property
    def horario_humano(self) -> str:
        return SigaaDiscrepancyService._format_schedule_list(self.horario_componentes)

    @property
    def unique_key(self) -> str:
        schedule_key = "|".join(sorted(self.schedule_key_set))
        return f"{self.codigo_disciplina}|{self.turma_normalizada}|{schedule_key}"


@dataclass
class LocalGroup:
    """Consolidated local representation shown to the UI."""

    codigo_disciplina: str
    nome_disciplina: str
    turma: str
    turma_normalizada: str
    suboffers: List[LocalSuboffer] = field(default_factory=list)
    professores: List[str] = field(default_factory=list)
    cursos: List[str] = field(default_factory=list)
    demanda_ids: List[int] = field(default_factory=list)

    @property
    def professores_raw(self) -> str:
        return ", ".join(self.professores)

    @property
    def schedule_key_set(self) -> set[str]:
        result: set[str] = set()
        for suboffer in self.suboffers:
            result.update(suboffer.schedule_key_set)
        return result

    @property
    def horario_componentes(self) -> List[Tuple[str, str]]:
        components: list[Tuple[str, str]] = []
        seen: set[str] = set()
        for suboffer in self.suboffers:
            for day, time_range in suboffer.horario_componentes:
                key = SigaaDiscrepancyService.format_schedule_component(day, time_range)
                if key in seen:
                    continue
                seen.add(key)
                components.append((day, time_range))
        return SigaaDiscrepancyService._sort_schedule_components(components)

    @property
    def horario_humano(self) -> str:
        return SigaaDiscrepancyService._format_schedule_list(self.horario_componentes)

    @property
    def unique_key(self) -> str:
        return f"{self.codigo_disciplina}|{self.turma_normalizada}"


class SigaaDiscrepancyService:
    """Service that scrapes SIGAA and compares it against local demands."""

    DEFAULT_DEPTO_ID = "666"
    DEFAULT_NIVEL = "G"
    DAY_ORDER = {"SEG": 2, "TER": 3, "QUA": 4, "QUI": 5, "SEX": 6, "SAB": 7}
    SCHEDULE_PATTERN = re.compile(
        r"\b(SEG|TER|QUA|QUI|SEX|SAB)\s+(\d{2}:\d{2}\s*-\s*\d{2}:\d{2})\b",
        flags=re.IGNORECASE,
    )

    def __init__(
        self,
        client: Optional[SigaaPublicTurmasClient] = None,
        schedule_parser: Optional[SigaaScheduleParser] = None,
    ) -> None:
        if client is None or schedule_parser is None:
            from src.utils.cache_helpers import (
                get_sigaa_parser,
                get_sigaa_public_turmas_client,
            )

        self.client = client or get_sigaa_public_turmas_client()
        self.schedule_parser = schedule_parser or get_sigaa_parser()

    @classmethod
    def normalize_turma_value(cls, turma: Any) -> str:
        value = cls._clean_text(turma)
        if not value:
            return ""
        if value.isdigit():
            return str(int(value))
        return value.upper()

    @classmethod
    def semester_name_to_year_period(cls, semester_name: str) -> Tuple[int, int]:
        cleaned = cls._clean_text(semester_name)
        match = re.fullmatch(r"(\d{4})[-.](\d+)", cleaned)
        if not match:
            raise ValueError(
                f"Semestre '{semester_name}' inválido para consulta no SIGAA. Use o formato AAAA-N."
            )
        return int(match.group(1)), int(match.group(2))

    @staticmethod
    def format_schedule_component(day: str, time_range: str) -> str:
        return f"{day} {time_range}".strip()

    def fetch_sigaa_turmas_html(
        self,
        year: int,
        period: int,
        depto_id: str | None = None,
        nivel: str | None = None,
    ) -> Tuple[str, Dict[str, Any]]:
        depto_value = depto_id or self.DEFAULT_DEPTO_ID
        nivel_value = nivel or self.DEFAULT_NIVEL
        return self.client.fetch_turmas_html(
            year,
            period,
            depto_id=str(depto_value),
            nivel=nivel_value,
        )

    def compare_local_demands_to_sigaa(
        self,
        semester_name: str,
        local_demands: Sequence[Any],
        depto_id: str | None = None,
        nivel: str | None = None,
    ) -> Dict[str, Any]:
        rows = list(local_demands)
        return self._compare_local_rows(
            semester_name=semester_name,
            local_rows=rows,
            depto_id=depto_id,
            nivel=nivel,
        )

    def compare_local_dataframe_to_sigaa(
        self,
        semester_name: str,
        local_df: pd.DataFrame,
        depto_id: str | None = None,
        nivel: str | None = None,
    ) -> Dict[str, Any]:
        rows = [] if local_df is None else local_df.to_dict(orient="records")
        return self._compare_local_rows(
            semester_name=semester_name,
            local_rows=rows,
            depto_id=depto_id,
            nivel=nivel,
        )

    def parse_sigaa_turmas_html(self, html: str) -> List[SigaaTurmaRecord]:
        soup = BeautifulSoup(html, "lxml")
        table = soup.select_one("#turmasAbertas table.listagem") or soup.select_one(
            "table.listagem"
        )
        if table is None:
            raise SigaaScrapingError(
                "A tabela pública de turmas do SIGAA não foi encontrada na resposta HTML."
            )

        records: list[SigaaTurmaRecord] = []
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

    def _compare_local_rows(
        self,
        *,
        semester_name: str,
        local_rows: Sequence[Any],
        depto_id: str | None,
        nivel: str | None,
    ) -> Dict[str, Any]:
        year, period = self.semester_name_to_year_period(semester_name)
        html, probe = self.fetch_sigaa_turmas_html(
            year, period, depto_id=depto_id, nivel=nivel
        )
        sigaa_records = self.parse_sigaa_turmas_html(html)
        local_records = self._build_local_records(local_rows)
        local_groups = self._build_local_groups(local_records)

        sigaa_by_code: dict[str, list[SigaaTurmaRecord]] = {}
        for record in sigaa_records:
            sigaa_by_code.setdefault(record.codigo_disciplina, []).append(record)

        suboffer_match_map, matched_sigaa_keys = self._match_local_suboffers_to_sigaa(
            local_groups,
            sigaa_by_code,
        )

        discrepancies: list[dict[str, Any]] = []
        missing_in_sigaa: list[dict[str, Any]] = []
        missing_in_local: list[dict[str, Any]] = []
        status_by_demanda_id: dict[int, str] = {}

        schedule_mismatch_count = 0
        professor_mismatch_count = 0
        turma_mismatch_count = 0
        consolidated_turma_count = 0

        for group in local_groups:
            matched_pairs = [
                suboffer_match_map[suboffer.unique_key]
                for suboffer in group.suboffers
                if suboffer.unique_key in suboffer_match_map
            ]
            matched_records = self._unique_sigaa_records(
                [pair["sigaa_record"] for pair in matched_pairs]
            )
            unmatched_suboffers = [
                suboffer
                for suboffer in group.suboffers
                if suboffer.unique_key not in suboffer_match_map
            ]

            if not matched_records:
                self._set_group_status(
                    status_by_demanda_id,
                    group,
                    "❌ Ausente no SIGAA",
                )
                for suboffer in unmatched_suboffers or group.suboffers:
                    missing_in_sigaa.append(
                        {
                            "Código": suboffer.codigo_disciplina,
                            "Disciplina": suboffer.nome_disciplina,
                            "Turma": group.turma,
                            "Cursos": ", ".join(suboffer.cursos),
                            "Professores": suboffer.professores_raw,
                            "Horário (Sistema)": suboffer.horario_humano,
                            "Observação": "Nenhuma oferta correspondente foi encontrada no SIGAA.",
                        }
                    )
                continue

            for suboffer in unmatched_suboffers:
                missing_in_sigaa.append(
                    {
                        "Código": suboffer.codigo_disciplina,
                        "Disciplina": suboffer.nome_disciplina,
                        "Turma": group.turma,
                        "Cursos": ", ".join(suboffer.cursos),
                        "Professores": suboffer.professores_raw,
                        "Horário (Sistema)": suboffer.horario_humano,
                        "Observação": "Oferta local sem correspondência no SIGAA.",
                    }
                )

            issue_types: list[str] = []
            matched_sigaa_turmas = sorted(
                {record.turma_normalizada for record in matched_records}
            )
            union_sigaa_schedule = set().union(
                *(record.schedule_key_set for record in matched_records)
            )
            union_sigaa_professors = self._unique_strings(
                name for record in matched_records for name in record.professores
            )
            professor_similarity = self._professor_list_similarity(
                group.professores,
                union_sigaa_professors,
            )
            only_in_system = sorted(group.schedule_key_set - union_sigaa_schedule)
            only_in_sigaa = sorted(union_sigaa_schedule - group.schedule_key_set)

            if len(matched_sigaa_turmas) > 1:
                consolidated_turma_count += 1
                issue_types.append("Turma consolidada localmente")

            if only_in_system or only_in_sigaa:
                schedule_mismatch_count += 1
                issue_types.append("Horário")

            if professor_similarity < 0.78:
                professor_mismatch_count += 1
                issue_types.append("Professor")

            if unmatched_suboffers:
                issue_types.append("Ausente no SIGAA")

            if issue_types:
                self._set_group_status(
                    status_by_demanda_id,
                    group,
                    "⚠️ " + ", ".join(issue_types),
                )
                discrepancies.append(
                    {
                        "Código": group.codigo_disciplina,
                        "Disciplina": group.nome_disciplina,
                        "Turma (Sistema)": group.turma,
                        "Turmas (SIGAA)": ", ".join(
                            record.turma for record in matched_records
                        ),
                        "Tipos de Divergência": ", ".join(issue_types),
                        "Cursos": ", ".join(group.cursos),
                        "Professores (Sistema)": group.professores_raw,
                        "Professores (SIGAA)": ", ".join(union_sigaa_professors),
                        "Horário (Sistema)": group.horario_humano,
                        "Horário (SIGAA)": self._format_schedule_list(
                            self._sort_schedule_components(
                                [
                                    component
                                    for record in matched_records
                                    for component in record.horario_componentes
                                ]
                            )
                        ),
                    }
                )
            else:
                self._set_group_status(
                    status_by_demanda_id,
                    group,
                    "✅ Sem divergência",
                )

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
            "local_total": len(local_groups),
            "local_row_total": len(local_records),
            "local_suboffer_total": sum(len(group.suboffers) for group in local_groups),
            "sigaa_total": len(sigaa_records),
            "matched_count": len(
                [
                    group
                    for group in local_groups
                    if any(
                        suboffer.unique_key in suboffer_match_map
                        for suboffer in group.suboffers
                    )
                ]
            ),
            "discrepancy_count": len(discrepancies),
            "schedule_mismatch_count": schedule_mismatch_count,
            "professor_mismatch_count": professor_mismatch_count,
            "turma_mismatch_count": turma_mismatch_count,
            "consolidated_turma_count": consolidated_turma_count,
            "missing_in_sigaa_count": len(missing_in_sigaa),
            "missing_in_local_count": len(missing_in_local),
            "status_by_demanda_id": status_by_demanda_id,
            "discrepancies": discrepancies,
            "missing_in_sigaa": missing_in_sigaa,
            "missing_in_local": missing_in_local,
        }

    def _build_local_records(
        self, local_demands: Sequence[Any]
    ) -> List[Dict[str, Any]]:
        records: list[dict[str, Any]] = []
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
                "codigo_curso": self._clean_text(
                    self._get_field(demanda, "codigo_curso", "")
                ).upper(),
            }
            records.append(record)

        return records

    def _build_local_groups(
        self, local_records: Sequence[Dict[str, Any]]
    ) -> List[LocalGroup]:
        groups: dict[tuple[str, str], LocalGroup] = {}
        suboffers_by_group: dict[
            tuple[str, str], dict[tuple[str, ...], LocalSuboffer]
        ] = {}

        for record in local_records:
            group_key = (
                record["codigo_disciplina"],
                record["turma_normalizada"],
            )
            if group_key not in groups:
                groups[group_key] = LocalGroup(
                    codigo_disciplina=record["codigo_disciplina"],
                    nome_disciplina=record["nome_disciplina"],
                    turma=record["turma"],
                    turma_normalizada=record["turma_normalizada"],
                )
                suboffers_by_group[group_key] = {}

            group = groups[group_key]
            self._merge_string_list(group.professores, record["professores"])
            if record["codigo_curso"]:
                self._merge_string_list(group.cursos, [record["codigo_curso"]])
            demanda_id = record["id"]
            if isinstance(demanda_id, int) and demanda_id not in group.demanda_ids:
                group.demanda_ids.append(demanda_id)

            suboffer_key = tuple(sorted(record["schedule_key_set"]))
            suboffer = suboffers_by_group[group_key].get(suboffer_key)
            if suboffer is None:
                suboffer = LocalSuboffer(
                    codigo_disciplina=record["codigo_disciplina"],
                    nome_disciplina=record["nome_disciplina"],
                    turma=record["turma"],
                    turma_normalizada=record["turma_normalizada"],
                    horario_componentes=self._sort_schedule_components(
                        list(record["horario_componentes"])
                    ),
                    schedule_key_set=set(record["schedule_key_set"]),
                )
                suboffers_by_group[group_key][suboffer_key] = suboffer
                group.suboffers.append(suboffer)

            self._merge_string_list(suboffer.professores, record["professores"])
            if record["codigo_curso"]:
                self._merge_string_list(suboffer.cursos, [record["codigo_curso"]])
            if record["horario_sigaa_bruto"]:
                self._merge_string_list(
                    suboffer.horario_sigaa_brutos,
                    [self._clean_text(record["horario_sigaa_bruto"])],
                )
            if isinstance(demanda_id, int) and demanda_id not in suboffer.demanda_ids:
                suboffer.demanda_ids.append(demanda_id)

        for group in groups.values():
            group.professores.sort()
            group.cursos.sort()
            group.demanda_ids.sort()
            group.suboffers.sort(key=lambda item: tuple(sorted(item.schedule_key_set)))
            for suboffer in group.suboffers:
                suboffer.professores.sort()
                suboffer.cursos.sort()
                suboffer.horario_sigaa_brutos.sort()
                suboffer.demanda_ids.sort()

        return sorted(
            groups.values(),
            key=lambda group: (group.codigo_disciplina, group.turma_normalizada),
        )

    def _match_local_suboffers_to_sigaa(
        self,
        local_groups: Sequence[LocalGroup],
        sigaa_by_code: Dict[str, List[SigaaTurmaRecord]],
    ) -> Tuple[Dict[str, Dict[str, Any]], set[str]]:
        candidates: list[dict[str, Any]] = []
        for group in local_groups:
            for suboffer in group.suboffers:
                for record in sigaa_by_code.get(suboffer.codigo_disciplina, []):
                    pair = self._score_suboffer_match(suboffer, record)
                    if pair["score"] >= 0.55:
                        candidates.append(pair)

        candidates.sort(
            key=lambda item: (
                item["score"],
                item["exact_schedule"],
                item["schedule_overlap"],
                item["turma_score"],
                item["professor_similarity"],
            ),
            reverse=True,
        )

        matched_suboffers: set[str] = set()
        matched_sigaa: set[str] = set()
        match_map: dict[str, dict[str, Any]] = {}

        for candidate in candidates:
            local_key = candidate["local_suboffer"].unique_key
            sigaa_key = candidate["sigaa_record"].unique_key
            if local_key in matched_suboffers or sigaa_key in matched_sigaa:
                continue
            matched_suboffers.add(local_key)
            matched_sigaa.add(sigaa_key)
            match_map[local_key] = candidate

        return match_map, matched_sigaa

    def _score_suboffer_match(
        self,
        local_suboffer: LocalSuboffer,
        sigaa_record: SigaaTurmaRecord,
    ) -> Dict[str, Any]:
        professor_similarity = self._professor_list_similarity(
            local_suboffer.professores,
            sigaa_record.professores,
        )
        schedule_overlap = self._schedule_overlap_score(
            local_suboffer.horario_componentes,
            sigaa_record.horario_componentes,
        )
        turma_score = (
            1.0
            if local_suboffer.turma_normalizada == sigaa_record.turma_normalizada
            else 0.0
        )
        exact_schedule = (
            1.0
            if local_suboffer.schedule_key_set == sigaa_record.schedule_key_set
            else 0.0
        )
        score = (
            0.45 * schedule_overlap
            + 0.30 * professor_similarity
            + 0.15 * turma_score
            + 0.10 * exact_schedule
        )
        return {
            "local_suboffer": local_suboffer,
            "sigaa_record": sigaa_record,
            "score": score,
            "professor_similarity": professor_similarity,
            "schedule_overlap": schedule_overlap,
            "turma_score": turma_score,
            "exact_schedule": exact_schedule,
        }

    def _parse_schedule_components(self, horario_texto: str) -> List[Tuple[str, str]]:
        cleaned = self._clean_schedule_text(horario_texto)
        raw_codes = self._extract_sigaa_schedule_codes(cleaned)
        if raw_codes:
            return self._build_local_schedule_components(raw_codes)

        components: list[Tuple[str, str]] = []
        for day_name, time_range in self.SCHEDULE_PATTERN.findall(cleaned or ""):
            normalized_day = day_name.upper()
            normalized_range = time_range.replace(" ", "")
            components.append((normalized_day, normalized_range))

        return self._sort_schedule_components(self._deduplicate_components(components))

    def _build_local_schedule_components(
        self,
        horario_sigaa_bruto: str,
    ) -> List[Tuple[str, str]]:
        groups = self.schedule_parser.get_block_groups_with_names(
            horario_sigaa_bruto or ""
        )
        components: list[Tuple[str, str]] = []

        for group in groups:
            day_name = self._clean_text(group.get("day_name"))
            time_range = self.schedule_parser.get_time_range_for_blocks(
                group.get("blocks", [])
            )
            if not day_name or not time_range:
                continue
            components.append((day_name, time_range))

        return self._sort_schedule_components(components)

    def _extract_professor_names_from_sigaa(self, raw_text: str) -> List[str]:
        names: list[str] = []
        current_parts: list[str] = []

        for line in raw_text.splitlines():
            cleaned_line = self._clean_text(line)
            if not cleaned_line:
                continue

            if re.fullmatch(r"\(\d+h\)", cleaned_line, flags=re.IGNORECASE):
                if current_parts:
                    names.append(self._clean_text(" ".join(current_parts)))
                    current_parts = []
                continue

            line_without_hours = re.sub(
                r"\s*\(\d+h\)\s*$",
                "",
                cleaned_line,
                flags=re.IGNORECASE,
            )
            current_parts.append(line_without_hours)

            if line_without_hours != cleaned_line:
                names.append(self._clean_text(" ".join(current_parts)))
                current_parts = []

        if current_parts:
            names.append(self._clean_text(" ".join(current_parts)))

        return self._unique_strings(names)

    def _split_local_professors(self, raw_text: str) -> List[str]:
        chunks = re.split(r"[,;\n]+", raw_text or "")
        return self._unique_strings(self._clean_text(chunk) for chunk in chunks)

    def _professor_list_similarity(
        self,
        local_professors: Sequence[str],
        sigaa_professors: Sequence[str],
    ) -> float:
        if not local_professors and not sigaa_professors:
            return 1.0
        if not local_professors or not sigaa_professors:
            return 0.0

        local_normalized = [
            self._normalize_person_name(name) for name in local_professors
        ]
        sigaa_normalized = [
            self._normalize_person_name(name) for name in sigaa_professors
        ]

        def best_average(source: Sequence[str], target: Sequence[str]) -> float:
            scores: list[float] = []
            for source_name in source:
                best = max(
                    SequenceMatcher(None, source_name, target_name).ratio()
                    for target_name in target
                )
                scores.append(best)
            return sum(scores) / len(scores) if scores else 0.0

        return (
            best_average(local_normalized, sigaa_normalized)
            + best_average(sigaa_normalized, local_normalized)
        ) / 2.0

    def _schedule_overlap_score(
        self,
        local_components: Sequence[Tuple[str, str]],
        sigaa_components: Sequence[Tuple[str, str]],
    ) -> float:
        local_keys = {
            self.format_schedule_component(day, time_range)
            for day, time_range in local_components
        }
        sigaa_keys = {
            self.format_schedule_component(day, time_range)
            for day, time_range in sigaa_components
        }
        if not local_keys and not sigaa_keys:
            return 1.0
        if not local_keys or not sigaa_keys:
            return 0.0
        intersection = len(local_keys & sigaa_keys)
        union = len(local_keys | sigaa_keys)
        return intersection / union if union else 0.0

    @classmethod
    def _format_schedule_list(cls, components: Sequence[Tuple[str, str]]) -> str:
        return " | ".join(
            cls.format_schedule_component(day, time_range)
            for day, time_range in cls._sort_schedule_components(components)
        )

    @classmethod
    def _sort_schedule_components(
        cls,
        components: Sequence[Tuple[str, str]],
    ) -> List[Tuple[str, str]]:
        return sorted(
            list(components),
            key=lambda item: (cls.DAY_ORDER.get(item[0], 99), item[1]),
        )

    @staticmethod
    def _deduplicate_components(
        components: Sequence[Tuple[str, str]],
    ) -> List[Tuple[str, str]]:
        seen: set[Tuple[str, str]] = set()
        deduplicated: list[Tuple[str, str]] = []
        for component in components:
            if component in seen:
                continue
            seen.add(component)
            deduplicated.append(component)
        return deduplicated

    @classmethod
    def _clean_text(cls, value: Any) -> str:
        if value is None:
            return ""
        return " ".join(str(value).split()).strip()

    @staticmethod
    def _extract_int(value: Any) -> Optional[int]:
        match = re.search(r"\d+", str(value or ""))
        if not match:
            return None
        return int(match.group(0))

    @staticmethod
    def _merge_string_list(target: List[str], values: Iterable[str]) -> None:
        existing = set(target)
        for value in values:
            cleaned = SigaaDiscrepancyService._clean_text(value)
            if not cleaned or cleaned in existing:
                continue
            target.append(cleaned)
            existing.add(cleaned)

    @staticmethod
    def _get_field(item: Any, field: str, default: Any = None) -> Any:
        aliases = {
            "codigo_disciplina": ["codigo_disciplina", "Código"],
            "nome_disciplina": ["nome_disciplina", "Disciplina"],
            "turma_disciplina": ["turma_disciplina", "Turma"],
            "professores_disciplina": ["professores_disciplina", "Professores"],
            "horario_sigaa_bruto": ["horario_sigaa_bruto", "Horário"],
            "codigo_curso": ["codigo_curso", "Curso"],
            "id": ["id", "ID"],
        }
        keys = aliases.get(field, [field])
        for key in keys:
            if isinstance(item, dict) and key in item:
                return item.get(key, default)
            if hasattr(item, key):
                return getattr(item, key)
        return default

    @staticmethod
    def _normalize_person_name(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value or "")
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^a-z0-9]+", " ", ascii_only.lower()).strip()

    @staticmethod
    def _unique_strings(values: Iterable[str]) -> List[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = SigaaDiscrepancyService._clean_text(value)
            if not cleaned:
                continue
            marker = cleaned.casefold()
            if marker in seen:
                continue
            seen.add(marker)
            result.append(cleaned)
        return result

    @staticmethod
    def _clean_schedule_text(value: str) -> str:
        cleaned = SigaaDiscrepancyService._clean_text(value)
        cleaned = re.sub(r"\(\d{2}/\d{2}/\d{4}\s*-\s*\d{2}/\d{2}/\d{4}\)", "", cleaned)
        return SigaaDiscrepancyService._clean_text(cleaned)

    @staticmethod
    def _extract_sigaa_schedule_codes(value: str) -> str:
        matches = re.finditer(SigaaScheduleParser.PATTERN, value or "")
        return " ".join(match.group(0) for match in matches)

    @staticmethod
    def _unique_sigaa_records(
        records: Sequence[SigaaTurmaRecord],
    ) -> List[SigaaTurmaRecord]:
        result: list[SigaaTurmaRecord] = []
        seen: set[str] = set()
        for record in records:
            if record.unique_key in seen:
                continue
            seen.add(record.unique_key)
            result.append(record)
        return result

    @staticmethod
    def _set_group_status(
        status_by_demanda_id: Dict[int, str],
        group: LocalGroup,
        status: str,
    ) -> None:
        for demanda_id in group.demanda_ids:
            status_by_demanda_id[int(demanda_id)] = status
