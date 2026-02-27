"""
Script para investigar por que FUP0518 não foi alocada na sala AT-42/12.
"""

from sqlalchemy import text
from src.config.database import get_db_session
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.sala import SalaRepository
from src.repositories.alocacao import AlocacaoRepository
from src.services.room_scoring_service import RoomScoringService
from src.utils.sigaa_parser import SigaaScheduleParser


def main():
    with get_db_session() as session:
        # Repositories
        disciplina_repo = DisciplinaRepository(session)
        sala_repo = SalaRepository(session)
        alocacao_repo = AlocacaoRepository(session)
        scoring_service = RoomScoringService(session)
        parser = SigaaScheduleParser()

        # 1. Buscar a demanda FUP0518 no semestre 2026-1
        result = session.execute(
            text("SELECT id FROM semestres WHERE nome = '2026-1'")
        ).fetchone()
        semester_id = result[0] if result else None

        if not semester_id:
            print("❌ Semestre 2026-1 não encontrado!")
            return

        print(f"✅ Semestre 2026-1 ID: {semester_id}\n")

        # Buscar demanda
        result = session.execute(
            text(
                """
                SELECT id, codigo_disciplina, nome_disciplina, turma_disciplina,
                       vagas_disciplina, horario_sigaa_bruto
                FROM demandas
                WHERE codigo_disciplina = 'FUP0518' AND semestre_id = :sem_id
            """
            ),
            {"sem_id": semester_id},
        ).fetchone()

        if not result:
            print("❌ Demanda FUP0518 não encontrada no semestre 2026-1!")
            return

        demanda_id, codigo, nome, turma, vagas, horario = result
        print("📚 Demanda encontrada:")
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

        # 2. Verificar salas AT-42/12 e AT-79/11
        salas_interesse = ["AT-42/12", "AT-79/11"]

        for sala_nome in salas_interesse:
            print(f"\n{'=' * 80}")
            print(f"🏢 Analisando sala: {sala_nome}")
            print(f"{'=' * 80}\n")

            # Buscar sala
            result = session.execute(
                text("SELECT id, nome, capacidade FROM salas WHERE nome = :nome"),
                {"nome": sala_nome},
            ).fetchone()

            if not result:
                print(f"❌ Sala {sala_nome} não encontrada!")
                continue

            sala_id, sala_nome_db, capacidade = result
            print(f"   ID: {sala_id}")
            print(f"   Capacidade: {capacidade} lugares")
            print()

            # 3. Verificar histórico de alocações desta disciplina nesta sala
            historical_result = session.execute(
                text(
                    """
                    SELECT sem.nome, COUNT(*) as blocos
                    FROM alocacoes_semestrais a
                    JOIN demandas d ON a.demanda_id = d.id
                    JOIN semestres sem ON d.semestre_id = sem.id
                    WHERE d.codigo_disciplina = :codigo
                      AND a.sala_id = :sala_id
                      AND sem.id != :current_sem
                    GROUP BY sem.nome
                    ORDER BY sem.nome
                """
                ),
                {"codigo": codigo, "sala_id": sala_id, "current_sem": semester_id},
            ).fetchall()

            if historical_result:
                print(f"📜 Histórico de alocações de {codigo} na sala {sala_nome}:")
                total_allocations = 0
                for sem_nome, blocos in historical_result:
                    allocations_count = blocos // 4  # 4 blocos por alocação semestral
                    total_allocations += allocations_count
                    print(
                        f"   - {sem_nome}: {blocos} blocos ({allocations_count} alocação(ões))"
                    )
                print(f"   📊 Total: {total_allocations} alocações históricas")
                print(
                    f"   🎯 Pontos históricos: {total_allocations} × 1 = {total_allocations} pontos"
                )
            else:
                print(f"📜 Sem histórico de alocações de {codigo} na sala {sala_nome}")
                print("   🎯 Pontos históricos: 0 pontos")
            print()

            # 4. Verificar conflitos nos blocos necessários
            print("🔍 Verificando conflitos no semestre 2026-1:")
            conflitos_encontrados = []
            blocos_livres = []

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
                        "sala_id": sala_id,
                        "dia": dia_sigaa,
                        "bloco": bloco_codigo,
                        "sem_id": semester_id,
                    },
                ).fetchone()

                if result:
                    conflitos_encontrados.append((bloco_codigo, dia_sigaa, result))
                    print(f"   ❌ Conflito: Dia {dia_sigaa} Bloco {bloco_codigo}")
                    print(
                        f"      Ocupado por: {result[0]} - {result[1]} (Turma {result[2]})"
                    )
                else:
                    blocos_livres.append((bloco_codigo, dia_sigaa))
                    print(f"   ✅ Livre: Dia {dia_sigaa} Bloco {bloco_codigo}")

            print()
            print(f"📊 Resumo: {len(blocos_livres)}/{len(atomic_blocks)} blocos livres")

            if conflitos_encontrados:
                print(
                    f"❌ SALA INVIÁVEL: {len(conflitos_encontrados)} conflito(s) detectado(s)"
                )
            else:
                print("✅ SALA VIÁVEL: Todos os blocos estão livres!")
            print()

        # 5. Verificar alocação atual da demanda
        print(f"\n{'=' * 80}")
        print("📍 ALOCAÇÃO ATUAL DA DEMANDA")
        print(f"{'=' * 80}\n")

        result = session.execute(
            text(
                """
                SELECT DISTINCT s.nome, s.capacidade
                FROM alocacoes_semestrais a
                JOIN salas s ON a.sala_id = s.id
                WHERE a.demanda_id = :demanda_id
            """
            ),
            {"demanda_id": demanda_id},
        ).fetchone()

        if result:
            sala_alocada, cap_alocada = result
            print(f"✅ Demanda {codigo} foi alocada para: {sala_alocada}")
            print(f"   Capacidade: {cap_alocada} lugares")

            # Calcular pontos da sala alocada
            sala_alocada_obj = session.execute(
                text("SELECT id FROM salas WHERE nome = :nome"), {"nome": sala_alocada}
            ).fetchone()

            if sala_alocada_obj:
                sala_alocada_id = sala_alocada_obj[0]

                # Histórico da sala alocada
                hist_result = session.execute(
                    text(
                        """
                        SELECT COUNT(DISTINCT d.semestre_id) as sem_count
                        FROM alocacoes_semestrais a
                        JOIN demandas d ON a.demanda_id = d.id
                        WHERE d.codigo_disciplina = :codigo
                          AND a.sala_id = :sala_id
                          AND d.semestre_id != :current_sem
                    """
                    ),
                    {
                        "codigo": codigo,
                        "sala_id": sala_alocada_id,
                        "current_sem": semester_id,
                    },
                ).fetchone()

                hist_count = hist_result[0] if hist_result else 0
                print(f"   📜 Histórico: {hist_count} alocação(ões) anterior(es)")
                print(
                    f"   🎯 Pontos históricos: {hist_count} × 1 = {hist_count} pontos"
                )
        else:
            print(f"❌ Demanda {codigo} NÃO foi alocada!")

        print()
        print(f"\n{'=' * 80}")
        print("🎯 CONCLUSÃO DA INVESTIGAÇÃO")
        print(f"{'=' * 80}\n")

        print("A investigação mostrará:")
        print("1. Se AT-42/12 tinha conflitos que impediram a alocação")
        print("2. Quantos pontos históricos AT-42/12 teria ganho")
        print("3. Por que AT-79/11 foi escolhida ao invés de AT-42/12")
        print()


if __name__ == "__main__":
    main()
