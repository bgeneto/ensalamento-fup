from __future__ import annotations

from contextlib import contextmanager

from src.repositories.disciplina import DisciplinaRepository
from src.services import semester_service
from src.utils.demanda_ui import (
    build_course_ignore_options,
    default_ignored_courses,
    sanitize_ignored_courses,
)


def _oferta(
    codigo: str,
    turma: str,
    horario: str,
    professor: str,
    codigo_curso: str = "CND",
    vagas: str = "30",
) -> dict:
    return {
        "cod_curso": codigo_curso,
        "cod_disciplina": codigo,
        "nome_disciplina": f"Disciplina {codigo}",
        "cod_turma": turma,
        "vagas_turma": vagas,
        "horario_turma": horario,
        "professores": [{"nome_perfil": professor}],
    }


def test_sync_second_run_stays_unchanged_when_api_payload_is_the_same(
    db_session, monkeypatch
):
    payload = {
        "semestre": "2026-1",
        "ofertas": {
            "oferta-1": _oferta("FUP0001", "01", "24M12", "Prof. Ana"),
            "oferta-2": _oferta("FUP0002", "01", "35T12", "Prof. Beto"),
        },
    }

    @contextmanager
    def fake_db_session():
        yield db_session

    monkeypatch.setattr(semester_service, "get_db_session", fake_db_session)
    monkeypatch.setattr(semester_service, "fetch_ofertas", lambda cod_semestre: payload)

    first_summary = semester_service.sync_semester_from_api("2026-1")
    second_summary = semester_service.sync_semester_from_api("2026-1")

    assert first_summary["created"] == 2
    assert first_summary["updated_from_api"] == 0
    assert first_summary["unchanged"] == 0

    assert second_summary["created"] == 0
    assert second_summary["updated_from_api"] == 0
    assert second_summary["unchanged"] == 2
    assert second_summary["removed_in_api"] == 0

    repo = DisciplinaRepository(db_session)
    demandas = repo.get_by_semestre(1)
    assert len(demandas) == 2
    assert all(d.sync_status == "active" for d in demandas)


def test_ignore_course_options_remain_stable_and_explicit():
    empty_db_options = build_course_ignore_options([])
    populated_db_options = build_course_ignore_options(["CND", "GAM"])

    assert "LEDOC" in empty_db_options
    assert "OUTROS" in empty_db_options
    assert "LEDOC" in populated_db_options
    assert "OUTROS" in populated_db_options
    assert default_ignored_courses() == ["LEDOC", "OUTROS"]
    assert default_ignored_courses(populated_db_options) == ["LEDOC", "OUTROS"]
    assert sanitize_ignored_courses(["CND", "INEXISTENTE"], populated_db_options) == [
        "CND"
    ]
