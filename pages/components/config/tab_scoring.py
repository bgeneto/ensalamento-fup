"""
Scoring Settings Tab Component.

Allows users to configure scoring weights and rules for the allocation algorithm.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pandas as pd
import streamlit as st

from src.config.scoring_registry import build_default_scoring_config, set_nested_value
from src.utils.ui_feedback import display_session_feedback, set_session_feedback


def render_scoring_tab():
    """Render the scoring configuration tab with editable settings."""
    from src.services.scoring_configuration_service import ScoringConfigurationService

    st.subheader("🎯 Configuração de Pontuação")

    st.info(
        """
        ℹ️ **Ajuste os pesos e regras de pontuação** usados pelo algoritmo de alocação.

        **Como ler esta tela:**
        - **Valor Atual**: configuração efetiva usada nas novas alocações
        - **Valor Padrão**: default versionado no código
        - **Origem**: mostra se o valor vem do default ou de um override salvo
        - **Faixa**: limites válidos para o parâmetro

        ⚠️ **Impacto das mudanças:**
        - Pesos maiores priorizam mais fortemente aquele critério
        - Penalidades maiores desestimulam fragmentação e desvios
        - Regras booleanas alteram o comportamento global do algoritmo

        As mudanças afetam **novas alocações** executadas após salvar.
        """
    )

    display_session_feedback("scoring_update")

    service = ScoringConfigurationService()
    base_config = service.get_effective_config_dict()
    rows_df = pd.DataFrame(service.get_ui_rows())
    weights_df, rules_df = _build_editor_dataframes(rows_df)

    _render_summary_metrics(rows_df)

    st.markdown("### 📊 Pesos de Pontuação")
    edited_weights_df = st.data_editor(
        weights_df,
        width="stretch",
        hide_index=True,
        disabled=[
            "Chave",
            "Valor Padrão",
            "Categoria",
            "Origem",
            "Faixa",
            "Descrição",
            "Tipo",
        ],
        column_config={
            "Chave": None,
            "Tipo": None,
            "Parâmetro": st.column_config.TextColumn("Parâmetro", width="medium"),
            "Valor Atual": st.column_config.NumberColumn(
                "Valor Atual",
                min_value=0,
                max_value=500,
                step=1,
                format="%d pts",
                help="Clique duplo para editar o peso efetivo.",
            ),
            "Valor Padrão": st.column_config.NumberColumn(
                "Valor Padrão",
                format="%d pts",
                help="Valor default definido no código.",
            ),
            "Categoria": st.column_config.TextColumn("Categoria", width="small"),
            "Origem": st.column_config.TextColumn("Origem", width="small"),
            "Faixa": st.column_config.TextColumn(
                "Faixa",
                width="small",
                help="Faixa de valores válida para este parâmetro.",
            ),
            "Descrição": st.column_config.TextColumn("Descrição", width="large"),
        },
        key="scoring_weights_editor",
    )

    st.markdown("### ⚙️ Regras de Comportamento")
    edited_rules_df = st.data_editor(
        rules_df,
        width="stretch",
        hide_index=True,
        disabled=[
            "Chave",
            "Valor Padrão",
            "Categoria",
            "Origem",
            "Faixa",
            "Descrição",
            "Tipo",
        ],
        column_config={
            "Chave": None,
            "Tipo": None,
            "Parâmetro": st.column_config.TextColumn("Parâmetro", width="medium"),
            "Valor Atual": st.column_config.CheckboxColumn(
                "Valor Atual",
                help="Marque ou desmarque para ativar a regra.",
            ),
            "Valor Padrão": st.column_config.CheckboxColumn(
                "Valor Padrão",
                help="Estado default definido no código.",
            ),
            "Categoria": st.column_config.TextColumn("Categoria", width="small"),
            "Origem": st.column_config.TextColumn("Origem", width="small"),
            "Faixa": st.column_config.TextColumn("Faixa", width="small"),
            "Descrição": st.column_config.TextColumn("Descrição", width="large"),
        },
        key="scoring_rules_editor",
    )

    change_summaries = _summarize_scoring_changes(weights_df, edited_weights_df)
    change_summaries.extend(_summarize_scoring_changes(rules_df, edited_rules_df))
    preview_config = _build_effective_config_from_editors(
        base_config,
        edited_weights_df,
        edited_rules_df,
    )

    if change_summaries:
        st.warning("⚠️ **Alterações detectadas:**\n\n" + "\n".join(change_summaries))

        col1, col2, col3 = st.columns([1, 1, 4])

        with col1:
            if st.button("💾 Salvar Alterações", type="primary", width="stretch"):
                try:
                    _save_scoring_config(preview_config)

                    set_session_feedback(
                        "scoring_update",
                        True,
                        "Configuração de pontuação atualizada com sucesso! As novas configurações serão aplicadas nas próximas alocações.",
                        ttl=10,
                    )

                    st.cache_data.clear()
                    st.rerun()

                except Exception as exc:
                    set_session_feedback(
                        "scoring_update",
                        False,
                        f"Erro ao salvar configurações: {str(exc)}",
                        ttl=10,
                    )
                    st.rerun()

        with col2:
            if st.button("🔄 Reverter", width="stretch"):
                st.rerun()

    else:
        st.success("✅ Nenhuma alteração pendente")

    st.markdown("---")
    st.markdown("### 📈 Simulação de Impacto")

    with st.expander("🔍 Ver exemplo de pontuação com configurações atuais"):
        _show_scoring_simulation(preview_config)


def _build_editor_dataframes(
    rows_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build separate editor dataframes for numeric weights and boolean rules."""
    weights_df = rows_df[rows_df["Tipo"] == "int"].copy()
    rules_df = rows_df[rows_df["Tipo"] == "bool"].copy()

    weights_df["Valor Atual"] = weights_df["Valor Atual"].astype(int)
    weights_df["Valor Padrão"] = weights_df["Valor Padrão"].astype(int)
    weights_df["Faixa"] = weights_df.apply(_format_range_label, axis=1)
    weights_df = weights_df[
        [
            "Chave",
            "Parâmetro",
            "Valor Atual",
            "Valor Padrão",
            "Categoria",
            "Origem",
            "Faixa",
            "Descrição",
            "Tipo",
        ]
    ].reset_index(drop=True)

    rules_df["Valor Atual"] = rules_df["Valor Atual"].astype(bool)
    rules_df["Valor Padrão"] = rules_df["Valor Padrão"].astype(bool)
    rules_df["Faixa"] = "Ligado / Desligado"
    rules_df = rules_df[
        [
            "Chave",
            "Parâmetro",
            "Valor Atual",
            "Valor Padrão",
            "Categoria",
            "Origem",
            "Faixa",
            "Descrição",
            "Tipo",
        ]
    ].reset_index(drop=True)

    return weights_df, rules_df


def _format_range_label(row: pd.Series) -> str:
    """Format the allowed range label for a numeric scoring field."""
    minimum = row.get("Mínimo")
    maximum = row.get("Máximo")

    if pd.notna(minimum) and pd.notna(maximum):
        return f"{int(minimum)} - {int(maximum)}"
    if pd.notna(minimum):
        return f">= {int(minimum)}"
    if pd.notna(maximum):
        return f"<= {int(maximum)}"
    return "Livre"


def _render_summary_metrics(rows_df: pd.DataFrame) -> None:
    """Render a compact summary of active overrides and rule/weight counts."""
    total_params = len(rows_df)
    override_count = int((rows_df["Origem"] == "override").sum())
    rules_count = int((rows_df["Tipo"] == "bool").sum())
    weights_count = int((rows_df["Tipo"] == "int").sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Parâmetros", total_params)
    col2.metric("Overrides Ativos", override_count)
    col3.metric("Pesos", weights_count)
    col4.metric("Regras", rules_count)


def _summarize_scoring_changes(
    original_df: pd.DataFrame, edited_df: pd.DataFrame
) -> list[str]:
    """Summarize editor changes between the original and edited scoring tables."""
    if original_df.empty or edited_df.empty:
        return []

    original_by_key = original_df.set_index("Chave")
    summaries: list[str] = []

    for _, row in edited_df.iterrows():
        key = row["Chave"]
        if key not in original_by_key.index:
            continue

        original_value = original_by_key.at[key, "Valor Atual"]
        new_value = row["Valor Atual"]
        value_type = row["Tipo"]

        if new_value == original_value:
            continue

        summaries.append(
            f"- **{row['Parâmetro']}**: "
            f"{_format_scoring_value(original_value, value_type)} → "
            f"{_format_scoring_value(new_value, value_type)}"
        )

    return summaries


def _format_scoring_value(value: Any, value_type: str) -> str:
    """Format a scoring value for change summaries."""
    if value_type == "bool":
        return "Ativado" if bool(value) else "Desativado"
    return f"{int(value)} pts"


def _build_effective_config_from_editors(
    base_config: dict[str, dict[str, Any]],
    *editor_dataframes: pd.DataFrame,
) -> dict[str, dict[str, Any]]:
    """Build an effective config dict from the current editor tables."""
    config = deepcopy(base_config)

    for editor_df in editor_dataframes:
        for _, row in editor_df.iterrows():
            if row["Tipo"] == "bool":
                value = bool(row["Valor Atual"])
            else:
                value = int(row["Valor Atual"])

            set_nested_value(config, row["Chave"], value)

    return config


def _save_scoring_config(config: dict[str, dict[str, Any]]) -> None:
    """Persist the scoring configuration using the DB-backed service."""
    from src.config.scoring_config import reload_scoring_config, validate_scoring_config
    from src.services.scoring_configuration_service import ScoringConfigurationService

    if not validate_scoring_config(config):
        raise ValueError(
            "Configuração inválida detectada. Verifique os valores e tente novamente."
        )

    ScoringConfigurationService().save_effective_config(
        config,
        username=st.session_state.get("username"),
        reason="Updated via scoring configuration tab",
        source="ui",
    )

    reload_scoring_config()


def _show_scoring_simulation(config: dict[str, dict[str, Any]]) -> None:
    """Show a simulation of how the current scoring config affects sample outcomes."""
    weights = config.get("weights", {})
    capacity_pts = int(weights.get("CAPACITY_ADEQUATE", 0))
    history_weight = int(weights.get("HISTORICAL_FREQUENCY_PER_ALLOCATION", 0))
    history_cap = int(weights.get("HISTORICAL_FREQUENCY_MAX_CAP", 0))
    preferred_room_pts = int(weights.get("PREFERRED_ROOM", 0))
    hard_rule_pts = int(weights.get("HARD_RULE_COMPLIANCE", 0))

    st.markdown(
        "**Exemplo: disciplina com 30 vagas competindo por uma sala de capacidade 36**"
    )

    scenarios = [
        {
            "Descrição": "Sem histórico e sem preferências atendidas",
            "Histórico": 0,
            "Sala Preferida": False,
            "Hard Rule": False,
        },
        {
            "Descrição": "1 alocação anterior e preferência de sala atendida",
            "Histórico": 1,
            "Sala Preferida": True,
            "Hard Rule": False,
        },
        {
            "Descrição": "3 alocações anteriores e regra obrigatória atendida",
            "Histórico": 3,
            "Sala Preferida": False,
            "Hard Rule": True,
        },
        {
            "Descrição": f"10 alocações anteriores (limitadas a {history_cap} pts)",
            "Histórico": 10,
            "Sala Preferida": True,
            "Hard Rule": True,
        },
    ]

    simulation_data = []
    for scenario in scenarios:
        hist_count = scenario["Histórico"]
        raw_hist_points = hist_count * history_weight
        capped_hist_points = min(raw_hist_points, history_cap)
        preferred_points = preferred_room_pts if scenario["Sala Preferida"] else 0
        hard_points = hard_rule_pts if scenario["Hard Rule"] else 0
        total_score = capacity_pts + capped_hist_points + preferred_points + hard_points

        simulation_data.append(
            {
                "Cenário": scenario["Descrição"],
                "Capacidade": f"{capacity_pts} pts",
                "Histórico": (
                    f"{hist_count} × {history_weight} = {raw_hist_points} pts"
                    f"{' → ' + str(capped_hist_points) + ' pts' if raw_hist_points > history_cap else ''}"
                ),
                "Preferência": (
                    f"{preferred_room_pts} pts"
                    if scenario["Sala Preferida"]
                    else "0 pts"
                ),
                "Hard Rule": (
                    f"{hard_rule_pts} pts" if scenario["Hard Rule"] else "0 pts"
                ),
                "Total": f"{total_score} pts",
            }
        )

    sim_df = pd.DataFrame(simulation_data)
    st.dataframe(sim_df, width="stretch", hide_index=True)

    min_score = capacity_pts
    max_score = capacity_pts + history_cap + preferred_room_pts + hard_rule_pts

    st.info(
        f"📊 **Range aproximado do exemplo:** {min_score} a {max_score} pontos\n\n"
        f"- Base só por capacidade: **{min_score} pts**\n"
        f"- Com histórico no teto + preferência + hard rule: **{max_score} pts**\n"
        f"- Diferença (gap): **{max_score - min_score} pts**"
    )

    if config != build_default_scoring_config():
        st.caption(
            "A simulação acima já considera os valores editados na tela, mesmo antes de salvar."
        )
