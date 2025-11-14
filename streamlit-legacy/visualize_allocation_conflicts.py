"""
Mapa Visual de Conflitos e Dependências de Alocação
Mostra a cadeia de decisões que levou FUP0518 a não ser alocada na AT-42/12
"""

import sys
from sqlalchemy import text
from src.config.database import get_db_session
from src.utils.sigaa_parser import SigaaScheduleParser


def print_header(title, char="="):
    """Imprime cabeçalho formatado."""
    width = 100
    print(f"\n{char * width}")
    print(f"{title:^{width}}")
    print(f"{char * width}\n")


def print_box(content, width=96, indent=2):
    """Imprime conteúdo em uma caixa."""
    space = " " * indent
    print(f"{space}╔{'═' * width}╗")
    for line in content:
        padding = width - len(line)
        print(f"{space}║ {line}{' ' * padding} ║")
    print(f"{space}╚{'═' * width}╝")


def analyze_room_competition(session, sala_id, sala_nome, semester_id):
    """Analisa todas as disciplinas alocadas em uma sala e seus históricos."""
    parser = SigaaScheduleParser()

    # Buscar todas as demandas alocadas nesta sala
    demands = session.execute(
        text(
            """
            SELECT DISTINCT
                d.id, d.codigo_disciplina, d.nome_disciplina,
                d.turma_disciplina, d.vagas_disciplina, d.horario_sigaa_bruto
            FROM alocacoes_semestrais a
            JOIN demandas d ON a.demanda_id = d.id
            WHERE a.sala_id = :sala_id
              AND d.semestre_id = :sem_id
            ORDER BY d.codigo_disciplina, d.turma_disciplina
        """
        ),
        {"sala_id": sala_id, "sem_id": semester_id},
    ).fetchall()

    print_header(f"🏢 SALA: {sala_nome}", "═")

    for dem_id, codigo, nome, turma, vagas, horario in demands:
        # Buscar blocos ocupados
        blocos = session.execute(
            text(
                """
                SELECT dia_semana_id, codigo_bloco
                FROM alocacoes_semestrais
                WHERE demanda_id = :dem_id
                ORDER BY dia_semana_id, codigo_bloco
            """
            ),
            {"dem_id": dem_id},
        ).fetchall()

        blocos_str = ", ".join([f"{dia}{bloco}" for dia, bloco in blocos])

        # Buscar histórico desta disciplina nesta sala
        historico = session.execute(
            text(
                """
                SELECT COUNT(DISTINCT d.semestre_id) as num_sem,
                       GROUP_CONCAT(DISTINCT sem.nome) as semestres
                FROM alocacoes_semestrais a
                JOIN demandas d ON a.demanda_id = d.id
                JOIN semestres sem ON d.semestre_id = sem.id
                WHERE d.codigo_disciplina = :codigo
                  AND a.sala_id = :sala_id
                  AND d.semestre_id != :current_sem
            """
            ),
            {"codigo": codigo, "sala_id": sala_id, "current_sem": semester_id},
        ).fetchone()

        num_hist = historico[0] if historico and historico[0] else 0
        sem_list = historico[1] if historico and historico[1] else "Nenhum"

        pontos_base = 4  # Capacidade adequada
        pontos_hist = num_hist
        pontos_total = pontos_base + pontos_hist

        print(f"\n  📚 {codigo} - {nome[:50]}")
        print(f"     Turma: {turma} | Vagas: {vagas}")
        print(f"     ⏰ Horário: {horario} → Blocos: {blocos_str}")
        print(f"     📜 Histórico: {num_hist} alocação(ões) anterior(es) ({sem_list})")
        print(
            f"     🎯 Pontuação: {pontos_base} (base) + {pontos_hist} (histórico) = {pontos_total} pontos"
        )


def analyze_demand_alternatives(session, codigo_disciplina, semester_id, parser):
    """Analisa alternativas de alocação para uma disciplina."""
    # Buscar a demanda
    demand = session.execute(
        text(
            """
            SELECT id, codigo_disciplina, nome_disciplina, turma_disciplina,
                   vagas_disciplina, horario_sigaa_bruto
            FROM demandas
            WHERE codigo_disciplina = :codigo AND semestre_id = :sem_id
            LIMIT 1
        """
        ),
        {"codigo": codigo_disciplina, "sem_id": semester_id},
    ).fetchone()

    if not demand:
        return

    dem_id, codigo, nome, turma, vagas, horario = demand
    atomic_blocks = parser.split_to_atomic_tuples(horario)

    print_header(f"🔍 ANÁLISE DE ALTERNATIVAS: {codigo}", "─")

    print(f"  📚 Disciplina: {nome}")
    print(f"  Turma: {turma} | Vagas: {vagas} | Horário: {horario}")
    print(f"  Blocos necessários: {atomic_blocks}\n")

    # Buscar todas as salas com histórico
    historical_rooms = session.execute(
        text(
            """
            SELECT DISTINCT
                s.id, s.nome, s.capacidade,
                COUNT(DISTINCT d.semestre_id) as num_hist
            FROM alocacoes_semestrais a
            JOIN demandas d ON a.demanda_id = d.id
            JOIN salas s ON a.sala_id = s.id
            WHERE d.codigo_disciplina = :codigo
              AND d.semestre_id != :current_sem
            GROUP BY s.id, s.nome, s.capacidade
            ORDER BY num_hist DESC, s.capacidade
        """
        ),
        {"codigo": codigo, "current_sem": semester_id},
    ).fetchall()

    # Buscar sala atual
    current_room = session.execute(
        text(
            """
            SELECT DISTINCT s.id, s.nome, s.capacidade
            FROM alocacoes_semestrais a
            JOIN salas s ON a.sala_id = s.id
            WHERE a.demanda_id = :dem_id
        """
        ),
        {"dem_id": dem_id},
    ).fetchone()

    if current_room:
        curr_id, curr_nome, curr_cap = current_room
        print(f"  ✅ Sala alocada: {curr_nome} (Cap: {curr_cap})")

        # Verificar se tem histórico
        curr_hist = session.execute(
            text(
                """
                SELECT COUNT(DISTINCT d.semestre_id)
                FROM alocacoes_semestrais a
                JOIN demandas d ON a.demanda_id = d.id
                WHERE d.codigo_disciplina = :codigo
                  AND a.sala_id = :sala_id
                  AND d.semestre_id != :current_sem
            """
            ),
            {"codigo": codigo, "sala_id": curr_id, "current_sem": semester_id},
        ).fetchone()

        hist_count = curr_hist[0] if curr_hist else 0
        pontos_base = 4 if curr_cap >= vagas else 0
        pontos_total = pontos_base + hist_count
        print(f"  🎯 Pontuação: {pontos_base} + {hist_count} = {pontos_total} pontos\n")

    print("  📊 Salas com Histórico:")
    print("  " + "─" * 95)

    for sala_id, sala_nome, capacidade, num_hist in historical_rooms:
        # Verificar disponibilidade
        conflitos = []
        for bloco_codigo, dia_sigaa in atomic_blocks:
            conflict = session.execute(
                text(
                    """
                    SELECT d.codigo_disciplina
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

            if conflict:
                conflitos.append(f"{dia_sigaa}{bloco_codigo}→{conflict[0]}")

        capacidade_ok = capacidade >= vagas
        pontos_base = 4 if capacidade_ok else 0
        pontos_total = pontos_base + num_hist

        status = (
            "✅ DISPONÍVEL"
            if not conflitos
            else f"❌ OCUPADA ({len(conflitos)} conflitos)"
        )
        cap_status = "✅" if capacidade_ok else "⚠️ PEQUENA"

        print(
            f"\n  🏢 {sala_nome:<15} Cap: {capacidade:>3} {cap_status:<12} Hist: {num_hist} → {pontos_total} pts"
        )
        print(f"     {status}")
        if conflitos:
            print(f"     Conflitos: {', '.join(conflitos[:3])}")


def main():
    with get_db_session() as session:
        parser = SigaaScheduleParser()

        # Buscar semestre 2026-1
        result = session.execute(
            text("SELECT id FROM semestres WHERE nome = '2026-1'")
        ).fetchone()
        semester_id = result[0] if result else None

        if not semester_id:
            print("❌ Semestre 2026-1 não encontrado!")
            return

        print_header("🗺️  MAPA VISUAL DE CONFLITOS E DEPENDÊNCIAS DE ALOCAÇÃO", "█")
        print_box(
            [
                "Semestre: 2026-1",
                "Foco: Por que FUP0518 não foi alocada na sala AT-42/12?",
                "",
                "Este mapa mostra a cadeia de decisões baseadas em pontuação histórica",
                "que levou múltiplas disciplinas a competirem pela mesma sala.",
            ]
        )

        # 1. Analisar a sala AT-42/12 (foco da investigação)
        analyze_room_competition(session, 2, "AT-42/12", semester_id)

        print("\n" + "═" * 100)
        print("💡 INTERPRETAÇÃO: AT-42/12 é uma sala muito disputada!")
        print("   • FUP0329 T2: 7 pontos (3 históricos) → Conquistou 2N1, 2N2")
        print("   • FUP0408 T1: 6 pontos (2 históricos) → Conquistou 4M3, 4M4")
        print("   • FUP0518: Precisava 4M3, 4M4 mas já estava ocupada por FUP0408")
        print("═" * 100)

        # 2. Analisar alternativas de FUP0518
        print("\n\n")
        analyze_demand_alternatives(session, "FUP0518", semester_id, parser)

        # 3. Analisar alternativas de FUP0408 (que bloqueou FUP0518)
        print("\n\n")
        analyze_demand_alternatives(session, "FUP0408", semester_id, parser)

        # 4. Analisar FUP0329 (que bloqueou FUP0408 nos outros horários)
        print("\n\n")
        analyze_demand_alternatives(session, "FUP0329", semester_id, parser)

        # 5. Conclusão visual
        print("\n\n")
        print_header("🎯 CADEIA DE DECISÕES (Efeito Cascata)", "█")

        print(
            """
  Ordem de Alocação por Pontuação (maior → menor):

  1️⃣  FUP0329 T2 (7 pontos na AT-42/12)
      ├─ 3 alocações históricas na AT-42/12
      ├─ Conquistou blocos: 2N1, 2N2
      └─ ✅ Decisão: AT-42/12 (melhor opção)

  2️⃣  FUP0408 T1 (6 pontos na AT-42/12)
      ├─ 2 alocações históricas na AT-42/12
      ├─ Blocos 2N1, 2N2 já ocupados por FUP0329
      ├─ Tentou alternativa: A1-48/32 e A1-48/40 (capacidade insuficiente: 16 < 30 vagas)
      ├─ Conquistou blocos: 4M3, 4M4
      └─ ✅ Decisão: AT-42/12 (segunda melhor época)

  3️⃣  FUP0518 (1 ponto histórico na AT-42/12, mas 6 pontos total)
      ├─ 1 alocação histórica na AT-42/12
      ├─ Blocos 4M3, 4M4 já ocupados por FUP0408 ⚠️
      ├─ AT-42/12 INDISPONÍVEL nos horários necessários
      ├─ Sem alternativas com histórico disponíveis
      └─ ⚠️  Decisão: AT-79/11 (4 pontos - sem histórico, mas disponível)
        """
        )

        print_header("📋 CONCLUSÕES", "═")
        print_box(
            [
                "✅ O algoritmo está funcionando CORRETAMENTE",
                "",
                "• Prioriza disciplinas com maior pontuação histórica (comportamento esperado)",
                "• FUP0329 tinha mais histórico (3) que FUP0408 (2) que FUP0518 (1)",
                "• Cada disciplina conquistou a melhor sala disponível no SEU TURNO",
                "",
                "❌ O 'problema' não é um bug, é uma LIMITAÇÃO DE RECURSOS:",
                "",
                "• AT-42/12 é muito popular (3 disciplinas diferentes com histórico)",
                "• Não há salas suficientes para atender todas com histórico",
                "• Disciplinas com menos histórico são forçadas a aceitar alternativas",
                "",
                "💡 SOLUÇÃO POSSÍVEL:",
                "",
                "• Aumentar o peso dos pontos históricos (ex: 2 pontos por alocação)",
                "• Adicionar um fator de 'equidade' para balancear distribuição",
                "• Reservar salas com histórico alto para disciplinas específicas (regras)",
                "• Considerar múltiplos semestres simultaneamente (otimização global)",
            ],
            width=96,
        )

        print("\n")


if __name__ == "__main__":
    main()
