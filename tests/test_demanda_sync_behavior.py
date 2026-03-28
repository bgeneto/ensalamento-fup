from __future__ import annotations

from contextlib import contextmanager

from src.models.academic import Demanda
from src.models.allocation import AlocacaoSemestral
from src.models.inventory import Campus, Predio, Sala, TipoSala
from src.repositories.disciplina import DisciplinaRepository
from src.services import semester_service
from src.services.demanda_sync_service import DemandaSyncService
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


def test_delete_semester_demands_can_preserve_manual_demands(
    db_session,
    sample_semestre,
):
    manual_demand = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="FUP1001",
        nome_disciplina="Demanda Manual",
        turma_disciplina="1",
        horario_sigaa_bruto="24M12",
        origem="manual",
        sync_status="manual",
    )
    api_demand = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="FUP1002",
        nome_disciplina="Demanda API",
        turma_disciplina="1",
        horario_sigaa_bruto="35T12",
        origem="api",
        sync_status="active",
    )
    db_session.add_all([manual_demand, api_demand])
    db_session.commit()

    service = DemandaSyncService(db_session)
    result = service.delete_semester_demands(
        sample_semestre.id,
        preserve_manual_demands=True,
    )

    repo = DisciplinaRepository(db_session)
    remaining = repo.get_by_semestre(sample_semestre.id)

    assert result.success is True
    assert result.deleted_demands_count == 1
    assert result.preserved_manual_demands_count == 1
    assert [(d.codigo_disciplina, d.origem) for d in remaining] == [
        ("FUP1001", "manual")
    ]


def test_delete_semester_demands_blocks_when_any_target_demand_has_allocations(
    db_session,
    sample_semestre,
    sample_dia_semana,
    sample_horario_bloco,
):
    campus = Campus(nome="Campus Delete", descricao="Campus de teste")
    predio = Predio(nome="Predio Delete", descricao="Predio de teste", campus=campus)
    tipo_sala = TipoSala(nome="Sala Delete")
    sala = Sala(
        nome="D404",
        descricao="Sala de teste",
        predio=predio,
        tipo_sala=tipo_sala,
        capacidade=40,
        andar=4,
    )
    blocked_demand = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="FUP2001",
        nome_disciplina="Demanda Bloqueada",
        turma_disciplina="1",
        horario_sigaa_bruto="24M12",
        origem="api",
        sync_status="active",
    )
    removable_demand = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="FUP2002",
        nome_disciplina="Demanda Sem Alocacao",
        turma_disciplina="1",
        horario_sigaa_bruto="35T12",
        origem="api",
        sync_status="active",
    )
    db_session.add_all(
        [campus, predio, tipo_sala, sala, blocked_demand, removable_demand]
    )
    db_session.commit()
    db_session.refresh(sala)
    db_session.refresh(blocked_demand)

    db_session.add(
        AlocacaoSemestral(
            semestre_id=sample_semestre.id,
            demanda_id=blocked_demand.id,
            sala_id=sala.id,
            dia_semana_id=sample_dia_semana.id_sigaa,
            codigo_bloco=sample_horario_bloco.codigo_bloco,
            origem_alocacao="manual",
        )
    )
    db_session.commit()

    service = DemandaSyncService(db_session)
    result = service.delete_semester_demands(sample_semestre.id)

    repo = DisciplinaRepository(db_session)
    remaining_codes = [
        d.codigo_disciplina for d in repo.get_by_semestre(sample_semestre.id)
    ]

    assert result.success is False
    assert result.deleted_demands_count == 0
    assert result.blocked_demands_count == 1
    assert result.blocked_demands == ["FUP2001-1"]
    assert "Não é possível remover demandas com alocações salvas" in (
        result.error_message or ""
    )
    assert remaining_codes == ["FUP2001", "FUP2002"]
