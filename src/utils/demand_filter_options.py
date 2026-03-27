"""Helpers for building demand-related filter options."""

from typing import Any, Iterable


def build_demand_filter_options(
    demandas: Iterable[Any],
) -> tuple[dict[str, str], dict[str, str]]:
    """Build discipline and professor filter options from semester demands."""
    discipline_options = {"all": "Todas as disciplinas"}
    professor_options = {"all": "Todos os professores"}

    for demanda in demandas:
        discipline_code = str(getattr(demanda, "codigo_disciplina", "") or "").strip()
        discipline_name = str(getattr(demanda, "nome_disciplina", "") or "").strip()

        if discipline_code and discipline_code not in discipline_options:
            discipline_options[discipline_code] = (
                f"{discipline_code} - {discipline_name}"
                if discipline_name
                else discipline_code
            )

        professors_raw = str(
            getattr(demanda, "professores_disciplina", "") or ""
        ).strip()
        if not professors_raw:
            continue

        for professor in split_professors(professors_raw):
            professor_options.setdefault(professor, professor)

    return discipline_options, professor_options


def split_professors(professors_raw: str) -> list[str]:
    """Split a raw professor field into individual normalized names."""
    return [
        professor.strip()
        for professor in professors_raw.replace(";", ",").replace("/", ",").split(",")
        if professor.strip()
    ]
