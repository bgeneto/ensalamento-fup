"""
Script para investigar por que FUP0321, apesar de ser híbrida,
não foi alocada em duas salas diferentes (uma lab e uma sala comum).
"""

from sqlalchemy import text
from src.config.database import get_db_session
from src.repositories.alocacao import AlocacaoRepository
from src.services.room_scoring_service import RoomScoringService
from src.services.hybrid_discipline_service import (
    HybridDisciplineDetectionService,
    REGULAR_CLASSROOM_TYPE_ID,
)
from src.utils.sigaa_parser import SigaaScheduleParser


def main():
    DISCIPLINA_CODIGO = "FUP0321"
    TARGET_SEMESTER = "2026-1"

    with get_db_session() as session:
        parser = SigaaScheduleParser()
        alocacao_repo = AlocacaoRepository(session)
        hybrid_service = HybridDisciplineDetectionService(session)

        # 1. Buscar o semestre
        result = session.execute(
            text("SELECT id FROM semestres WHERE nome = :nome"),
            {"nome": TARGET_SEMESTER},
        ).fetchone()
        semester_id = result[0] if result else None

        if not semester_id:
            print(f"❌ Semestre {TARGET_SEMESTER} não encontrado!")
            return

        print(f"✅ Semestre {TARGET_SEMESTER} ID: {semester_id}\n")

        # 2. Buscar a demanda
        result = session.execute(
            text(
                """
                SELECT id, codigo_disciplina, nome_disciplina, turma_disciplina,
                       vagas_disciplina, horario_sigaa_bruto
                FROM demandas
                WHERE codigo_disciplina = :codigo AND semestre_id = :sem_id
            """
            ),
            {"codigo": DISCIPLINA_CODIGO, "sem_id": semester_id},
        ).fetchone()

        if not result:
            print(
                f"❌ Demanda {DISCIPLINA_CODIGO} não encontrada no semestre {TARGET_SEMESTER}!"
            )
            return

        demanda_id, codigo, nome, turma, vagas, horario = result
        print(f"{'=' * 80}")
        print(f"📚 DEMANDA {DISCIPLINA_CODIGO}")
        print(f"{'=' * 80}")
        print(f"   ID: {demanda_id}")
        print(f"   Código: {codigo}")
        print(f"   Nome: {nome}")
        print(f"   Turma: {turma}")
        print(f"   Vagas: {vagas}")
        print(f"   Horário SIGAA: {horario}")
        print()

        # Parse atomic blocks
        atomic_blocks = parser.split_to_atomic_tuples(horario)
        print(f"🕐 Blocos atômicos necessários: {atomic_blocks}")

        # Agrupar por dia
        day_names = {2: "SEG", 3: "TER", 4: "QUA", 5: "QUI", 6: "SEX", 7: "SAB"}
        blocks_by_day = {}
        for block_code, day_id in atomic_blocks:
            if day_id not in blocks_by_day:
                blocks_by_day[day_id] = []
            blocks_by_day[day_id].append(block_code)

        print("\n📅 Blocos agrupados por dia:")
        for day_id in sorted(blocks_by_day.keys()):
            print(
                f"   {day_names.get(day_id, f'DIA{day_id}')}: {blocks_by_day[day_id]}"
            )
        print()

        # 3. Verificar detecção de híbrida
        print(f"{'=' * 80}")
        print("🔬 ANÁLISE DE DETECÇÃO HÍBRIDA")
        print(f"{'=' * 80}\n")

        # Buscar semestre usado para detecção (mais recente com alocações)
        detection_semester_id = alocacao_repo.get_most_recent_semester_with_allocations(
            exclude_semester_id=semester_id
        )
        if not detection_semester_id:
            detection_semester_id = (
                alocacao_repo.get_most_recent_semester_with_allocations()
            )

        if detection_semester_id:
            detection_sem_name = session.execute(
                text("SELECT nome FROM semestres WHERE id = :id"),
                {"id": detection_semester_id},
            ).fetchone()
            print(
                f"📊 Semestre usado para detecção: {detection_sem_name[0] if detection_sem_name else detection_semester_id}"
            )
        else:
            print("⚠️ Nenhum semestre com alocações encontrado para detecção!")
            return

        # Executar detecção
        detection_result = hybrid_service.detect_hybrid_disciplines(
            detection_semester_id
        )

        print("\n🔍 Resultado da detecção:")
        print(
            f"   Total de disciplinas híbridas detectadas: {detection_result.detected_count}"
        )

        is_hybrid = DISCIPLINA_CODIGO in detection_result.hybrid_disciplines
        print(
            f"   {DISCIPLINA_CODIGO} é híbrida? {'✅ SIM' if is_hybrid else '❌ NÃO'}"
        )

        if is_hybrid:
            info = detection_result.details.get(DISCIPLINA_CODIGO)
            if info:
                print("\n   📋 Detalhes da disciplina híbrida:")
                print(
                    f"      Lab days: {info.lab_days} ({[day_names.get(d, f'DIA{d}') for d in info.lab_days]})"
                )
                print(
                    f"      Classroom days: {info.classroom_days} ({[day_names.get(d, f'DIA{d}') for d in info.classroom_days]})"
                )
                print(f"      Lab room types: {info.lab_room_types}")
                print(f"      Historical lab rooms: {info.historical_lab_rooms}")
        else:
            # Investigar por que NÃO foi detectada
            print("\n   🔍 Investigando por que NÃO foi detectada como híbrida...")

            # Verificar alocações no semestre de detecção
            hist_allocs = session.execute(
                text(
                    """
                    SELECT DISTINCT s.id, s.nome, s.tipo_sala_id, ts.nome as tipo_sala_nome
                    FROM alocacoes_semestrais a
                    JOIN demandas d ON a.demanda_id = d.id
                    JOIN salas s ON a.sala_id = s.id
                    LEFT JOIN tipos_sala ts ON s.tipo_sala_id = ts.id
                    WHERE d.codigo_disciplina = :codigo
                      AND a.semestre_id = :sem_id
                """
                ),
                {"codigo": DISCIPLINA_CODIGO, "sem_id": detection_semester_id},
            ).fetchall()

            if hist_allocs:
                print(
                    f"   Salas usadas no semestre de detecção ({detection_sem_name[0] if detection_sem_name else detection_semester_id}):"
                )
                for sala_id, sala_nome, tipo_sala_id, tipo_sala_nome in hist_allocs:
                    is_lab = tipo_sala_id != REGULAR_CLASSROOM_TYPE_ID
                    print(
                        f"      - {sala_nome} (tipo: {tipo_sala_nome}, ID tipo: {tipo_sala_id}) {'🧪 LAB' if is_lab else '🏫 SALA'}"
                    )

                # Critérios de detecção:
                unique_rooms = len(set([r[0] for r in hist_allocs]))
                has_lab = any(r[2] != REGULAR_CLASSROOM_TYPE_ID for r in hist_allocs)

                print("\n   📋 Critérios de detecção híbrida:")
                print(
                    f"      - 2+ salas diferentes? {'✅' if unique_rooms >= 2 else '❌'} ({unique_rooms} sala(s))"
                )
                print(
                    f"      - Pelo menos 1 lab/sala especial? {'✅' if has_lab else '❌'}"
                )
            else:
                print("   ❌ Sem alocações encontradas no semestre de detecção!")

        # 4. Verificar alocações atuais
        print(f"\n\n{'=' * 80}")
        print(f"📍 ALOCAÇÕES ATUAIS ({TARGET_SEMESTER})")
        print(f"{'=' * 80}\n")

        current_allocs = session.execute(
            text(
                """
                SELECT DISTINCT s.id, s.nome, s.capacidade, s.tipo_sala_id, 
                       ts.nome as tipo_sala_nome, a.dia_semana_id
                FROM alocacoes_semestrais a
                JOIN salas s ON a.sala_id = s.id
                LEFT JOIN tipos_sala ts ON s.tipo_sala_id = ts.id
                WHERE a.demanda_id = :demanda_id
                ORDER BY a.dia_semana_id
            """
            ),
            {"demanda_id": demanda_id},
        ).fetchall()

        if current_allocs:
            print(f"Salas alocadas para {DISCIPLINA_CODIGO}:")

            # Agrupar por sala
            rooms_used = {}
            for sala_id, sala_nome, cap, tipo_id, tipo_nome, dia in current_allocs:
                if sala_id not in rooms_used:
                    rooms_used[sala_id] = {
                        "nome": sala_nome,
                        "capacidade": cap,
                        "tipo_id": tipo_id,
                        "tipo_nome": tipo_nome,
                        "dias": [],
                    }
                rooms_used[sala_id]["dias"].append(dia)

            for sala_id, info in rooms_used.items():
                is_lab = info["tipo_id"] != REGULAR_CLASSROOM_TYPE_ID
                dias_str = ", ".join(
                    [day_names.get(d, f"DIA{d}") for d in info["dias"]]
                )
                print(f"\n   🏢 {info['nome']} (Cap: {info['capacidade']})")
                print(
                    f"      Tipo: {info['tipo_nome']} (ID: {info['tipo_id']}) {'🧪 LAB' if is_lab else '🏫 SALA'}"
                )
                print(f"      Dias alocados: {dias_str}")

            # Verificar se tem apenas 1 sala (problema!)
            if len(rooms_used) == 1:
                print("\n   ⚠️ PROBLEMA: Apenas 1 sala alocada para disciplina híbrida!")
                print("      Esperado: 2 salas (1 lab + 1 sala de aula)")
        else:
            print(f"❌ {DISCIPLINA_CODIGO} NÃO foi alocada!")

        # 5. Histórico de alocações por dia
        print(f"\n\n{'=' * 80}")
        print("📜 HISTÓRICO DE ALOCAÇÕES POR DIA")
        print(f"{'=' * 80}\n")

        for day_id in sorted(blocks_by_day.keys()):
            day_name = day_names.get(day_id, f"DIA{day_id}")
            print(f"\n{'─' * 60}")
            print(f"📅 {day_name} (ID: {day_id})")
            print(f"{'─' * 60}")

            hist_by_day = session.execute(
                text(
                    """
                    SELECT s.id, s.nome, s.tipo_sala_id, ts.nome as tipo_nome,
                           sem.nome as semestre, COUNT(*) as blocos
                    FROM alocacoes_semestrais a
                    JOIN demandas d ON a.demanda_id = d.id
                    JOIN salas s ON a.sala_id = s.id
                    LEFT JOIN tipos_sala ts ON s.tipo_sala_id = ts.id
                    JOIN semestres sem ON a.semestre_id = sem.id
                    WHERE d.codigo_disciplina = :codigo
                      AND a.dia_semana_id = :dia
                      AND a.semestre_id != :current_sem
                    GROUP BY s.id, s.nome, s.tipo_sala_id, ts.nome, sem.nome
                    ORDER BY sem.nome DESC
                """
                ),
                {
                    "codigo": DISCIPLINA_CODIGO,
                    "dia": day_id,
                    "current_sem": semester_id,
                },
            ).fetchall()

            if hist_by_day:
                for (
                    sala_id,
                    sala_nome,
                    tipo_id,
                    tipo_nome,
                    semestre,
                    blocos,
                ) in hist_by_day:
                    is_lab = tipo_id != REGULAR_CLASSROOM_TYPE_ID
                    print(
                        f"   {semestre}: {sala_nome} ({tipo_nome}) - {blocos} blocos {'🧪' if is_lab else '🏫'}"
                    )
            else:
                print("   Sem histórico para este dia.")

        # 6. Análise de scoring por dia
        print(f"\n\n{'=' * 80}")
        print("🎯 ANÁLISE DE SCORING POR DIA")
        print(f"{'=' * 80}\n")

        scoring_service = RoomScoringService(session)
        scoring_service.set_hybrid_detection_service(hybrid_service)

        for day_id in sorted(blocks_by_day.keys()):
            day_name = day_names.get(day_id, f"DIA{day_id}")
            print(f"\n{'─' * 60}")
            print(f"📅 {day_name} - Top 5 salas por pontuação")
            print(f"{'─' * 60}")

            # Criar BlockGroup para este dia
            from src.services.room_scoring_service import BlockGroup

            block_group = BlockGroup(
                day_id=day_id,
                day_name=day_name,
                blocks=blocks_by_day[day_id],
            )

            # Obter scores
            scores = scoring_service.score_rooms_for_block_group(
                demanda_id, block_group, semester_id
            )

            # Mostrar top 5
            for i, score in enumerate(scores[:5]):
                conflict_str = "⚠️ CONFLITO" if score.has_conflict else "✅"
                is_lab = score.room_type != "Sala de Aula"

                print(
                    f"\n   {i + 1}. {score.room_name} ({score.room_type}) {conflict_str}"
                )
                print(f"      Score Total: {score.score}")
                print(f"      - Capacidade: {score.breakdown.capacity_points} pts")
                print(f"      - Hard rules: {score.breakdown.hard_rules_points} pts")
                print(
                    f"      - Preferências: {score.breakdown.soft_preference_points} pts"
                )
                print(
                    f"      - Histórico: {score.breakdown.historical_frequency_points} pts ({score.breakdown.historical_allocations} alocações)"
                )
                print(
                    f"      - Híbrido: {score.breakdown.hybrid_bonus_points} pts {'(match!)' if score.breakdown.hybrid_room_type_match else ''}"
                )

            # Verificar se é esperado lab ou sala
            if is_hybrid:
                info = detection_result.details.get(DISCIPLINA_CODIGO)
                if info:
                    expected = (
                        "🧪 LAB"
                        if day_id in info.lab_days
                        else (
                            "🏫 SALA"
                            if day_id in info.classroom_days
                            else "❓ INDEFINIDO"
                        )
                    )
                    print(f"\n   📋 Tipo esperado para este dia: {expected}")

        # 7. Conclusão
        print(f"\n\n{'=' * 80}")
        print("🎯 CONCLUSÃO DA INVESTIGAÇÃO")
        print(f"{'=' * 80}\n")

        if not is_hybrid:
            print(
                "❌ PROBLEMA IDENTIFICADO: Disciplina NÃO foi detectada como híbrida!"
            )
            print("\n   Possíveis causas:")
            print("   1. No semestre de detecção, a disciplina usou apenas 1 sala")
            print(
                "   2. No semestre de detecção, só usou salas de aula (tipo_sala_id = 2)"
            )
            print("   3. Problema na query de detecção")
            print("\n   Recomendação: Verificar alocações do semestre de detecção")
        elif len(rooms_used) == 1:
            print(
                "❌ PROBLEMA IDENTIFICADO: Híbrida detectada, mas só alocada em 1 sala!"
            )
            print("\n   Possíveis causas:")
            print("   1. Conflitos nas salas alternativas")
            print("   2. Pontuação histórica muito alta para uma única sala")
            print("   3. Alocação não está usando modo parcial (partial_allocation)")
            print("   4. Bonus híbrido não está sendo aplicado corretamente")
            print(
                "\n   Recomendação: Verificar se execute_autonomous_allocation_partial foi usado"
            )
        else:
            print("✅ Disciplina híbrida alocada em múltiplas salas corretamente!")


if __name__ == "__main__":
    main()
