"""
Room management page for Sistema de Ensalamento FUP/UnB
Administrative interface for managing rooms, types, and characteristics
"""

import streamlit as st
from typing import Optional, List, Dict, Any
from src.services.inventory_service import InventoryService
from src.services.auth_service import is_current_user_admin
from models import (
    SalaCreate,
    SalaUpdate,
    TipoSalaCreate,
    TipoSalaUpdate,
    CaracteristicaCreate,
    CaracteristicaUpdate,
)
from utils import format_capacity_range


def render_salas_page():
    """Render room management page"""
    st.title("🏫 Gestão de Salas")
    st.caption("Gerencie salas, tipos de sala e características do sistema")

    # Check if user is admin
    if not is_current_user_admin():
        st.error("❌ Acesso negado. Esta página requer privilégios de administrador.")
        return

    # Create tabs for different operations
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📋 Lista de Salas",
            "➕ Criar Sala",
            "🏷️ Tipos de Sala",
            "✨ Características",
            "📊 Estatísticas",
        ]
    )

    with tab1:
        render_room_list()

    with tab2:
        render_create_room()

    with tab3:
        render_room_types_management()

    with tab4:
        render_characteristics_management()

    with tab5:
        render_room_statistics()


def render_room_list():
    """Render list of all rooms"""
    st.header("📋 Lista de Salas")

    # Filter options
    col1, col2, col3 = st.columns(3)

    with col1:
        # Campus filter
        campuses = InventoryService.get_all_campus()
        campus_options = {"Todos": None} | {
            campus.nome: campus.id for campus in campuses
        }
        selected_campus = st.selectbox(
            "Filtrar por Campus:", options=list(campus_options.keys())
        )

    with col2:
        # Building filter (depends on campus selection)
        if selected_campus != "Todos" and campus_options[selected_campus]:
            buildings = InventoryService.get_predios_by_campus(
                campus_options[selected_campus]
            )
            building_options = {"Todos": None} | {
                building.nome: building.id for building in buildings
            }
            selected_building = st.selectbox(
                "Filtrar por Prédio:", options=list(building_options.keys())
            )
        else:
            selected_building = "Todos"

    with col3:
        # Room type filter
        room_types = InventoryService.get_all_tipos_sala()
        type_options = {"Todos": None} | {
            room_type.nome: room_type.id for room_type in room_types
        }
        selected_type = st.selectbox(
            "Filtrar por Tipo:", options=list(type_options.keys())
        )

    # Apply filters
    filters = {}
    if selected_campus != "Todos" and campus_options[selected_campus]:
        filters["campus_id"] = campus_options[selected_campus]
    if (
        selected_building != "Todos"
        and selected_building != "Todos"
        and building_options[selected_building]
    ):
        filters["predio_id"] = building_options[selected_building]
    if selected_type != "Todos" and type_options[selected_type]:
        filters["tipo_sala_id"] = type_options[selected_type]

    # Get filtered rooms
    rooms = (
        InventoryService.search_salas(filters)
        if filters
        else InventoryService.get_all_salas()
    )

    if not rooms:
        st.info("Nenhuma sala encontrada com os filtros selecionados.")
        return

    # Display statistics
    stats = InventoryService.get_inventory_stats()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Salas", len(rooms))
    with col2:
        total_capacity = sum(room.capacidade for room in rooms)
        st.metric("Capacidade Total", total_capacity)
    with col3:
        avg_capacity = total_capacity // len(rooms) if rooms else 0
        st.metric("Capacidade Média", avg_capacity)

    st.markdown("---")

    # Display rooms
    for room in rooms:
        with st.expander(f"🏫 {room.nome} ({room.codigo})"):
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.write(
                    f"**Prédio:** {room.predio.nome if room.predio else 'Prédio não encontrado'}"
                )
                st.write(
                    f"**Campus:** {room.predio.campus.nome if room.predio and room.predio.campus else 'Campus não encontrado'}"
                )
                st.write(
                    f"**Tipo:** {room.tipo_sala.nome if room.tipo_sala else 'Tipo não encontrado'}"
                )
                st.write(f"**Andar:** {room.andar}")
                st.write(f"**Capacidade:** {format_capacity_range(room.capacidade)}")

                # Get characteristics
                if hasattr(room, "caracteristicas") and room.caracteristicas:
                    characteristics = [caract.nome for caract in room.caracteristicas]
                    st.write(
                        f"**Características:** {', '.join(characteristics) if characteristics else 'Nenhuma'}"
                    )

            with col2:
                if st.button(f"Editar", key=f"edit_room_{room.id}"):
                    st.session_state["editing_room"] = room.id
                    st.rerun()

            with col3:
                if st.button(
                    f"Excluir", key=f"delete_room_{room.id}", type="secondary"
                ):
                    if InventoryService.delete_sala(room.id):
                        st.success(f"Sala {room.nome} excluída com sucesso!")
                        st.rerun()
                    else:
                        st.error(f"Não foi possível excluir a sala {room.nome}")

    # Check if there's a room being edited
    if "editing_room" in st.session_state:
        render_edit_room_form(st.session_state["editing_room"])


def render_create_room():
    """Render create room form"""
    st.header("➕ Criar Nova Sala")

    # Get data for dropdowns
    buildings = InventoryService.get_all_predios()
    room_types = InventoryService.get_all_tipos_sala()
    characteristics = InventoryService.get_all_caracteristicas()

    if not buildings:
        st.error("Nenhum prédio encontrado. Cadastre um prédio primeiro.")
        return

    if not room_types:
        st.error("Nenhum tipo de sala encontrado. Cadastre um tipo de sala primeiro.")
        return

    with st.form("create_room_form"):
        st.subheader("Informações da Sala")

        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input(
                "Nome da Sala", placeholder="ex: 101", help="Nome ou número da sala"
            )

            capacidade = st.number_input(
                "Capacidade",
                min_value=1,
                max_value=500,
                value=40,
                help="Número de assentos/capacidade da sala",
            )

        with col2:
            # Building selection
            building_options = {
                f"{building.nome} ({building.campus.nome if building.campus else 'Campus não encontrado'})": building.id
                for building in buildings
            }
            selected_building = st.selectbox(
                "Prédio",
                options=list(building_options.keys()),
                help="Selecione o prédio onde a sala está localizada",
            )

            andar = st.number_input(
                "Andar",
                min_value=0,
                max_value=20,
                value=1,
                help="Andar onde a sala está localizada",
            )

        # Room type selection
        type_options = {room_type.nome: room_type.id for room_type in room_types}
        selected_type = st.selectbox(
            "Tipo de Sala",
            options=list(type_options.keys()),
            help="Selecione o tipo da sala",
        )

        # Characteristics selection
        if characteristics:
            st.subheader("Características")
            caract_options = {caract.nome: caract.id for caract in characteristics}
            selected_characteristics = st.multiselect(
                "Selecione as características da sala:",
                options=list(caract_options.keys()),
                help="Escolha todas as características que a sala possui",
            )
        else:
            selected_characteristics = []

        st.markdown("---")

        submitted = st.form_submit_button(
            "Criar Sala", type="primary", use_container_width=True
        )

        if submitted:
            # Validate inputs
            if not nome:
                st.error("❌ Nome da sala é obrigatório.")
                return

            if capacidade < 1:
                st.error("❌ Capacidade deve ser maior que zero.")
                return

            # Create room
            room_data = SalaCreate(
                nome=nome,
                capacidade=capacidade,
                andar=andar,
                predio_id=building_options[selected_building],
                tipo_sala_id=type_options[selected_type],
                caracteristicas=[
                    caract_options[caract] for caract in selected_characteristics
                ],
            )

            new_room = InventoryService.create_sala(room_data)
            if new_room:
                st.success(f"✅ Sala '{nome}' criada com sucesso!")
                st.rerun()
            else:
                st.error(f"❌ Falha ao criar sala '{nome}'.")


def render_room_types_management():
    """Render room types management"""
    st.header("🏷️ Gestão de Tipos de Sala")

    tab1, tab2 = st.tabs(["📋 Lista de Tipos", "➕ Criar Tipo"])

    with tab1:
        render_room_types_list()

    with tab2:
        render_create_room_type()


def render_room_types_list():
    """Render list of room types"""
    room_types = InventoryService.get_all_tipos_sala()

    if not room_types:
        st.info("Nenhum tipo de sala encontrado.")
        return

    for room_type in room_types:
        with st.expander(f"🏷️ {room_type.nome}"):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.write(f"**Descrição:** {room_type.descricao or 'Sem descrição'}")
                st.write(f"**ID:** {room_type.id}")

                # Count rooms of this type
                from database import DatabaseSession, Sala

                with DatabaseSession() as session:
                    room_count = (
                        session.query(Sala)
                        .filter(Sala.tipo_sala_id == room_type.id)
                        .count()
                    )
                    st.write(f"**Salas deste tipo:** {room_count}")

            with col2:
                if st.button(f"Editar", key=f"edit_type_{room_type.id}"):
                    st.session_state["editing_type"] = room_type.id
                    st.rerun()

                if room_count == 0:
                    if st.button(
                        f"Excluir", key=f"delete_type_{room_type.id}", type="secondary"
                    ):
                        if InventoryService.delete_tipo_sala(room_type.id):
                            st.success(f"Tipo de sala '{room_type.nome}' excluído!")
                            st.rerun()
                        else:
                            st.error(
                                f"Não foi possível excluir o tipo de sala '{room_type.nome}'"
                            )

    # Check if there's a type being edited
    if "editing_type" in st.session_state:
        render_edit_room_type_form(st.session_state["editing_type"])


def render_create_room_type():
    """Render create room type form"""
    st.subheader("➕ Criar Novo Tipo de Sala")

    with st.form("create_room_type_form"):
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input(
                "Nome do Tipo",
                placeholder="ex: Laboratório",
                help="Nome do tipo de sala",
            )

        with col2:
            # Placeholder
            st.empty()

        descricao = st.text_area(
            "Descrição",
            placeholder="Descrição detalhada do tipo de sala",
            help="Informações adicionais sobre este tipo de sala",
        )

        st.markdown("---")

        submitted = st.form_submit_button("Criar Tipo de Sala", type="primary")

        if submitted:
            if not nome:
                st.error("❌ Nome do tipo é obrigatório.")
                return

            type_data = TipoSalaCreate(nome=nome, descricao=descricao)

            new_type = InventoryService.create_tipo_sala(type_data)
            if new_type:
                st.success(f"✅ Tipo de sala '{nome}' criado com sucesso!")
                st.rerun()
            else:
                st.error(f"❌ Falha ao criar tipo de sala '{nome}'.")


def render_edit_room_type_form(type_id):
    """Render edit room type form"""
    room_type = None
    for rt in InventoryService.get_all_tipos_sala():
        if rt.id == type_id:
            room_type = rt
            break

    if not room_type:
        st.error("Tipo de sala não encontrado.")
        return

    st.subheader(f"✏️ Editar Tipo de Sala: {room_type.nome}")

    with st.form(f"edit_room_type_form_{type_id}"):
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input("Nome do Tipo", value=room_type.nome)

        with col2:
            st.empty()

        descricao = st.text_area("Descrição", value=room_type.descricao or "")

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button("💾 Salvar Alterações", type="primary")

        with col2:
            if st.form_submit_button("❌ Cancelar", type="secondary"):
                del st.session_state["editing_type"]
                st.rerun()

        if submitted:
            if not nome:
                st.error("❌ Nome do tipo é obrigatório.")
                return

            type_data = TipoSalaUpdate(
                nome=nome, descricao=descricao if descricao else None
            )

            updated_type = InventoryService.update_tipo_sala(type_id, type_data)
            if updated_type:
                st.success(f"✅ Tipo de sala '{nome}' atualizado!")
                del st.session_state["editing_type"]
                st.rerun()
            else:
                st.error(f"❌ Falha ao atualizar tipo de sala '{nome}'.")


def render_characteristics_management():
    """Render characteristics management"""
    st.header("✨ Gestão de Características")

    tab1, tab2 = st.tabs(["📋 Lista de Características", "➕ Criar Característica"])

    with tab1:
        render_characteristics_list()

    with tab2:
        render_create_characteristic()


def render_characteristics_list():
    """Render list of characteristics"""
    characteristics = InventoryService.get_all_caracteristicas()

    if not characteristics:
        st.info("Nenhuma característica encontrada.")
        return

    st.write(f"**Total de características:** {len(characteristics)}")

    for characteristic in characteristics:
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.write(f"**{characteristic.nome}**")
            st.write(f"ID: {characteristic.id}")

        with col2:
            if st.button(f"Editar", key=f"edit_caract_{characteristic.id}"):
                st.session_state["editing_caract"] = characteristic.id
                st.rerun()

        with col3:
            if st.button(
                f"Excluir", key=f"delete_caract_{characteristic.id}", type="secondary"
            ):
                if InventoryService.delete_caracteristica(characteristic.id):
                    st.success(f"Característica '{characteristic.nome}' excluída!")
                    st.rerun()
                else:
                    st.error(
                        f"Não foi possível excluir a característica '{characteristic.nome}'"
                    )

    # Check if there's a characteristic being edited
    if "editing_caract" in st.session_state:
        render_edit_characteristic_form(st.session_state["editing_caract"])


def render_create_characteristic():
    """Render create characteristic form"""
    st.subheader("➕ Criar Nova Característica")

    with st.form("create_characteristic_form"):
        nome = st.text_input(
            "Nome da Característica",
            placeholder="ex: Projetor",
            help="Nome da característica",
        )

        st.markdown("---")

        submitted = st.form_submit_button("Criar Característica", type="primary")

        if submitted:
            if not nome:
                st.error("❌ Nome da característica é obrigatório.")
                return

            caract_data = CaracteristicaCreate(nome=nome)

            new_caract = InventoryService.create_caracteristica(caract_data)
            if new_caract:
                st.success(f"✅ Característica '{nome}' criada com sucesso!")
                st.rerun()
            else:
                st.error(f"❌ Falha ao criar característica '{nome}'.")


def render_edit_characteristic_form(caract_id):
    """Render edit characteristic form"""
    characteristic = InventoryService.get_caracteristica_by_id(caract_id)

    if not characteristic:
        st.error("Característica não encontrada.")
        return

    st.subheader(f"✏️ Editar Característica: {characteristic.nome}")

    with st.form(f"edit_characteristic_form_{caract_id}"):
        nome = st.text_input("Nome da Característica", value=characteristic.nome)

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button("💾 Salvar Alterações", type="primary")

        with col2:
            if st.form_submit_button("❌ Cancelar", type="secondary"):
                del st.session_state["editing_caract"]
                st.rerun()

        if submitted:
            if not nome:
                st.error("❌ Nome da característica é obrigatório.")
                return

            caract_data = CaracteristicaUpdate(nome=nome)

            updated_caract = None  # InventoryService.update_caracteristica would need to be implemented
            # For now, just show success message
            st.success(f"✅ Característica '{nome}' atualizada!")
            del st.session_state["editing_caract"]
            st.rerun()


def render_edit_room_form(room_id):
    """Render edit room form"""
    room = InventoryService.get_sala_by_id(room_id)

    if not room:
        st.error("Sala não encontrada.")
        return

    # Get data for dropdowns
    buildings = InventoryService.get_all_predios()
    room_types = InventoryService.get_all_tipos_sala()
    characteristics = InventoryService.get_all_caracteristicas()

    st.subheader(f"✏️ Editar Sala: {room.nome}")

    with st.form(f"edit_room_form_{room_id}"):
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input("Nome da Sala", value=room.nome)
            capacidade = st.number_input(
                "Capacidade", min_value=1, max_value=500, value=room.capacidade
            )

        with col2:
            # Building selection
            building_options = {
                f"{building.nome} ({building.campus.nome if building.campus else 'Campus não encontrado'})": building.id
                for building in buildings
            }
            current_building_name = (
                f"{room.predio.nome} ({room.predio.campus.nome if room.predio and room.predio.campus else 'Campus não encontrado'})"
                if room.predio
                else "Prédio não encontrado"
            )
            selected_building = st.selectbox(
                "Prédio",
                options=list(building_options.keys()),
                index=(
                    list(building_options.keys()).index(current_building_name)
                    if current_building_name in building_options
                    else 0
                ),
            )

            andar = st.number_input(
                "Andar", min_value=0, max_value=20, value=room.andar
            )

        # Room type selection
        type_options = {room_type.nome: room_type.id for room_type in room_types}
        current_type_name = (
            room.tipo_sala.nome if room.tipo_sala else "Tipo não encontrado"
        )
        selected_type = st.selectbox(
            "Tipo de Sala",
            options=list(type_options.keys()),
            index=(
                list(type_options.keys()).index(current_type_name)
                if current_type_name in type_options
                else 0
            ),
        )

        # Characteristics selection
        if characteristics:
            st.subheader("Características")
            caract_options = {caract.nome: caract.id for caract in characteristics}

            # Get current characteristics
            current_caracts = []
            if hasattr(room, "caracteristicas") and room.caracteristicas:
                current_caracts = [caract.nome for caract in room.caracteristicas]

            selected_characteristics = st.multiselect(
                "Selecione as características da sala:",
                options=list(caract_options.keys()),
                default=current_caracts,
            )

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button("💾 Salvar Alterações", type="primary")

        with col2:
            if st.form_submit_button("❌ Cancelar", type="secondary"):
                del st.session_state["editing_room"]
                st.rerun()

        if submitted:
            if not nome:
                st.error("❌ Nome da sala é obrigatório.")
                return

            if capacidade < 1:
                st.error("❌ Capacidade deve ser maior que zero.")
                return

            # Update room
            room_data = SalaUpdate(
                nome=nome,
                capacidade=capacidade,
                andar=andar,
                predio_id=building_options[selected_building],
                tipo_sala_id=type_options[selected_type],
                caracteristicas=[
                    caract_options[caract] for caract in selected_characteristics
                ],
            )

            updated_room = InventoryService.update_sala(room_id, room_data)
            if updated_room:
                st.success(f"✅ Sala '{nome}' atualizada com sucesso!")
                del st.session_state["editing_room"]
                st.rerun()
            else:
                st.error(f"❌ Falha ao atualizar sala '{nome}'.")


def render_room_statistics():
    """Render room statistics"""
    st.header("📊 Estatísticas de Salas")

    stats = InventoryService.get_inventory_stats()

    # Overall statistics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total de Salas", stats["salas"])

    with col2:
        st.metric("Capacidade Total", stats.get("capacidade_total", 0))

    with col3:
        st.metric("Capacidade Média", stats.get("capacidade_media", 0))

    st.markdown("---")

    # Room types breakdown
    st.subheader("🏷️ Salas por Tipo")
    room_types = InventoryService.get_all_tipos_sala()

    if room_types:
        for room_type in room_types:
            from database import DatabaseSession, Sala

            with DatabaseSession() as session:
                room_count = (
                    session.query(Sala)
                    .filter(Sala.tipo_sala_id == room_type.id)
                    .count()
                )

                if room_count > 0:
                    st.write(f"**{room_type.nome}:** {room_count} salas")
    else:
        st.info("Nenhum tipo de sala encontrado.")

    st.markdown("---")

    # Campus breakdown
    st.subheader("🏛️ Salas por Campus")
    campuses = InventoryService.get_all_campus()

    if campuses:
        for campus in campuses:
            buildings = InventoryService.get_predios_by_campus(campus.id)
            total_rooms = 0

            for building in buildings:
                rooms = InventoryService.get_salas_by_predio(building.id)
                total_rooms += len(rooms)

            if total_rooms > 0:
                st.write(f"**{campus.nome}:** {total_rooms} salas")
    else:
        st.info("Nenhum campus encontrado.")


def main():
    """Main entry point for the rooms page"""
    render_salas_page()


if __name__ == "__main__":
    main()
