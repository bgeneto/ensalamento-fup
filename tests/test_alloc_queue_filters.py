from datetime import datetime

from pages.components.alloc_queue import _apply_filters, _check_rule_warnings
from src.schemas.academic import DemandaRead
from src.utils.demand_filter_options import build_demand_filter_options


def _make_demanda(
    codigo_disciplina: str,
    nome_disciplina: str,
    turma_disciplina: str,
    professores_disciplina: str = "",
    codigo_curso: str = "",
) -> DemandaRead:
    timestamp = datetime(2026, 3, 27, 12, 0, 0)
    return DemandaRead(
        id=1,
        semestre_id=1,
        codigo_disciplina=codigo_disciplina,
        nome_disciplina=nome_disciplina,
        professores_disciplina=professores_disciplina,
        turma_disciplina=turma_disciplina,
        vagas_disciplina=40,
        horario_sigaa_bruto="24M12",
        codigo_curso=codigo_curso,
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_apply_filters_can_filter_multiple_offers_by_discipline_code():
    demandas = [
        _make_demanda("FUP0001", "Introducao", "A"),
        _make_demanda("FUP0001", "Introducao", "B"),
        _make_demanda("FUP0002", "Metodologia", "A"),
    ]

    filtered = _apply_filters(
        demandas,
        search_text="",
        professor_filter="",
        course_filter="",
        discipline_filter="FUP0001",
    )

    assert len(filtered) == 2
    assert [demanda.turma_disciplina for demanda in filtered] == ["A", "B"]


def test_apply_filters_supports_dto_and_dict_demands_with_combined_filters():
    dto_demanda = _make_demanda(
        "MAT0001",
        "Calculo I",
        "A",
        professores_disciplina="Ana Souza",
        codigo_curso="MAT",
    )
    dict_demanda = {
        "codigo_disciplina": "BIO0001",
        "nome_disciplina": "Biologia",
        "professores_disciplina": "Carlos Lima",
        "codigo_curso": "BIO",
    }

    filtered = _apply_filters(
        [dto_demanda, dict_demanda],
        search_text="calc",
        professor_filter="Ana",
        course_filter="MAT",
        discipline_filter="MAT0001",
    )

    assert filtered == [dto_demanda]


def test_apply_filters_can_filter_by_professor_name_and_ignore_all_sentinel():
    demandas = [
        _make_demanda(
            "FUP0001",
            "Introducao",
            "A",
            professores_disciplina="Ana Souza",
        ),
        _make_demanda(
            "FUP0002",
            "Metodologia",
            "A",
            professores_disciplina="Carlos Lima",
        ),
    ]

    filtered_by_professor = _apply_filters(
        demandas,
        search_text="",
        professor_filter="Ana Souza",
        course_filter="",
        discipline_filter="all",
    )
    filtered_with_all = _apply_filters(
        demandas,
        search_text="",
        professor_filter="all",
        course_filter="",
        discipline_filter="all",
    )

    assert filtered_by_professor == [demandas[0]]
    assert filtered_with_all == demandas


def test_build_demand_filter_options_keeps_professors_from_duplicate_disciplines():
    demandas = [
        _make_demanda(
            "FUP0001",
            "Introducao",
            "A",
            professores_disciplina="Ana Souza",
        ),
        _make_demanda(
            "FUP0001",
            "Introducao",
            "B",
            professores_disciplina="Carlos Lima / Maria Clara",
        ),
    ]

    _, professor_options = build_demand_filter_options(demandas)

    assert professor_options == {
        "all": "Todos os professores",
        "Ana Souza": "Ana Souza",
        "Carlos Lima": "Carlos Lima",
        "Maria Clara": "Maria Clara",
    }


def test_check_rule_warnings_prefers_actual_mixed_hybrid_allocation(monkeypatch):
    demanda = _make_demanda("FUP0363", "Eletromagnetismo em Ciencias", "1")

    monkeypatch.setattr(
        "pages.components.alloc_queue.get_hybrid_status_for_demand",
        lambda demanda, semester_id: {
            "is_hybrid": True,
            "current_slot_requirements": {"4_T": "classroom"},
            "all_slot_requirements": {
                "4_N": "lab",
                "4_T": "classroom",
                "2_N": "lab",
            },
        },
    )

    warnings = _check_rule_warnings(
        demanda,
        semester_id=5,
        allocation_info={
            "has_classroom_room": True,
            "has_laboratory_room": True,
            "has_specialized_room": True,
        },
    )

    assert warnings == ["Disciplina HÍBRIDA detectada 🧪"]


def test_check_rule_warnings_marks_partial_hybrid_history_coverage(monkeypatch):
    demanda = _make_demanda("FUP0363", "Eletromagnetismo em Ciencias", "1")

    monkeypatch.setattr(
        "pages.components.alloc_queue.get_hybrid_status_for_demand",
        lambda demanda, semester_id: {
            "is_hybrid": True,
            "current_slot_requirements": {"4_T": "classroom"},
            "all_slot_requirements": {
                "4_N": "lab",
                "4_T": "classroom",
                "2_N": "lab",
            },
        },
    )

    warnings = _check_rule_warnings(demanda, semester_id=5)

    assert warnings == ["Disciplina HÍBRIDA detectada 🧪"]
