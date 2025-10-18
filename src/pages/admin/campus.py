"""
Campus management page for Sistema de Ensalamento FUP/UnB
Administrative interface for managing campuses and buildings
"""

import streamlit as st
from typing import Optional, Dict, Any
from src.services.inventory_service import InventoryService
from src.services.auth_service import is_current_user_admin
from models import CampusCreate, CampusUpdate, PredioCreate, PredioUpdate


def render_campus_page():
    """Render campus management page"""
    st.title("🏛️ Gestão de Campi e Prédios")
    st.caption("Gerencie campi, prédios e a estrutura física da instituição")

    # Check if user is admin
    if not is_current_user_admin():
        st.error("❌ Acesso negado. Esta página requer privilégios de administrador.")
        return

    # Create tabs for different operations
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📋 Lista de Campi",
            "➕ Criar Campus",
            "🏢 Gestão de Prédios",
            "📊 Estatísticas",
        ]
    )

    with tab1:
        render_campus_list()

    with tab2:
        render_create_campus()

    with tab3:
        render_building_management()

    with tab4:
        render_statistics()


def render_campus_list():
    """Render list of all campuses"""
    st.header("📋 Lista de Campi")

    campuses = InventoryService.get_all_campus()

    if not campuses:
        st.info("Nenhum campus encontrado no sistema.")
        return

    # Display statistics
    stats = InventoryService.get_inventory_stats()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total de Campi", stats["campus"])
    with col2:
        st.metric("Total de Prédios", stats["predios"])

    st.markdown("---")

    # Display campuses with their buildings
    for campus in campuses:
        with st.expander(f"🏛️ {campus.nome}"):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.write(f"**Descrição:** {campus.descricao or 'Sem descrição'}")
                st.write(f"**ID:** {campus.id}")

                # Get buildings for this campus
                buildings = InventoryService.get_predios_by_campus(campus.id)
                if buildings:
                    st.write(f"**Prédios ({len(buildings)}):**")
                    for building in buildings:
                        st.write(
                            f"  • {building.nome} - {building.descricao or 'Sem descrição'}"
                        )
                else:
                    st.write("**Prédios:** Nenhum prédio cadastrado")

            with col2:
                # Action buttons
                if st.button(f"Editar {campus.nome}", key=f"edit_campus_{campus.id}"):
                    st.session_state["editing_campus"] = campus.id
                    st.rerun()

                if buildings:
                    if st.button(f"Adicionar Prédio", key=f"add_building_{campus.id}"):
                        st.session_state["adding_building"] = campus.id
                        st.rerun()

                if not buildings:
                    if st.button(
                        f"Excluir {campus.nome}",
                        key=f"delete_campus_{campus.id}",
                        type="secondary",
                    ):
                        if InventoryService.delete_campus(campus.id):
                            st.success(f"Campus {campus.nome} excluído com sucesso!")
                            st.rerun()
                        else:
                            st.error(f"Não foi possível excluir o campus {campus.nome}")

    # Check if there's a campus being edited
    if "editing_campus" in st.session_state:
        render_edit_campus_form(st.session_state["editing_campus"])

    # Check if there's a building being added
    if "adding_building" in st.session_state:
        render_add_building_form(st.session_state["adding_building"])


def render_create_campus():
    """Render create campus form"""
    st.header("➕ Criar Novo Campus")

    with st.form("create_campus_form"):
        st.subheader("Informações do Campus")

        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input(
                "Nome do Campus",
                placeholder="ex: FUP - Faculdade UnB Planaltina",
                help="Nome completo do campus",
            )

        with col2:
            # Placeholder for future fields
            st.empty()

        descricao = st.text_area(
            "Descrição",
            placeholder="Descrição detalhada do campus, localização, etc.",
            help="Informações adicionais sobre o campus",
        )

        st.markdown("---")

        submitted = st.form_submit_button(
            "Criar Campus", type="primary", use_container_width=True
        )

        if submitted:
            # Validate inputs
            if not nome:
                st.error("❌ Nome do campus é obrigatório.")
                return

            # Create campus
            campus_data = CampusCreate(nome=nome, descricao=descricao)

            new_campus = InventoryService.create_campus(campus_data)
            if new_campus:
                st.success(f"✅ Campus '{nome}' criado com sucesso!")
                st.rerun()
            else:
                st.error(f"❌ Falha ao criar campus '{nome}'.")


def render_building_management():
    """Render building management interface"""
    st.header("🏢 Gestão de Prédios")

    # Get all buildings with campus information
    buildings = InventoryService.get_all_predios()

    if not buildings:
        st.info("Nenhum prédio encontrado no sistema.")
        return

    # Get campuses for dropdown
    campuses = InventoryService.get_all_campus()
    campus_options = {campus.nome: campus.id for campus in campuses}

    # Filter by campus
    selected_campus = st.selectbox(
        "Filtrar por Campus:",
        options=["Todos"] + list(campus_options.keys()),
        help="Selecione um campus para filtrar os prédios",
    )

    if selected_campus != "Todos":
        campus_id = campus_options[selected_campus]
        filtered_buildings = [b for b in buildings if b.campus_id == campus_id]
    else:
        filtered_buildings = buildings

    st.markdown("---")

    # Display buildings
    for building in filtered_buildings:
        with st.expander(
            f"🏢 {building.nome} ({building.campus.nome if building.campus else 'Campus não encontrado'})"
        ):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.write(f"**Descrição:** {building.descricao or 'Sem descrição'}")
                st.write(
                    f"**Campus:** {building.campus.nome if building.campus else 'Campus não encontrado'}"
                )
                st.write(f"**ID:** {building.id}")

                # Get rooms for this building
                from src.services.inventory_service import InventoryService

                rooms = InventoryService.get_salas_by_predio(building.id)
                st.write(f"**Salas:** {len(rooms)} salas cadastradas")

            with col2:
                # Action buttons
                if st.button(f"Editar Prédio", key=f"edit_building_{building.id}"):
                    st.session_state["editing_building"] = building.id
                    st.rerun()

                if not rooms or len(rooms) == 0:
                    if st.button(
                        f"Excluir Prédio",
                        key=f"delete_building_{building.id}",
                        type="secondary",
                    ):
                        if InventoryService.delete_predio(building.id):
                            st.success(f"Prédio {building.nome} excluído com sucesso!")
                            st.rerun()
                        else:
                            st.error(
                                f"Não foi possível excluir o prédio {building.nome}"
                            )

    # Check if there's a building being edited
    if "editing_building" in st.session_state:
        render_edit_building_form(st.session_state["editing_building"])


def render_add_building_form(campus_id):
    """Render add building form for a specific campus"""
    campus = InventoryService.get_campus_by_id(campus_id)

    if not campus:
        st.error("Campus não encontrado.")
        return

    st.subheader(f"➕ Adicionar Prédio ao Campus: {campus.nome}")

    with st.form(f"add_building_form_{campus_id}"):
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input(
                "Nome do Prédio", placeholder="ex: Bloco A", help="Nome do prédio"
            )

        with col2:
            # Campus is pre-selected
            st.text_input("Campus", value=campus.nome, disabled=True)

        descricao = st.text_area(
            "Descrição",
            placeholder="Descrição do prédio, funções, etc.",
            help="Informações adicionais sobre o prédio",
        )

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button("Adicionar Prédio", type="primary")

        with col2:
            if st.form_submit_button("Cancelar", type="secondary"):
                del st.session_state["adding_building"]
                st.rerun()

        if submitted:
            # Validate inputs
            if not nome:
                st.error("❌ Nome do prédio é obrigatório.")
                return

            # Create building
            building_data = PredioCreate(
                nome=nome, descricao=descricao, campus_id=campus_id
            )

            new_building = InventoryService.create_predio(building_data)
            if new_building:
                st.success(f"✅ Prédio '{nome}' adicionado ao campus '{campus.nome}'!")
                del st.session_state["adding_building"]
                st.rerun()
            else:
                st.error(f"❌ Falha ao adicionar prédio '{nome}'.")


def render_edit_campus_form(campus_id):
    """Render edit campus form"""
    campus = InventoryService.get_campus_by_id(campus_id)

    if not campus:
        st.error("Campus não encontrado.")
        return

    st.subheader(f"✏️ Editar Campus: {campus.nome}")

    with st.form(f"edit_campus_form_{campus_id}"):
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input("Nome do Campus", value=campus.nome)

        with col2:
            # Placeholder for future fields
            st.empty()

        descricao = st.text_area("Descrição", value=campus.descricao or "")

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button("💾 Salvar Alterações", type="primary")

        with col2:
            if st.form_submit_button("❌ Cancelar", type="secondary"):
                del st.session_state["editing_campus"]
                st.rerun()

        if submitted:
            # Validate inputs
            if not nome:
                st.error("❌ Nome do campus é obrigatório.")
                return

            # Update campus
            campus_data = CampusUpdate(
                nome=nome, descricao=descricao if descricao else None
            )

            updated_campus = InventoryService.update_campus(campus_id, campus_data)
            if updated_campus:
                st.success(f"✅ Campus '{nome}' atualizado com sucesso!")
                del st.session_state["editing_campus"]
                st.rerun()
            else:
                st.error(f"❌ Falha ao atualizar campus '{nome}'.")


def render_edit_building_form(building_id):
    """Render edit building form"""
    building = InventoryService.get_predio_by_id(building_id)

    if not building:
        st.error("Prédio não encontrado.")
        return

    # Get all campuses for dropdown
    campuses = InventoryService.get_all_campus()
    campus_options = {campus.nome: campus.id for campus in campuses}

    st.subheader(f"✏️ Editar Prédio: {building.nome}")

    with st.form(f"edit_building_form_{building_id}"):
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input("Nome do Prédio", value=building.nome)

        with col2:
            # Campus selection
            current_campus_name = (
                building.campus.nome if building.campus else "Campus não encontrado"
            )
            selected_campus = st.selectbox(
                "Campus",
                options=list(campus_options.keys()),
                index=(
                    list(campus_options.keys()).index(current_campus_name)
                    if current_campus_name in campus_options
                    else 0
                ),
            )

        descricao = st.text_area("Descrição", value=building.descricao or "")

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button("💾 Salvar Alterações", type="primary")

        with col2:
            if st.form_submit_button("❌ Cancelar", type="secondary"):
                del st.session_state["editing_building"]
                st.rerun()

        if submitted:
            # Validate inputs
            if not nome:
                st.error("❌ Nome do prédio é obrigatório.")
                return

            # Update building
            building_data = PredioUpdate(
                nome=nome,
                descricao=descricao if descricao else None,
                campus_id=campus_options[selected_campus],
            )

            updated_building = InventoryService.update_predio(
                building_id, building_data
            )
            if updated_building:
                st.success(f"✅ Prédio '{nome}' atualizado com sucesso!")
                del st.session_state["editing_building"]
                st.rerun()
            else:
                st.error(f"❌ Falha ao atualizar prédio '{nome}'.")


def render_statistics():
    """Render campus and building statistics"""
    st.header("📊 Estatísticas de Campi e Prédios")

    stats = InventoryService.get_inventory_stats()

    # Overall statistics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total de Campi", stats["campus"])

    with col2:
        st.metric("Total de Prédios", stats["predios"])

    with col3:
        avg_buildings_per_campus = (
            stats["predios"] / stats["campus"] if stats["campus"] > 0 else 0
        )
        st.metric("Média de Prédios por Campus", f"{avg_buildings_per_campus:.1f}")

    st.markdown("---")

    # Campus details
    st.subheader("📋 Detalhes por Campus")

    campuses = InventoryService.get_all_campus()

    if campuses:
        for campus in campuses:
            buildings = InventoryService.get_predios_by_campus(campus.id)

            with st.expander(f"🏛️ {campus.nome}"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Prédios", len(buildings))

                with col2:
                    # Count total rooms in all buildings
                    total_rooms = 0
                    for building in buildings:
                        from src.services.inventory_service import InventoryService

                        rooms = InventoryService.get_salas_by_predio(building.id)
                        total_rooms += len(rooms)
                    st.metric("Salas", total_rooms)

                with col3:
                    st.metric("ID", campus.id)

                if buildings:
                    st.write("**Prédios:**")
                    for building in buildings:
                        from src.services.inventory_service import InventoryService

                        rooms = InventoryService.get_salas_by_predio(building.id)
                        st.write(f"  • {building.nome} ({len(rooms)} salas)")
    else:
        st.info("Nenhum campus encontrado para exibir estatísticas.")


def main():
    """Main entry point for the campus page"""
    render_campus_page()


if __name__ == "__main__":
    main()
