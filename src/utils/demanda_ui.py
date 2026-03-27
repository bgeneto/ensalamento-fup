"""Helpers for keeping Demanda page filters predictable across reruns."""

from __future__ import annotations

from typing import Iterable

PREDEFINED_COURSE_CODES = (
    "PPGCIMA",
    "PPGCA-M",
    "PPGCA-D",
    "CND",
    "CNN",
    "LEDOC",
    "PPGEC",
    "GAM",
    "GEAGRO",
    "PROFAGUA",
    "PPGP",
    "PPG-MADER",
    "OUTROS",
)

DEFAULT_IGNORED_COURSE_CODES = ("LEDOC", "OUTROS")


def build_course_ignore_options(cursos_from_db: Iterable[str] | None) -> list[str]:
    """Return a stable option list for the ignore-courses selector."""
    options = {
        code.strip()
        for code in (cursos_from_db or [])
        if isinstance(code, str) and code.strip()
    }
    options.update(PREDEFINED_COURSE_CODES)
    return sorted(options)


def default_ignored_courses(options: Iterable[str] | None = None) -> list[str]:
    """Return the default ignored courses filtered by the available options."""
    if options is None:
        return list(DEFAULT_IGNORED_COURSE_CODES)
    valid_codes = set(options)
    return [code for code in DEFAULT_IGNORED_COURSE_CODES if code in valid_codes]


def sanitize_ignored_courses(
    selected_codes: Iterable[str] | None, options: Iterable[str]
) -> list[str]:
    """Drop stale selections that are no longer available in the widget."""
    valid_codes = set(options)
    return [code for code in (selected_codes or []) if code in valid_codes]
