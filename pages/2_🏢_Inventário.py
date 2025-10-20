"""
Inventory Management Page - Room/Building/Campus CRUD

Comprehensive inventory management for physical space allocation infrastructure.
Includes CRUD operations for campuses, buildings, and rooms.

Route: /pages/2_🏢_Inventário.py
URL: ?page=Inventário
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# ============================================================================
# AUTHENTICATION CHECK
# ============================================================================
# Retrieve authenticator from session state (set by main.py)
authenticator = st.session_state.get("authenticator")

if authenticator is None:
    st.warning("👈 Por favor, faça login na página inicial para acessar o sistema.")
    st.page_link("main.py", label="Voltar para o início ↩", icon="🏠")
    st.stop()

# Call login with unrendered location to maintain session (required for page refresh fix)
try:
    authenticator.login(location="unrendered", key="authenticator-inventario")
except Exception as exc:
    st.error(f"❌ Erro de autenticação: {exc}")
    st.stop()

auth_status = st.session_state.get("authentication_status")

if auth_status:
    # Show logout button in sidebar
    authenticator.logout(location="sidebar", key="logout-inventario")
elif auth_status is False:
    st.error("❌ Acesso negado.")
    st.stop()
else:
    # Not authenticated - redirect to main page
    st.warning("👈 Por favor, faça login na página inicial para acessar o sistema.")
    st.page_link("main.py", label="Voltar para o início ↩", icon="🏠")
    st.stop()

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Ensalamento - Inventário",
    page_icon="🏢",
    layout="wide",
)

# ============================================================================
# IMPORTS
# ============================================================================

from src.repositories.sala import SalaRepository
from src.config.database import get_db_session

# ============================================================================
# PAGE HEADER
# ============================================================================

st.title("🏢 Gerenciamento de Inventário")
st.markdown(
    "Gerencie campi, prédios, salas e características da infraestrutura física."
)

st.markdown("---")

# ============================================================================
# TABS STRUCTURE
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs(
    ["📍 Campi", "🏭 Prédios", "🚪 Salas", "🏷️ Características"]
)

# =============================================================================
# TAB 1: CAMPUS MANAGEMENT
# =============================================================================

with tab1:
    st.subheader("Gerenciamento de Campi")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Novo Campus", key="btn_campus", width="stretch"):
            st.session_state.show_campus_form = True

    # Campus list
    st.write("**Campi Cadastrados:**")
    st.info(
        """
    Funcionalidade em desenvolvimento.

    Nesta seção você poderá:
    - 📝 Criar novos campi
    - ✏️ Editar campi existentes
    - 🗑️ Remover campi (se sem prédios)
    - 📊 Ver estatísticas por campus
    """
    )

# =============================================================================
# TAB 2: BUILDING MANAGEMENT
# =============================================================================

with tab2:
    st.subheader("Gerenciamento de Prédios")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Novo Prédio", key="btn_predio", width="stretch"):
            st.session_state.show_predio_form = True

    st.write("**Prédios Cadastrados:**")
    st.info(
        """
    Funcionalidade em desenvolvimento.

    Nesta seção você poderá:
    - 📝 Criar novos prédios
    - 🎯 Associar a um campus
    - ✏️ Editar informações do prédio
    - 🗑️ Remover prédios (se sem salas)
    - 📊 Ver salas por prédio
    """
    )

# =============================================================================
# TAB 3: ROOM MANAGEMENT (MAIN)
# =============================================================================

with tab3:
    st.subheader("Gerenciamento de Salas")

    # Filters and actions
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

    with col1:
        floor_filter = st.selectbox(
            "Filtrar por Andar",
            ["Todos", "Térreo (0)", "1º Andar (1)"],
            key="sala_floor_filter",
        )

    with col2:
        capacity_filter = st.selectbox(
            "Filtrar por Capacidade",
            ["Todas", "Pequenas (<30)", "Médias (30-50)", "Grandes (>50)"],
            key="sala_capacity_filter",
        )

    with col3:
        search_text = st.text_input(
            "Buscar por Nome", placeholder="ex: A1, Sala...", key="sala_search"
        )

    with col4:
        if st.button("➕ Nova Sala", width="stretch"):
            st.session_state.show_sala_form = True

    st.markdown("---")

    # Room list
    try:
        with get_db_session() as session:
            sala_repo = SalaRepository(session)
            salas = sala_repo.get_all()

            if salas:
                # Apply filters
                filtered_salas = salas

                # Floor filter
                if floor_filter != "Todos":
                    if floor_filter == "Térreo (0)":
                        filtered_salas = [s for s in filtered_salas if s.andar == "0"]
                    elif floor_filter == "1º Andar (1)":
                        filtered_salas = [s for s in filtered_salas if s.andar == "1"]

                # Capacity filter
                if capacity_filter != "Todas":
                    if capacity_filter == "Pequenas (<30)":
                        filtered_salas = [
                            s for s in filtered_salas if s.capacidade < 30
                        ]
                    elif capacity_filter == "Médias (30-50)":
                        filtered_salas = [
                            s for s in filtered_salas if 30 <= s.capacidade <= 50
                        ]
                    elif capacity_filter == "Grandes (>50)":
                        filtered_salas = [
                            s for s in filtered_salas if s.capacidade > 50
                        ]

                # Search filter
                if search_text:
                    filtered_salas = [
                        s
                        for s in filtered_salas
                        if search_text.lower() in s.nome.lower()
                    ]

                # Display summary
                st.markdown(
                    f"**Total de salas encontradas: {len(filtered_salas)} de {len(salas)}**"
                )

                # Create DataFrame for display
                sala_data = []
                for sala in filtered_salas:
                    sala_data.append(
                        {
                            "ID": sala.id,
                            "Nome": sala.nome,
                            "Andar": sala.andar or "N/A",
                            "Capacidade": sala.capacidade,
                            "Tipo de Assento": sala.tipo_assento or "-",
                            "Criada em": (
                                sala.created_at.strftime("%d/%m/%Y")
                                if sala.created_at
                                else "-"
                            ),
                        }
                    )

                df = pd.DataFrame(sala_data)

                # Display table
                st.dataframe(df, width="stretch", hide_index=True)

                # Export button
                col1, col2, col3 = st.columns(3)
                with col1:
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Exportar CSV",
                        data=csv,
                        file_name=f"salas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                    )

                st.markdown("---")

                # Room details modal (simplified)
                st.subheader("Detalhes de Sala")

                selected_room_id = st.selectbox(
                    "Selecione uma sala para ver detalhes:",
                    [s.id for s in filtered_salas],
                    format_func=lambda x: f"ID {x} - {next((s.nome for s in filtered_salas if s.id == x), 'N/A')}",
                )

                if selected_room_id:
                    selected_room = next(
                        (s for s in filtered_salas if s.id == selected_room_id), None
                    )

                    if selected_room:
                        col1, col2 = st.columns([1, 1])

                        with col1:
                            st.markdown(f"**Nome:** {selected_room.nome}")
                            st.markdown(f"**Andar:** {selected_room.andar or 'N/A'}")
                            st.markdown(
                                f"**Capacidade:** {selected_room.capacidade} pessoas"
                            )

                        with col2:
                            st.markdown(
                                f"**Tipo de Assento:** {selected_room.tipo_assento or 'Não especificado'}"
                            )
                            st.markdown(f"**Prédio ID:** {selected_room.predio_id}")
                            st.markdown(
                                f"**Tipo Sala ID:** {selected_room.tipo_sala_id}"
                            )

                        # Edit / Delete buttons
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            if st.button(
                                "✏️ Editar Sala", key=f"edit_{selected_room_id}"
                            ):
                                st.session_state.editing_sala_id = selected_room_id
                                st.rerun()

                        with col2:
                            if st.button(
                                "🗑️ Deletar Sala", key=f"delete_{selected_room_id}"
                            ):
                                try:
                                    sala_repo.delete(selected_room_id)
                                    st.success(
                                        f"Sala {selected_room.nome} removida com sucesso!"
                                    )
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao deletar sala: {str(e)}")

            else:
                st.info(
                    "📭 Nenhuma sala cadastrada ainda. Clique em '➕ Nova Sala' para criar."
                )

    except Exception as e:
        st.error(f"❌ Erro ao carregar salas: {str(e)}")

# =============================================================================
# TAB 4: ROOM CHARACTERISTICS
# =============================================================================

with tab4:
    st.subheader("Gerenciamento de Características de Salas")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button(
            "➕ Nova Característica", key="btn_caracteristica", width="stretch"
        ):
            st.session_state.show_caracteristica_form = True

    st.info(
        """
    Funcionalidade em desenvolvimento.

    Nesta seção você poderá:
    - 📝 Definir características disponíveis (ex: Projetor, Ar-condicionado, Quadro branco)
    - 🏷️ Associar características a salas
    - ✏️ Editar características existentes
    - 🗑️ Remover características não utilizadas
    - 📊 Ver quais salas têm cada característica
    """
    )

st.markdown("---")

# Footer
