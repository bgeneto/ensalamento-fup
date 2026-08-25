from pages.components import allocation_assistant
from src.models.academic import Demanda, Semestre
from src.models.allocation import (
    AlocacaoSemestral,
    Regra,
    TIPO_REGRA_DISCIPLINA_SEM_SALA,
)
from src.models.horario import DiaSemana, HorarioBloco
from src.models.inventory import Campus, Predio, Sala, TipoSala
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.regra import RegraRepository
from src.services.manual_allocation_service import ManualAllocationService


def test_allocate_demand_partial_preserves_explicit_day_block_pairs(
    db_session,
    sample_semestre,
    sample_sala,
):
    db_session.add_all(
        [
            DiaSemana(id_sigaa=2, nome="SEG"),
            DiaSemana(id_sigaa=4, nome="QUA"),
            HorarioBloco(
                codigo_bloco="N1",
                turno="N",
                horario_inicio="19:00",
                horario_fim="19:50",
            ),
            HorarioBloco(
                codigo_bloco="N2",
                turno="N",
                horario_inicio="19:50",
                horario_fim="20:40",
            ),
        ]
    )
    demanda = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="COMP099",
        nome_disciplina="Seleção Atômica",
        professores_disciplina="Prof. Teste",
        turma_disciplina="A",
        codigo_curso="COMP",
        horario_sigaa_bruto="24N12",
    )
    db_session.add(demanda)
    db_session.commit()
    db_session.refresh(demanda)

    service = ManualAllocationService(db_session)
    result = service.allocate_demand_partial(
        demanda.id,
        sample_sala.id,
        selected_atomic_blocks=[("N1", 2), ("N2", 4)],
    )

    allocations = (
        db_session.query(AlocacaoSemestral)
        .filter_by(demanda_id=demanda.id)
        .order_by(
            AlocacaoSemestral.dia_semana_id,
            AlocacaoSemestral.codigo_bloco,
        )
        .all()
    )

    assert result.success is True
    assert result.allocated_blocks == ["2N1", "4N2"]
    assert result.remaining_blocks == ["2N2", "4N1"]
    assert [
        (allocation.codigo_bloco, allocation.dia_semana_id)
        for allocation in allocations
    ] == [("N1", 2), ("N2", 4)]


def test_selected_atomic_block_pairs_preserve_day_relationship():
    selected_groups = [
        {"day_id": 2, "blocks": ["N1"]},
        {"day_id": 4, "blocks": ["N2"]},
    ]

    assert allocation_assistant._selected_atomic_block_pairs(selected_groups) == [
        ("N1", 2),
        ("N2", 4),
    ]


def test_clear_allocation_selection_state_removes_widget_and_legacy_keys(
    monkeypatch,
):
    session_state = {
        "selected_atomic_blocks_17": {"2_N1": True},
        "selected_block_groups_17": {"2_N": True},
        "atom_17_2_N1": True,
        "atom_17_4_N2": False,
        "toggle_group_17_2_N": True,
        "block_group_17_2_N": True,
        "manual_room_select_partial_17": 3,
        "atom_18_2_N1": True,
        "unrelated": "keep",
    }
    monkeypatch.setattr(allocation_assistant.st, "session_state", session_state)

    allocation_assistant._clear_allocation_selection_state(17)

    assert session_state == {
        "manual_room_select_partial_17": 3,
        "atom_18_2_N1": True,
        "unrelated": "keep",
    }


def test_deallocate_semester_removes_only_current_semester_allocations(
    db_session,
    sample_semestre,
    sample_dia_semana,
    sample_horario_bloco,
):
    other_semester = Semestre(nome="2024.2", status=0)
    campus = Campus(nome="Campus Teste", descricao="Campus de teste")
    predio = Predio(nome="Predio Teste", descricao="Predio de teste", campus=campus)
    tipo_sala = TipoSala(nome="Sala Teste")
    sala = Sala(
        nome="A101",
        descricao="Sala de teste",
        predio=predio,
        tipo_sala=tipo_sala,
        capacidade=30,
        andar=1,
    )
    db_session.add_all([other_semester, campus, predio, tipo_sala, sala])
    db_session.commit()
    db_session.refresh(other_semester)
    db_session.refresh(sala)

    first_demand = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="COMP001",
        nome_disciplina="Programacao I",
        professores_disciplina="Prof. Joao",
        turma_disciplina="A",
        codigo_curso="COMP",
        horario_sigaa_bruto="24M12",
    )
    extra_demand = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="COMP002",
        nome_disciplina="Programacao II",
        professores_disciplina="Prof. Maria",
        turma_disciplina="B",
        codigo_curso="COMP",
        horario_sigaa_bruto="24M34",
    )
    other_semester_demand = Demanda(
        semestre_id=other_semester.id,
        codigo_disciplina="COMP003",
        nome_disciplina="Estruturas",
        professores_disciplina="Prof. Jose",
        turma_disciplina="A",
        codigo_curso="COMP",
        horario_sigaa_bruto="24M12",
    )
    second_block = HorarioBloco(
        codigo_bloco="M2",
        turno="M",
        horario_inicio="08:55",
        horario_fim="09:50",
    )
    db_session.add_all(
        [first_demand, extra_demand, other_semester_demand, second_block]
    )
    db_session.commit()
    db_session.refresh(first_demand)
    db_session.refresh(extra_demand)
    db_session.refresh(other_semester_demand)

    db_session.add_all(
        [
            AlocacaoSemestral(
                semestre_id=sample_semestre.id,
                demanda_id=first_demand.id,
                sala_id=sala.id,
                dia_semana_id=sample_dia_semana.id_sigaa,
                codigo_bloco=sample_horario_bloco.codigo_bloco,
                origem_alocacao="autonoma",
            ),
            AlocacaoSemestral(
                semestre_id=sample_semestre.id,
                demanda_id=extra_demand.id,
                sala_id=sala.id,
                dia_semana_id=sample_dia_semana.id_sigaa,
                codigo_bloco=second_block.codigo_bloco,
                origem_alocacao="autonoma",
            ),
            AlocacaoSemestral(
                semestre_id=other_semester.id,
                demanda_id=other_semester_demand.id,
                sala_id=sala.id,
                dia_semana_id=sample_dia_semana.id_sigaa,
                codigo_bloco=sample_horario_bloco.codigo_bloco,
                origem_alocacao="manual",
            ),
        ]
    )
    db_session.commit()

    service = ManualAllocationService(db_session)
    result = service.deallocate_semester(sample_semestre.id)

    assert result.success is True
    assert result.deleted_allocations_count == 2
    assert result.affected_demands_count == 2
    assert (
        db_session.query(AlocacaoSemestral)
        .filter_by(semestre_id=sample_semestre.id)
        .count()
        == 0
    )
    assert (
        db_session.query(AlocacaoSemestral)
        .filter_by(semestre_id=other_semester.id)
        .count()
        == 1
    )


def test_deallocate_semester_can_preserve_manual_allocations(
    db_session,
    sample_semestre,
    sample_dia_semana,
    sample_horario_bloco,
):
    campus = Campus(nome="Campus Mistura", descricao="Campus de teste")
    predio = Predio(nome="Predio Mistura", descricao="Predio de teste", campus=campus)
    tipo_sala = TipoSala(nome="Sala Mistura")
    sala = Sala(
        nome="B202",
        descricao="Sala de teste",
        predio=predio,
        tipo_sala=tipo_sala,
        capacidade=40,
        andar=2,
    )
    db_session.add_all([campus, predio, tipo_sala, sala])
    db_session.commit()
    db_session.refresh(sala)

    autonomous_demand = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="COMP010",
        nome_disciplina="Algoritmos",
        professores_disciplina="Prof. Ana",
        turma_disciplina="A",
        codigo_curso="COMP",
        horario_sigaa_bruto="24M12",
    )
    manual_demand = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="COMP011",
        nome_disciplina="Banco de Dados",
        professores_disciplina="Prof. Bruno",
        turma_disciplina="B",
        codigo_curso="COMP",
        horario_sigaa_bruto="24M34",
    )
    second_block = HorarioBloco(
        codigo_bloco="M2",
        turno="M",
        horario_inicio="08:55",
        horario_fim="09:50",
    )
    db_session.add_all([autonomous_demand, manual_demand, second_block])
    db_session.commit()
    db_session.refresh(autonomous_demand)
    db_session.refresh(manual_demand)

    db_session.add_all(
        [
            AlocacaoSemestral(
                semestre_id=sample_semestre.id,
                demanda_id=autonomous_demand.id,
                sala_id=sala.id,
                dia_semana_id=sample_dia_semana.id_sigaa,
                codigo_bloco=sample_horario_bloco.codigo_bloco,
                origem_alocacao="autonoma",
            ),
            AlocacaoSemestral(
                semestre_id=sample_semestre.id,
                demanda_id=manual_demand.id,
                sala_id=sala.id,
                dia_semana_id=sample_dia_semana.id_sigaa,
                codigo_bloco=second_block.codigo_bloco,
                origem_alocacao="manual",
            ),
        ]
    )
    db_session.commit()

    service = ManualAllocationService(db_session)
    result = service.deallocate_semester(
        sample_semestre.id, preserve_manual_allocations=True
    )

    remaining_allocations = (
        db_session.query(AlocacaoSemestral)
        .filter_by(semestre_id=sample_semestre.id)
        .order_by(AlocacaoSemestral.id)
        .all()
    )

    assert result.success is True
    assert result.deleted_allocations_count == 1
    assert result.affected_demands_count == 1
    assert result.preserved_manual_allocations_count == 1
    assert result.preserved_manual_demands_count == 1
    assert len(remaining_allocations) == 1
    assert remaining_allocations[0].origem_alocacao == "manual"


def test_deallocate_semester_returns_error_when_no_allocations_exist(
    db_session,
    sample_semestre,
):
    service = ManualAllocationService(db_session)

    result = service.deallocate_semester(sample_semestre.id)

    assert result.success is False
    assert result.deleted_allocations_count == 0
    assert "não possui alocações" in (result.error_message or "")


def test_get_all_demands_uses_visible_allocation_scope(
    db_session,
    sample_semestre,
    sample_dia_semana,
    sample_horario_bloco,
):
    campus = Campus(nome="Campus Visivel", descricao="Campus de teste")
    predio = Predio(nome="Predio Visivel", descricao="Predio de teste", campus=campus)
    tipo_sala = TipoSala(nome="Sala Visivel")
    sala = Sala(
        nome="C303",
        descricao="Sala de teste",
        predio=predio,
        tipo_sala=tipo_sala,
        capacidade=35,
        andar=3,
    )
    db_session.add_all([campus, predio, tipo_sala, sala])
    db_session.commit()
    db_session.refresh(sala)

    active_demand = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="COMP100",
        nome_disciplina="Demanda Ativa",
        professores_disciplina="Prof. A",
        turma_disciplina="A",
        codigo_curso="COMP",
        horario_sigaa_bruto="24M12",
        sync_status="active",
        origem="api",
    )
    removed_hidden_demand = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="COMP200",
        nome_disciplina="Demanda Removida",
        professores_disciplina="Prof. B",
        turma_disciplina="B",
        codigo_curso="COMP",
        horario_sigaa_bruto="24M12",
        sync_status="removed_in_api",
        origem="api",
    )
    removed_allocated_demand = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="COMP300",
        nome_disciplina="Demanda Removida Com Alocacao",
        professores_disciplina="Prof. C",
        turma_disciplina="C",
        codigo_curso="COMP",
        horario_sigaa_bruto="24M12",
        sync_status="removed_in_api",
        origem="api",
    )
    db_session.add_all([active_demand, removed_hidden_demand, removed_allocated_demand])
    db_session.commit()
    db_session.refresh(active_demand)
    db_session.refresh(removed_hidden_demand)
    db_session.refresh(removed_allocated_demand)

    db_session.add(
        AlocacaoSemestral(
            semestre_id=sample_semestre.id,
            demanda_id=removed_allocated_demand.id,
            sala_id=sala.id,
            dia_semana_id=sample_dia_semana.id_sigaa,
            codigo_bloco=sample_horario_bloco.codigo_bloco,
            origem_alocacao="autonoma",
        )
    )
    db_session.commit()

    service = ManualAllocationService(db_session)

    all_visible_demands = service.get_all_demands(sample_semestre.id)
    progress = service.get_allocation_progress(sample_semestre.id)

    visible_ids = {demanda.id for demanda in all_visible_demands}

    assert visible_ids == {active_demand.id, removed_allocated_demand.id}
    assert removed_hidden_demand.id not in visible_ids
    assert progress["total_demands"] == len(all_visible_demands)


def _add_sem_sala_rule(db_session, codigo_disciplina: str) -> Regra:
    regra = Regra(
        descricao=f"Disciplina {codigo_disciplina} não requer sala",
        tipo_regra=TIPO_REGRA_DISCIPLINA_SEM_SALA,
        config_json=f'{{"codigo_disciplina": "{codigo_disciplina}"}}',
        prioridade=0,
    )
    db_session.add(regra)
    db_session.commit()
    db_session.refresh(regra)
    return regra


def test_get_codigos_sem_sala_parses_json_and_ignores_invalid_config(db_session):
    db_session.add_all(
        [
            Regra(
                descricao="Estágio sem sala",
                tipo_regra=TIPO_REGRA_DISCIPLINA_SEM_SALA,
                config_json='{"codigo_disciplina": "FUP0999"}',
                prioridade=0,
            ),
            Regra(
                descricao="JSON inválido",
                tipo_regra=TIPO_REGRA_DISCIPLINA_SEM_SALA,
                config_json="{not-json",
                prioridade=0,
            ),
            Regra(
                descricao="Sala específica",
                tipo_regra="DISCIPLINA_SALA",
                config_json='{"codigo_disciplina": "FUP0001", "sala_id": 1}',
                prioridade=0,
            ),
        ]
    )
    db_session.commit()

    codes = RegraRepository(db_session).get_codigos_sem_sala()

    assert codes == {"FUP0999"}


def test_sem_sala_demands_are_excluded_from_unallocated_and_progress(
    db_session,
    sample_semestre,
):
    regular = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="COMP100",
        nome_disciplina="Demanda Regular",
        professores_disciplina="Prof. A",
        turma_disciplina="A",
        codigo_curso="COMP",
        horario_sigaa_bruto="24M12",
        sync_status="active",
        origem="api",
    )
    sem_sala = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="FUP0999",
        nome_disciplina="Estágio Supervisionado",
        professores_disciplina="Prof. B",
        turma_disciplina="A",
        codigo_curso="COMP",
        horario_sigaa_bruto="24M12",
        sync_status="active",
        origem="api",
    )
    db_session.add_all([regular, sem_sala])
    db_session.commit()
    db_session.refresh(regular)
    db_session.refresh(sem_sala)
    _add_sem_sala_rule(db_session, "FUP0999")

    service = ManualAllocationService(db_session)
    disc_repo = DisciplinaRepository(db_session)

    unallocated_ids = {
        demanda.id for demanda in service.get_unallocated_demands(sample_semestre.id)
    }
    all_ids = {demanda.id for demanda in service.get_all_demands(sample_semestre.id)}
    progress = service.get_allocation_progress(sample_semestre.id)

    assert unallocated_ids == {regular.id}
    assert all_ids == {regular.id}
    assert sem_sala.id not in unallocated_ids
    assert progress["total_demands"] == 1
    assert progress["unallocated_demands"] == 1
    assert {d.id for d in disc_repo.get_allocatable(sample_semestre.id)} == {regular.id}
    assert {d.id for d in disc_repo.get_skip_allocation(sample_semestre.id)} == {
        sem_sala.id
    }


def test_allocate_demand_rejects_sem_sala_discipline(
    db_session,
    sample_semestre,
    sample_sala,
):
    demanda = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="FUP0888",
        nome_disciplina="TCC",
        professores_disciplina="Prof. C",
        turma_disciplina="A",
        codigo_curso="COMP",
        horario_sigaa_bruto="2M1",
        sync_status="active",
        origem="api",
    )
    db_session.add(demanda)
    db_session.commit()
    db_session.refresh(demanda)
    _add_sem_sala_rule(db_session, "FUP0888")

    service = ManualAllocationService(db_session)
    result = service.allocate_demand(demanda.id, sample_sala.id)
    partial = service.allocate_demand_partial(
        demanda.id,
        sample_sala.id,
        selected_atomic_blocks=[("M1", 2)],
    )

    assert result.success is False
    assert "não requer sala" in (result.error_message or "")
    assert partial.success is False
    assert "não requer sala" in partial.message
    assert (
        db_session.query(AlocacaoSemestral)
        .filter_by(demanda_id=demanda.id)
        .count()
        == 0
    )


def test_sem_sala_leftover_allocation_stays_visible_for_deallocation(
    db_session,
    sample_semestre,
    sample_sala,
    sample_dia_semana,
    sample_horario_bloco,
):
    extra_sala = Sala(
        nome="A102",
        predio_id=sample_sala.predio_id,
        tipo_sala_id=sample_sala.tipo_sala_id,
        capacidade=30,
        andar=1,
    )
    db_session.add(extra_sala)
    db_session.commit()
    db_session.refresh(extra_sala)
    leftover = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="FUP0777",
        nome_disciplina="Estágio com alocação residual",
        professores_disciplina="Prof. D",
        turma_disciplina="A",
        codigo_curso="COMP",
        horario_sigaa_bruto="2M1",
        sync_status="active",
        origem="api",
    )
    partial_leftover = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="FUP0777",
        nome_disciplina="Estágio parcial residual",
        professores_disciplina="Prof. D",
        turma_disciplina="B",
        codigo_curso="COMP",
        horario_sigaa_bruto="24M12",
        sync_status="active",
        origem="api",
    )
    pending_regular = Demanda(
        semestre_id=sample_semestre.id,
        codigo_disciplina="COMP100",
        nome_disciplina="Demanda Regular",
        professores_disciplina="Prof. A",
        turma_disciplina="A",
        codigo_curso="COMP",
        horario_sigaa_bruto="2M1",
        sync_status="active",
        origem="api",
    )
    db_session.add_all([leftover, partial_leftover, pending_regular])
    db_session.commit()
    db_session.refresh(leftover)
    db_session.refresh(partial_leftover)
    db_session.refresh(pending_regular)

    db_session.add_all(
        [
            AlocacaoSemestral(
                semestre_id=sample_semestre.id,
                demanda_id=leftover.id,
                sala_id=sample_sala.id,
                dia_semana_id=sample_dia_semana.id_sigaa,
                codigo_bloco=sample_horario_bloco.codigo_bloco,
                origem_alocacao="autonoma",
            ),
            AlocacaoSemestral(
                semestre_id=sample_semestre.id,
                demanda_id=partial_leftover.id,
                sala_id=extra_sala.id,
                dia_semana_id=sample_dia_semana.id_sigaa,
                codigo_bloco=sample_horario_bloco.codigo_bloco,
                origem_alocacao="autonoma",
            ),
        ]
    )
    db_session.commit()
    _add_sem_sala_rule(db_session, "FUP0777")

    service = ManualAllocationService(db_session)
    unallocated_ids = {
        demanda.id for demanda in service.get_unallocated_demands(sample_semestre.id)
    }
    allocated_ids = {
        demanda.id for demanda in service.get_allocated_demands(sample_semestre.id)
    }
    all_ids = {demanda.id for demanda in service.get_all_demands(sample_semestre.id)}
    progress = service.get_allocation_progress(sample_semestre.id)

    assert leftover.id not in unallocated_ids
    assert leftover.id in allocated_ids
    assert leftover.id in all_ids
    assert partial_leftover.id not in unallocated_ids
    assert partial_leftover.id not in allocated_ids
    assert partial_leftover.id in all_ids
    assert pending_regular.id in unallocated_ids
    assert progress["total_demands"] == 1
    assert progress["unallocated_demands"] == 1
    assert progress["allocated_demands"] == 0
