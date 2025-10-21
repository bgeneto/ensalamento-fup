"""
Associations Management Tab Component

Handles associations between rooms (Salas) and characteristics (Caracteristicas).
Extracted from the main inventory page for better maintainability.
"""

import streamlit as st
import pandas as pd
from src.repositories.sala import SalaRepository
from src.repositories.caracteristica import CaracteristicaRepository
from src.config.database import get_db_session
from src.utils.ui_feedback import display_session_feedback, set_session_feedback

# Needs to be imported from auth module for shared imports
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def render_associations_tab():
    st.subheader("Associação de Características com Salas")

    st.info(
        """
        Gerencie a associação entre salas e características.
        - Use o **seletor** abaixo para escolher uma sala ou característica.
        - Clique em **Adicionar Características** ou **Remover Características** para fazer alterações.
        - Visualize o estado atual das associações na tabela abaixo.
        """
    )

    # Room-characteristics associations management
    try:
        with get_db_session() as session:
            sala_repo = SalaRepository(session)
            caracteristica_repo = CaracteristicaRepository(session)

            # Get all rooms and characteristics
            salas = sala_repo.get_all()
            caracteristicas = caracteristica_repo.get_all()

            if not salas or not caracteristicas:
                st.warning(
                    "📭 Você precisa ter ao menos uma sala e uma característica cadastradas para fazer associações."
                )
                if not salas:
                    st.info("Acesse a aba 'Salas' para cadastrar salas.")
                if not caracteristicas:
                    st.info(
                        "Acesse a aba 'Características' para cadastrar características."
                    )
            else:
                # Create dropdown options
                sala_options = {s.id: s.nome for s in salas}
                caracteristica_options = {c.id: c.nome for c in caracteristicas}

                # Room selector spanning full width
                selected_sala_id = st.selectbox(
                    "Selecione uma sala:",
                    options=list(sala_options.keys()),
                    format_func=lambda x: sala_options.get(x, "N/A"),
                    key="sala_selector_associations",
                )

                # Get current characteristics for selected room
                if selected_sala_id:
                    sala_data = sala_repo.get_sala_with_caracteristicas(
                        selected_sala_id
                    )
                    if sala_data:
                        current_caracteristica_ids = [
                            c.id for c in sala_data["caracteristicas"]
                        ]

                        # Display current characteristics status (full width)
                        if sala_data["caracteristicas"]:
                            current_names = [
                                c.nome for c in sala_data["caracteristicas"]
                            ]
                        else:
                            st.warning(
                                "⚠️ Esta sala não possui características associadas."
                            )

                        # Multi-select for characteristics (full width)
                        selected_caracteristica_ids = st.multiselect(
                            f"Características para {sala_data['sala'].nome}:",
                            options=list(caracteristica_options.keys()),
                            format_func=lambda x: caracteristica_options.get(x, "N/A"),
                            default=current_caracteristica_ids,
                            key=f"caracteristica_multiselect_{selected_sala_id}",
                            help="Selecione uma ou mais características para associar à sala",
                        )

                        # Action buttons in proper layout
                        col_btn1, col_btn2 = st.columns([1, 1])

                        with col_btn1:
                            if st.button(
                                "💾 Salvar",
                                key=f"update_{selected_sala_id}",
                                help="Salva as características da sala",
                                width="stretch",
                                type="primary",
                            ):
                                try:
                                    success = sala_repo.set_caracteristicas_for_sala(
                                        selected_sala_id,
                                        selected_caracteristica_ids,
                                    )

                                    if success:
                                        set_session_feedback(
                                            "assoc_result",
                                            True,
                                            f"Características da sala '{sala_data['sala'].nome}' atualizadas com sucesso!",
                                        )
                                        st.rerun()
                                    else:
                                        set_session_feedback(
                                            "assoc_result",
                                            False,
                                            "Falha ao atualizar características da sala.",
                                        )

                                except Exception as e:
                                    set_session_feedback(
                                        "assoc_result",
                                        False,
                                        f"Erro ao atualizar: {str(e)}",
                                    )

                        with col_btn2:
                            if st.button(
                                "🗑️ Limpar Sala",
                                key=f"clear_{selected_sala_id}",
                                help="Remove todas as características da sala",
                                width="stretch",
                            ):
                                try:
                                    success = sala_repo.set_caracteristicas_for_sala(
                                        selected_sala_id, []
                                    )

                                    if success:
                                        set_session_feedback(
                                            "assoc_result",
                                            True,
                                            f"Todas as características removidas da sala '{sala_data['sala'].nome}'!",
                                        )
                                        st.rerun()
                                    else:
                                        set_session_feedback(
                                            "assoc_result",
                                            False,
                                            "Falha ao remover características.",
                                        )

                                except Exception as e:
                                    set_session_feedback(
                                        "assoc_result",
                                        False,
                                        f"Erro ao limpar: {str(e)}",
                                    )

                        # Display feedback messages
                        display_session_feedback("assoc_result")

                # Display comprehensive associations table
                st.divider()
                st.subheader("Visão Geral das Associações")

                # Build table data
                associations_data = []
                for sala in salas:
                    sala_with_carac = sala_repo.get_sala_with_caracteristicas(sala.id)
                    if sala_with_carac:
                        caracteristica_names = [
                            c.nome for c in sala_with_carac["caracteristicas"]
                        ]

                        associations_data.append(
                            {
                                "Sala": sala_with_carac["sala"].nome,
                                "Prédio": sala_with_carac[
                                    "sala"
                                ].predio_id,  # We'll resolve this later
                                "Capacidade": sala_with_carac["sala"].capacidade,
                                "Características": (
                                    "; ".join(caracteristica_names)
                                    if caracteristica_names
                                    else "Nenhuma"
                                ),
                                "Total Características": len(caracteristica_names),
                            }
                        )

                if associations_data:
                    associations_df = pd.DataFrame(associations_data)
                    st.dataframe(
                        associations_df,
                        column_config={
                            "Sala": st.column_config.TextColumn("Sala", width="medium"),
                            "Prédio": st.column_config.TextColumn(
                                "Prédio", width="medium"
                            ),
                            "Capacidade": st.column_config.NumberColumn(
                                "Capacidade", width="small"
                            ),
                            "Características": st.column_config.TextColumn(
                                "Características", width="large"
                            ),
                            "Total Características": st.column_config.NumberColumn(
                                "Total", width="small"
                            ),
                        },
                        hide_index=True,
                    )

                    # Summary stats
                    total_associations = sum(
                        len(row.split("; ")) if row != "Nenhuma" else 0
                        for row in associations_df["Características"]
                    )
                    avg_carac_per_room = (
                        total_associations / len(associations_df)
                        if associations_df.shape[0] > 0
                        else 0
                    )

                    col_stats1, col_stats2, col_stats3 = st.columns(3)
                    with col_stats1:
                        st.metric("Total de Associações", total_associations)
                    with col_stats2:
                        st.metric("Média por Sala", f"{avg_carac_per_room:.1f}")
                    with col_stats3:
                        st.metric(
                            "Salas sem Características",
                            sum(
                                1
                                for row in associations_df["Características"]
                                if row == "Nenhuma"
                            ),
                        )
                else:
                    st.info("Nenhuma sala encontrada para exibir associações.")

    except Exception as e:
        st.error(f"❌ Erro ao carregar associações: {str(e)}")
