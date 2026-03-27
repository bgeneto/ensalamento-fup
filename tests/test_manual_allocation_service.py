from src.models.academic import Demanda, Semestre
from src.models.allocation import AlocacaoSemestral
from src.models.horario import HorarioBloco
from src.models.inventory import Campus, Predio, Sala, TipoSala
from src.services.manual_allocation_service import ManualAllocationService


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
