"""
Scoring Settings Tab Component

Allows users to configure scoring weights and rules for the allocation algorithm.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any

from src.config.database import get_db_session
from src.utils.ui_feedback import display_session_feedback, set_session_feedback


def render_scoring_tab():
    """Render the scoring configuration tab with editable settings."""

    st.subheader("🎯 Configuração de Pontuação")

    st.info(
        """
        ℹ️ **Ajuste os pesos de pontuação** usados pelo algoritmo de alocação.

        **Pesos de Pontuação:**
        - **Capacidade Adequada**: Pontos quando a sala tem capacidade suficiente para a disciplina
        - **Alocações Históricas**: Pontos por cada alocação anterior da disciplina na mesma sala
        - **Lim. Máximo Histórico**: Limite máximo de pontos históricos (ex: 10 alocações × 2 pts = 20 pts → limitado a 12 pts)
        - **Regra Obrigatória**: Pontos quando a sala atende uma regra rígida (ex: sala específica obrigatória)
        - **Sala Preferida**: Pontos quando sala está nas preferências do professor
        - **Característica Preferida**: Pontos quando sala tem característica preferida (ex: projetor, quadro)

        ⚠️ **Impacto das Mudanças:**
        - Aumentar pontuação do **histórico** valoriza estabilidade (disciplinas ficam nas mesmas salas)
        - Reduzir **capacidade** dá mais peso ao histórico vs. capacidade adequada
        - Aumentar **Lim. máximo** permite que salas muito populares acumulem mais pontos históricos
        - Aumentar **preferências** dá mais peso às escolhas dos professores

        As mudanças afetarão **novas alocações** executadas após salvar.
        """
    )

    # Import current config
    from src.config.scoring_config import SCORING_WEIGHTS

    # Create DataFrame with current values
    scoring_data = [
        {
            "Parâmetro": "Capacidade Adequada",
            "Valor Atual": SCORING_WEIGHTS.CAPACITY_ADEQUATE,
            "Categoria": "Base",
            "Descrição": "Pontos quando sala tem capacidade >= vagas da disciplina",
        },
        {
            "Parâmetro": "Histórico por Alocação",
            "Valor Atual": SCORING_WEIGHTS.HISTORICAL_FREQUENCY_PER_ALLOCATION,
            "Categoria": "Histórico",
            "Descrição": "Pontos por cada vez que a disciplina foi alocada na sala antes",
        },
        {
            "Parâmetro": "Lim. Máximo Histórico",
            "Valor Atual": SCORING_WEIGHTS.HISTORICAL_FREQUENCY_MAX_CAP,
            "Categoria": "Histórico",
            "Descrição": "Limite máximo de PONTOS históricos (não quantidade de alocações)",
        },
        {
            "Parâmetro": "Regra Obrigatória",
            "Valor Atual": SCORING_WEIGHTS.HARD_RULE_COMPLIANCE,
            "Categoria": "Regras",
            "Descrição": "Pontos por atender regra hard (ex: sala específica obrigatória)",
        },
        {
            "Parâmetro": "Sala Preferida",
            "Valor Atual": SCORING_WEIGHTS.PREFERRED_ROOM,
            "Categoria": "Preferências",
            "Descrição": "Pontos quando sala está nas preferências do professor",
        },
        {
            "Parâmetro": "Característica Preferida",
            "Valor Atual": SCORING_WEIGHTS.PREFERRED_CHARACTERISTIC,
            "Categoria": "Preferências",
            "Descrição": "Pontos quando sala tem característica preferida (ex: projetor)",
        },
    ]

    df = pd.DataFrame(scoring_data)

    st.markdown("### 📊 Pesos de Pontuação Atuais")

    # Display current configuration with editable values
    edited_df = st.data_editor(
        df,
        width="stretch",
        hide_index=True,
        disabled=["Parâmetro", "Categoria", "Descrição"],
        column_config={
            "Parâmetro": st.column_config.TextColumn(
                "Parâmetro",
                width="medium",
            ),
            "Valor Atual": st.column_config.NumberColumn(
                "Valor",
                min_value=0,
                max_value=50,
                step=1,
                format="%d pts",
                help="Clique duplo para editar",
            ),
            "Categoria": st.column_config.TextColumn(
                "Categoria",
                width="small",
            ),
            "Descrição": st.column_config.TextColumn(
                "Descrição",
                width="large",
            ),
        },
        key="scoring_editor",
    )

    # Detect changes
    changes_detected = False
    changes_summary = []

    for idx, row in edited_df.iterrows():
        original_value = df.iloc[idx]["Valor Atual"]
        new_value = row["Valor Atual"]
        param_name = row["Parâmetro"]

        if new_value != original_value:
            changes_detected = True
            changes_summary.append(
                f"- **{param_name}**: {original_value} → {new_value} pts"
            )

    # Show save button only if changes detected
    if changes_detected:
        st.warning("⚠️ **Alterações detectadas:**\n\n" + "\n".join(changes_summary))

        col1, col2, col3 = st.columns([1, 1, 4])

        with col1:
            if st.button("💾 Salvar Alterações", type="primary", width="stretch"):
                try:
                    # Update the scoring_config.py file with new values
                    _save_scoring_config(edited_df)

                    set_session_feedback(
                        "scoring_update",
                        True,
                        "Configuração de pontuação atualizada com sucesso! As novas configurações serão aplicadas nas próximas alocações.",
                        ttl=10,
                    )

                    # Clear any caches that might depend on scoring config
                    st.cache_data.clear()

                    st.rerun()

                except Exception as e:
                    set_session_feedback(
                        "scoring_update",
                        False,
                        f"Erro ao salvar configurações: {str(e)}",
                        ttl=10,
                    )

        with col2:
            if st.button("🔄 Reverter", width="stretch"):
                st.rerun()

    else:
        st.success("✅ Nenhuma alteração pendente")

    # Display feedback messages
    display_session_feedback("scoring_update")

    # Show scoring impact simulation
    st.markdown("---")
    st.markdown("### 📈 Simulação de Impacto")

    with st.expander("🔍 Ver exemplo de pontuação com configurações atuais"):
        _show_scoring_simulation(edited_df if changes_detected else df)


def _save_scoring_config(df: pd.DataFrame) -> None:
    """
    Update the scoring configuration JSON file with new values.

    Args:
        df: DataFrame with updated scoring values
    """
    import json
    from pathlib import Path
    from datetime import datetime

    config_path = (
        Path(__file__).parent.parent.parent.parent / "data" / "scoring_config.json"
    )

    # Create mapping from display name to config key
    param_mapping = {
        "Capacidade Adequada": "CAPACITY_ADEQUATE",
        "Histórico por Alocação": "HISTORICAL_FREQUENCY_PER_ALLOCATION",
        "Lim. Máximo Histórico": "HISTORICAL_FREQUENCY_MAX_CAP",
        "Regra Obrigatória": "HARD_RULE_COMPLIANCE",
        "Sala Preferida": "PREFERRED_ROOM",
        "Característica Preferida": "PREFERRED_CHARACTERISTIC",
    }

    # Load current configuration
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        st.error(f"Erro ao carregar configuração atual: {e}")
        return

    # Update weights with new values
    for _, row in df.iterrows():
        param_name = row["Parâmetro"]
        new_value = int(row["Valor Atual"])

        if param_name in param_mapping:
            config_key = param_mapping[param_name]
            config["weights"][config_key] = new_value

    # Validate the new configuration
    from src.config.scoring_config import validate_scoring_config

    if not validate_scoring_config(config):
        st.error(
            "Configuração inválida detectada. Verifique os valores e tente novamente."
        )
        return

    # Update metadata
    config["_metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    # Write back to file
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"Erro ao salvar configuração: {e}")
        return

    # Reload the configuration module
    from src.config.scoring_config import reload_scoring_config

    reload_scoring_config()


def _show_scoring_simulation(df: pd.DataFrame) -> None:
    """
    Show a simulation of how different scenarios would be scored.

    Args:
        df: DataFrame with scoring configuration
    """
    # Extract current/edited values
    capacity_pts = int(
        df[df["Parâmetro"] == "Capacidade Adequada"]["Valor Atual"].iloc[0]
    )
    history_weight = int(
        df[df["Parâmetro"] == "Histórico por Alocação"]["Valor Atual"].iloc[0]
    )
    history_cap = int(
        df[df["Parâmetro"] == "Lim. Máximo Histórico"]["Valor Atual"].iloc[0]
    )

    st.markdown(
        "**Exemplo: Disciplina com 30 vagas competindo por sala com capacidade 36**"
    )

    scenarios = [
        {"Histórico": 0, "Descrição": "Sem histórico (nova disciplina)"},
        {"Histórico": 1, "Descrição": "1 alocação anterior"},
        {"Histórico": 2, "Descrição": "2 alocações anteriores"},
        {"Histórico": 3, "Descrição": "3 alocações anteriores"},
        {"Histórico": 5, "Descrição": "5 alocações anteriores"},
        {
            "Histórico": 10,
            "Descrição": f"10 alocações (pontos históricos limitados a {history_cap} pts)",
        },
    ]

    simulation_data = []
    for scenario in scenarios:
        hist_count = scenario["Histórico"]
        # Calculate points: count × weight, then cap at max POINTS (not count)
        hist_points = hist_count * history_weight
        capped_hist_points = min(hist_points, history_cap)

        total_score = capacity_pts + capped_hist_points

        simulation_data.append(
            {
                "Cenário": scenario["Descrição"],
                "Capacidade": f"{capacity_pts} pts",
                "Histórico": f"{hist_count} × {history_weight} = {hist_points} pts{' → ' + str(capped_hist_points) + ' pts' if hist_points > history_cap else ''}",
                "Total": f"{total_score} pts",
            }
        )

    sim_df = pd.DataFrame(simulation_data)
    st.dataframe(sim_df, width="stretch", hide_index=True)

    # Show range
    min_score = capacity_pts
    max_score = capacity_pts + (history_cap * history_weight)

    st.info(
        f"📊 **Range de pontuação:** {min_score} a {max_score} pontos\n\n"
        f"- Disciplina sem histórico: **{min_score} pts**\n"
        f"- Disciplina com máximo histórico ({history_cap}+): **{max_score} pts**\n"
        f"- Diferença (gap): **{max_score - min_score} pts**"
    )
