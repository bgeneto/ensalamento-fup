"""
Script para investigar por que FUP0408 não foi alocada nas salas com histórico.
"""

from sqlalchemy import text
from src.config.database import get_db_session
from src.utils.sigaa_parser import SigaaScheduleParser


def main():
    with get_db_session() as session:
        parser = SigaaScheduleParser()

        # 1. Buscar a demanda FUP0408 no semestre 2026-1
        result = session.execute(
            text("SELECT id FROM semestres WHERE nome = '2026-1'")
        ).fetchone()
        semester_id = result[0] if result else None

        if not semester_id:
            print("❌ Semestre 2026-1 não encontrado!")
            return

        print(f"✅ Semestre 2026-1 ID: {semester_id}\n")

        # Buscar demanda FUP0408
        result = session.execute(
            text(
                """
                SELECT id, codigo_disciplina, nome_disciplina, turma_disciplina,
                       vagas_disciplina, horario_sigaa_bruto
                FROM demandas
                WHERE codigo_disciplina = 'FUP0408' AND semestre_id = :sem_id
            """
            ),
            {"sem_id": semester_id},
        ).fetchone()

        if not result:
            print("❌ Demanda FUP0408 não encontrada no semestre 2026-1!")
            return

        demanda_id, codigo, nome, turma, vagas, horario = result
        print("📚 Demanda FUP0408:")
        print(f"   ID: {demanda_id}")
        print(f"   Código: {codigo}")
        print(f"   Nome: {nome}")
        print(f"   Turma: {turma}")
        print(f"   Vagas: {vagas}")
        print(f"   Horário: {horario}")
        print()

        # Parse atomic blocks
        atomic_blocks = parser.split_to_atomic_tuples(horario)
        print(f"🕐 Blocos atômicos necessários: {atomic_blocks}")
        print()

        # 2. Buscar TODAS as salas onde FUP0408 já foi alocada historicamente
        print(f"{'=' * 80}")
        print(f"📜 HISTÓRICO COMPLETO DE ALOCAÇÕES DE {codigo}")
        print(f"{'=' * 80}\n")

        historical_rooms = session.execute(
            text(
                """
                SELECT s.id, s.nome, s.capacidade, sem.nome as semestre,
                       COUNT(DISTINCT d.semestre_id) as num_semestres,
                       COUNT(*) as num_blocos
                FROM alocacoes_semestrais a
                JOIN demandas d ON a.demanda_id = d.id
                JOIN salas s ON a.sala_id = s.id
                JOIN semestres sem ON d.semestre_id = sem.id
                WHERE d.codigo_disciplina = :codigo
                  AND d.semestre_id != :current_sem
                GROUP BY s.id, s.nome, s.capacidade, sem.nome
                ORDER BY num_semestres DESC, s.nome
            """
            ),
            {"codigo": codigo, "current_sem": semester_id},
        ).fetchall()

        if historical_rooms:
            print(f"Salas com histórico de {codigo}:")
            salas_historico = {}
            for (
                sala_id,
                sala_nome,
                capacidade,
                semestre,
                num_sem,
                num_blocos,
            ) in historical_rooms:
                if sala_nome not in salas_historico:
                    salas_historico[sala_nome] = {
                        "id": sala_id,
                        "capacidade": capacidade,
                        "semestres": [],
                        "total_blocos": 0,
                    }
                salas_historico[sala_nome]["semestres"].append(semestre)
                salas_historico[sala_nome]["total_blocos"] += num_blocos

            for sala_nome, info in salas_historico.items():
                num_alocacoes = len(info["semestres"])
                print(f"\n   🏢 {sala_nome} (Capacidade: {info['capacidade']})")
                print(f"      Semestres: {', '.join(info['semestres'])}")
                print(
                    f"      Total: {num_alocacoes} semestre(s), {info['total_blocos']} blocos"
                )
                print(
                    f"      🎯 Pontos históricos: {num_alocacoes} × 1 = {num_alocacoes} pontos"
                )
        else:
            print(f"❌ Sem histórico de alocações de {codigo}")

        print()

        # 3. Verificar alocação ATUAL de FUP0408 em 2026-1
        print(f"\n{'=' * 80}")
        print("📍 ALOCAÇÃO ATUAL (2026-1)")
        print(f"{'=' * 80}\n")

        result = session.execute(
            text(
                """
                SELECT DISTINCT s.id, s.nome, s.capacidade
                FROM alocacoes_semestrais a
                JOIN salas s ON a.sala_id = s.id
                WHERE a.demanda_id = :demanda_id
            """
            ),
            {"demanda_id": demanda_id},
        ).fetchone()

        if result:
            sala_atual_id, sala_atual_nome, sala_atual_cap = result
            print(f"✅ {codigo} foi alocada para: {sala_atual_nome}")
            print(f"   Capacidade: {sala_atual_cap} lugares (demanda: {vagas} vagas)")

            # Verificar se tem histórico nesta sala
            hist_atual = session.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT d.semestre_id) as num_sem
                    FROM alocacoes_semestrais a
                    JOIN demandas d ON a.demanda_id = d.id
                    WHERE d.codigo_disciplina = :codigo
                      AND a.sala_id = :sala_id
                      AND d.semestre_id != :current_sem
                """
                ),
                {
                    "codigo": codigo,
                    "sala_id": sala_atual_id,
                    "current_sem": semester_id,
                },
            ).fetchone()

            num_hist_atual = hist_atual[0] if hist_atual else 0
            print(f"   📜 Histórico nesta sala: {num_hist_atual} alocação(ões)")
            print(f"   🎯 Pontos históricos: {num_hist_atual} pontos")
        else:
            print(f"❌ {codigo} NÃO foi alocada!")

        print()

        # 4. Verificar disponibilidade das salas com histórico
        print(f"\n{'=' * 80}")
        print("🔍 ANÁLISE DE DISPONIBILIDADE DAS SALAS COM HISTÓRICO")
        print(f"{'=' * 80}\n")

        if not salas_historico:
            print("Nenhuma sala com histórico para analisar.")
            return

        for sala_nome, info in salas_historico.items():
            print(f"\n{'─' * 80}")
            print(f"🏢 Sala: {sala_nome} (ID: {info['id']}, Cap: {info['capacidade']})")
            print(
                f"   Histórico: {len(info['semestres'])} alocação(ões) - {info['semestres']}"
            )
            print(f"{'─' * 80}")

            # Verificar conflitos
            conflitos = []
            livres = []

            for bloco_codigo, dia_sigaa in atomic_blocks:
                result = session.execute(
                    text(
                        """
                        SELECT d.codigo_disciplina, d.nome_disciplina, d.turma_disciplina
                        FROM alocacoes_semestrais a
                        JOIN demandas d ON a.demanda_id = d.id
                        WHERE a.sala_id = :sala_id
                          AND a.dia_semana_id = :dia
                          AND a.codigo_bloco = :bloco
                          AND d.semestre_id = :sem_id
                    """
                    ),
                    {
                        "sala_id": info["id"],
                        "dia": dia_sigaa,
                        "bloco": bloco_codigo,
                        "sem_id": semester_id,
                    },
                ).fetchone()

                if result:
                    conflitos.append((bloco_codigo, dia_sigaa, result))
                    print(f"   ❌ Conflito: Dia {dia_sigaa} Bloco {bloco_codigo}")
                    print(
                        f"      Ocupado por: {result[0]} - {result[1][:50]}... (Turma {result[2]})"
                    )
                else:
                    livres.append((bloco_codigo, dia_sigaa))
                    print(f"   ✅ Livre: Dia {dia_sigaa} Bloco {bloco_codigo}")

            print(f"\n   📊 Resumo: {len(livres)}/{len(atomic_blocks)} blocos livres")

            if conflitos:
                print(f"   ❌ SALA INVIÁVEL: {len(conflitos)} conflito(s)")
            else:
                print("   ✅✅ SALA VIÁVEL E COM HISTÓRICO!")
                print("   🎯 Esta sala deveria ter sido escolhida!")

        # 5. Comparar pontuação esperada
        print(f"\n\n{'=' * 80}")
        print("🎯 COMPARAÇÃO DE PONTUAÇÃO (ESPERADO)")
        print(f"{'=' * 80}\n")

        print("Pontuação base (capacidade adequada): 4 pontos")
        print()

        if sala_atual_nome in salas_historico:
            print(f"Sala ATUAL ({sala_atual_nome}):")
            print(
                f"   Base: 4 + Histórico: {len(salas_historico[sala_atual_nome]['semestres'])} = {4 + len(salas_historico[sala_atual_nome]['semestres'])} pontos"
            )
        else:
            print(f"Sala ATUAL ({sala_atual_nome}):")
            print(
                f"   Base: 4 + Histórico: {num_hist_atual} = {4 + num_hist_atual} pontos"
            )

        print()
        print("Salas com HISTÓRICO e DISPONÍVEIS:")
        for sala_nome, info in salas_historico.items():
            if sala_nome != sala_atual_nome:
                num_hist = len(info["semestres"])
                print(
                    f"   {sala_nome}: Base: 4 + Histórico: {num_hist} = {4 + num_hist} pontos"
                )

        print()
        print("⚠️  CONCLUSÃO:")
        print("Se alguma sala com histórico estava DISPONÍVEL e teve pontuação MAIOR,")
        print("então há um BUG no algoritmo de scoring ou na seleção de candidatos!")


if __name__ == "__main__":
    main()
