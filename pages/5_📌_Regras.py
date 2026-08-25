"""
Preferences Management Page

Configure professor and courses preferences.
"""

from typing import Optional

import pandas as pd
import streamlit as st

from pages.components.auth import initialize_page
from pages.components.ui import page_footer

# Initialize page with authentication and configuration
if not initialize_page(
    page_title="Regras - Ensalamento",
    page_icon="📌",
    layout="wide",
    key_suffix="regras",
):
    st.stop()

# ============================================================================
# IMPORTS
# ============================================================================

import json

from src.config.database import get_db_session
from src.models.allocation import TIPO_REGRA_DISCIPLINA_SEM_SALA
from src.models.inventory import Caracteristica, Sala
from src.repositories.caracteristica import CaracteristicaRepository
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.predio import PredioRepository
from src.repositories.regra import RegraRepository
from src.repositories.sala import SalaRepository
from src.repositories.tipo_sala import TipoSalaRepository
from src.schemas.allocation import RegraCreate, RegraRead
from src.utils.ui_feedback import display_session_feedback, set_session_feedback

DISCIPLINE_RULE_TYPES = [
    "DISCIPLINA_TIPO_SALA",
    "DISCIPLINA_SALA",
    "DISCIPLINA_CARACTERISTICA",
    TIPO_REGRA_DISCIPLINA_SEM_SALA,
]
DISCIPLINE_RULE_TYPE_LABELS = {
    "DISCIPLINA_TIPO_SALA": "🔒 Obrigatória: Tipo de Sala",
    "DISCIPLINA_SALA": "🔒 Obrigatória: Sala Específica",
    "DISCIPLINA_CARACTERISTICA": "⭐ Preferência: Característica",
    TIPO_REGRA_DISCIPLINA_SEM_SALA: "🚫 Obrigatória: Não requer sala",
}
ROOM_CONSTRAINT_RULE_TYPES = {
    "DISCIPLINA_SALA",
    "DISCIPLINA_TIPO_SALA",
    "DISCIPLINA_CARACTERISTICA",
}


def _format_discipline_rule_type(rule_type: str) -> str:
    return DISCIPLINE_RULE_TYPE_LABELS.get(rule_type, rule_type)


def _generate_rule_description(
    rule_type: str,
    disc_code: str,
    sala_id: Optional[int],
    tipo_sala_id: Optional[int],
    caracteristica: str,
    prioridade: int,
    salas_dict: dict,
    tipos_sala_dict: dict,
) -> str:
    """Generate rule description based on form selections."""
    if rule_type == "DISCIPLINA_SALA":
        # Hard rule: discipline must use specific room
        sala_name = salas_dict.get(sala_id, f"ID {sala_id}")
        return f"🔒 Obrigatório: Disciplina {disc_code} deve usar sala {sala_name}"

    elif rule_type == "DISCIPLINA_TIPO_SALA":
        # Hard rule: discipline must use specific room type
        tipo_nome = tipos_sala_dict.get(tipo_sala_id, f"Tipo ID {tipo_sala_id}")
        return f"🔒 Obrigatório: Disciplina {disc_code} deve usar {tipo_nome}"

    elif rule_type == "DISCIPLINA_CARACTERISTICA":
        # Soft rule: discipline prefers room with characteristic
        prioridade_text = f"(Prioridade {prioridade})" if prioridade > 0 else ""
        return f"⭐ Prefere: Disciplina {disc_code} prefere salas com {caracteristica} {prioridade_text}"

    elif rule_type == TIPO_REGRA_DISCIPLINA_SEM_SALA:
        return f"🚫 Obrigatório: Disciplina {disc_code} não requer sala"

    else:
        # Fallback
        return f"Tipo de regra: {rule_type}"


@st.dialog("Confirmar Exclusão de Regra")
def confirm_delete_rule(regra: RegraRead, regra_repo: RegraRepository):
    """Dialog to confirm deletion of an allocation rule."""
    st.warning(f"Tem certeza que deseja excluir a regra '{regra.descricao}'?")

    st.write("**Esta ação irá:**")
    st.write("• Remover permanentemente esta regra de alocação")
    st.write("• Esta regra não afetará mais futuras alocações")

    # Show rule details
    with st.expander("Detalhes da Regra", expanded=True):
        st.write(f"**ID:** {regra.id}")
        st.write(f"**Tipo:** {regra.tipo_regra}")
        st.write(f"**Prioridade:** {regra.prioridade}")
        if regra.config_json:
            try:
                config = json.loads(regra.config_json)
                st.write("**Configuração:**")
                st.json(config)
            except (TypeError, ValueError, json.JSONDecodeError):
                st.write("*Não foi possível exibir configuração*")

    col_cancel, col_confirm = st.columns(2)

    with col_cancel:
        if st.button("Cancelar", width="stretch"):
            st.rerun()

    with col_confirm:
        if st.button("🗑️ Confirmar Exclusão", type="primary", width="stretch"):
            try:
                success = regra_repo.delete(regra.id)
                if success:
                    set_session_feedback(
                        "rule_delete",
                        True,
                        f"Regra '{regra.descricao}' excluída com sucesso",
                    )
                    st.rerun()
                else:
                    set_session_feedback(
                        "rule_delete",
                        False,
                        f"Falha ao excluir regra '{regra.descricao}'.",
                    )

            except Exception as e:
                set_session_feedback(
                    "rule_delete",
                    False,
                    f"Erro ao excluir regra: {str(e)}",
                )

            st.rerun()


def format_rule_display(
    regra: RegraRead,
    salas_dict: dict,
    tipos_sala_dict: dict,
    caracteristicas_dict: dict,
) -> str:
    """Create user-friendly display for a rule instead of showing raw JSON."""
    try:
        config = json.loads(regra.config_json) if regra.config_json else {}
    except (json.JSONDecodeError, TypeError):
        config = {}

    if regra.tipo_regra == "DISCIPLINA_SALA":
        # Hard rule: discipline must use specific room
        disc_code = config.get("codigo_disciplina", "N/A")
        sala_id = config.get("sala_id")
        sala_name = salas_dict.get(sala_id, f"ID {sala_id}")
        return f"🔒 Obrigatório: Disciplina {disc_code} deve usar sala {sala_name}"

    elif regra.tipo_regra == "DISCIPLINA_TIPO_SALA":
        # Hard rule: discipline must use specific room type
        disc_code = config.get("codigo_disciplina", "N/A")
        tipo_sala_id = config.get("tipo_sala_id")
        tipo_nome = tipos_sala_dict.get(tipo_sala_id, f"Tipo ID {tipo_sala_id}")
        return f"🔒 Obrigatório: Disciplina {disc_code} deve usar {tipo_nome}"

    elif regra.tipo_regra == "DISCIPLINA_CARACTERISTICA":
        # Soft rule: discipline prefers room with characteristic
        disc_code = config.get("codigo_disciplina", "N/A")
        caract_nome = config.get("caracteristica_nome", "N/A")
        prioridade = f"(Prioridade {regra.prioridade})" if regra.prioridade > 0 else ""
        return f"⭐ Prefere: Disciplina {disc_code} prefere salas com {caract_nome} {prioridade}"

    elif regra.tipo_regra == TIPO_REGRA_DISCIPLINA_SEM_SALA:
        disc_code = config.get("codigo_disciplina", "N/A")
        return f"🚫 Obrigatório: Disciplina {disc_code} não requer sala"

    else:
        # Unknown rule type - fallback to generic
        return f"{regra.tipo_regra}: {regra.descricao}"


# ============================================================================
# PAGE HEADER
# ============================================================================

st.title("📌 Gerenciamento de Regras")
st.markdown(
    "Gerencie as regras e/ou preferências de alocação de sala para professores e disciplinas."
)

# ============================================================================
# TABS STRUCTURE
# ============================================================================

tab1, tab2 = st.tabs(["👨‍🏫 Professores", "📚 Disciplinas"])

# =============================================================================
# TAB 1: PROFESSOR RULES
# =============================================================================

with tab1:
    try:
        with get_db_session() as session:
            # Get all professors - use ORM objects to access relationships
            from src.models.academic import Professor as ProfessorModel

            professores = session.query(ProfessorModel).all()

            if professores:
                # Get all rooms and characteristics for dropdowns
                sala_repo = SalaRepository(session)
                caract_repo = CaracteristicaRepository(session)
                predio_repo = PredioRepository(session)

                salas_dto = sala_repo.get_all()
                caracteristicas = caract_repo.get_all()
                predios = predio_repo.get_all()

                # Create lookup dictionaries
                predios_dict = {p.id: p.nome for p in predios}
                caracteristicas_options = {
                    caract.id: caract.nome for caract in caracteristicas
                }

                # Create rooms options with building names
                from src.models.inventory import Predio, Sala

                salas_orm = (
                    session.query(Sala).join(Predio, Sala.predio_id == Predio.id).all()
                )
                salas_options = {
                    sala.id: f"{sala.predio.nome}: {sala.nome}" for sala in salas_orm
                }

                st.subheader("✏️ Editar Preferências dos Professores")

                st.info(
                    """
                    ℹ️ Para editar as preferências/regras de um(a) professor(a):
                    - Selecione o nome do(a) professor(a) abaixo.
                    - Escolha uma ou mais salas preferidas e/ou uma ou mais características preferidas.
                    - Clique em **💾 Salvar Preferências** para gravar as preferências do(a) professor(a).
                    - Para remover uma ou mais preferências, simplesmente desmarque-as antes de salvar.
                    - A tabela abaixo exibe um resumo das preferências atuais de todos os professores cadastrados.
                    """
                )

                # Sort professors by name for the selectbox
                professores_sorted = sorted(professores, key=lambda x: x.nome_completo)

                # Select professor to manage preferences
                prof_options = {
                    prof.id: prof.nome_completo for prof in professores_sorted
                }
                selected_prof_id = st.selectbox(
                    "Selecione um professor para gerenciar preferências:",
                    options=[""] + list(prof_options.keys()),
                    format_func=lambda x: (
                        prof_options.get(x, "Escolha um professor...")
                        if x
                        else "Escolha um professor..."
                    ),
                )

                if selected_prof_id:
                    # Get current professor
                    from src.models.academic import Professor as ProfessorModel

                    current_prof = session.get(ProfessorModel, selected_prof_id)

                    if current_prof:
                        st.markdown(f"**Gerenciando:** {current_prof.nome_completo}")

                        # Get current preferences
                        current_salas = [
                            sala.id for sala in current_prof.salas_preferidas
                        ]
                        current_caracteristicas = [
                            caract.id
                            for caract in current_prof.caracteristicas_preferidas
                        ]

                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown("#### 🏢 Salas Preferidas")
                            # Multi-select for preferred rooms
                            selected_salas = st.multiselect(
                                "Selecione as salas preferidas:",
                                options=list(salas_options.keys()),
                                default=current_salas,
                                format_func=lambda x: salas_options.get(x, f"ID {x}"),
                            )

                        with col2:
                            st.markdown("#### 🎯 Características Preferidas")
                            # Multi-select for preferred characteristics
                            selected_caracteristicas = st.multiselect(
                                "Selecione as características preferidas:",
                                options=list(caracteristicas_options.keys()),
                                default=current_caracteristicas,
                                format_func=lambda x: caracteristicas_options.get(
                                    x, f"ID {x}"
                                ),
                            )

                        # Save button
                        if st.button(
                            "💾 Salvar Preferências",
                            type="primary",
                            width="content",
                        ):
                            # Update room preferences
                            # Get current room objects
                            new_salas = []
                            for sala_id in selected_salas:
                                sala_obj = session.get(Sala, sala_id)
                                if sala_obj:
                                    new_salas.append(sala_obj)

                            # Update characteristic preferences
                            new_caracteristicas = []
                            for caract_id in selected_caracteristicas:
                                caract_obj = session.get(Caracteristica, caract_id)
                                if caract_obj:
                                    new_caracteristicas.append(caract_obj)

                            # Update professor preferences
                            current_prof.salas_preferidas = new_salas
                            current_prof.caracteristicas_preferidas = (
                                new_caracteristicas
                            )

                            # Save changes
                            session.commit()

                            set_session_feedback(
                                "prof_prefs",
                                True,
                                f"Preferências de {current_prof.nome_completo} atualizadas com sucesso",
                            )
                            st.rerun()

                # Display feedback
                display_session_feedback("prof_prefs")

                st.markdown("---")

                st.write("### 👁️ Visualização das Preferências dos Professores")

                # Display summary
                st.markdown(f"**Total de professores: {len(professores)}**")

                # Create DataFrame for display
                prof_data = []
                for prof in professores:
                    # Get current preferences
                    sala_ids = [sala.id for sala in prof.salas_preferidas]
                    caracteristica_ids = [
                        caract.id for caract in prof.caracteristicas_preferidas
                    ]

                    prof_data.append(
                        {
                            "ID": prof.id,
                            "Professor": prof.nome_completo,
                            "Salas Preferidas": (
                                ", ".join(
                                    [
                                        salas_options[sid]
                                        for sid in sala_ids
                                        if sid in salas_options
                                    ]
                                )
                                if sala_ids
                                else "Nenhuma"
                            ),
                            "Características Preferidas": (
                                ", ".join(
                                    [
                                        caracteristicas_options[cid]
                                        for cid in caracteristica_ids
                                        if cid in caracteristicas_options
                                    ]
                                )
                                if caracteristica_ids
                                else "Nenhuma"
                            ),
                        }
                    )

                # Convert to DataFrame and sort by Professor name
                df_prof = pd.DataFrame(prof_data)
                df_prof = df_prof.sort_values(by=["Professor"]).reset_index(drop=True)

                st.dataframe(
                    df_prof,
                    width="stretch",
                    hide_index=True,
                    column_config={"ID": None},  # Hide the ID column
                )

            else:
                st.info("📭 Nenhum professor cadastrado ainda.")
                st.page_link(
                    "pages/3_👨‍🏫_Professores.py",
                    label="➕ Cadastrar professores primeiro",
                    icon="👥",
                )

    except Exception as e:
        st.error(f"❌ Erro ao carregar preferências de professores: {str(e)}")


# =============================================================================
# TAB 2: DISCIPLINE RULES
# =============================================================================

with tab2:
    st.subheader("📜 Regras e Preferências de Disciplinas")

    try:
        with get_db_session() as session:
            # Initialize repositories
            regra_repo = RegraRepository(session)
            sala_repo = SalaRepository(session)
            tipo_sala_repo = TipoSalaRepository(session)
            caract_repo = CaracteristicaRepository(session)
            disc_repo = DisciplinaRepository(session)

            # Get data for lookups - use ORM objects to access related data like building names
            from src.models.inventory import Caracteristica, Predio, Sala

            salas_orm = (
                session.query(Sala).join(Predio, Sala.predio_id == Predio.id).all()
            )
            tipos_sala_orm = tipo_sala_repo.get_all()
            caracteristicas_orm = caract_repo.get_all()

            # Create lookup dictionaries
            salas = salas_orm  # Use full ORM objects
            tipos_sala = tipos_sala_orm
            caracteristicas = caracteristicas_orm
            # Get unique discipline codes and names from demands
            disc_options = {}
            try:
                demandas = disc_repo.get_all()
                if demandas:
                    # Create mapping of code -> "code - name" for selectbox display
                    for demanda in demandas:
                        code = demanda.codigo_disciplina
                        name = demanda.nome_disciplina or "Nome não informado"
                        display_text = f"{code} - {name}"
                        disc_options[code] = display_text

                    # Sort by code for consistent ordering
                    disc_options = dict(sorted(disc_options.items()))
                else:
                    disc_options = {}
            except Exception as e:
                st.warning(f"Não foi possível carregar códigos de disciplina: {str(e)}")
                disc_options = {}
            finally:
                # Ensure we have some options for the selectbox
                if not disc_options:
                    disc_options = {"": "Nenhuma disciplina na demanda atual"}

            # Create lookup dictionaries
            salas_dict = {sala.id: f"{sala.predio.nome}: {sala.nome}" for sala in salas}
            tipos_sala_dict = {tipo.id: tipo.nome for tipo in tipos_sala}
            caracteristicas_options = [
                caract.nome for caract in caracteristicas
            ]  # List for selectbox

            # Get existing rules
            regras = regra_repo.get_all()
            stats = regra_repo.get_statistics()

            # Display statistics and summary
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total de Regras", stats["total_regras"])
            with col2:
                st.metric("Regras Rígidas", f"{stats['regras_duras']} 🔒")
            with col3:
                st.metric("Regras Suaves", f"{stats['regras_suaves']} ⭐")
            with col4:
                st.metric("Tipos Distintos", stats["tipos_distintos"])

            # Filter controls
            col1, col2, col3 = st.columns(3)
            with col1:
                rule_type_filter = st.selectbox(
                    "Filtrar por tipo:",
                    options=["Todos"] + DISCIPLINE_RULE_TYPES,
                    format_func=lambda x: (
                        "Todos" if x == "Todos" else _format_discipline_rule_type(x)
                    ),
                )
            with col2:
                rule_priority_filter = st.selectbox(
                    "Filtrar por prioridade:",
                    options=[
                        "Todos",
                        "Rígidas (prioridade=0)",
                        "Suaves (prioridade>0)",
                    ],
                )
            with col3:
                search_term = st.text_input(
                    "Buscar na descrição:", placeholder="Digite termo..."
                )

            # Apply filters
            filtered_regras = regras
            if rule_type_filter != "Todos":
                filtered_regras = [
                    r for r in filtered_regras if r.tipo_regra == rule_type_filter
                ]
            if rule_priority_filter != "Todos":
                if "Rígidas" in rule_priority_filter:
                    filtered_regras = [r for r in filtered_regras if r.prioridade == 0]
                else:
                    filtered_regras = [r for r in filtered_regras if r.prioridade > 0]
            if search_term:
                filtered_regras = [
                    r
                    for r in filtered_regras
                    if search_term.lower() in str(r.descricao).lower()
                ]

            # Display existing rules
            if filtered_regras:
                st.markdown("### 📋 Regras Existentes")

                st.info(
                    """
                    ℹ️ A lista abaixo exibe as regras de alocação de disciplinas com base nos filtros aplicados acima.
                    - Cada regra pode ser expandida para ver detalhes completos.
                    - Ao expandir uma regra, use o botão **🗑️ Apagar Regra** para remover uma regra indesejada.
                    """
                )

                # Sort rules by ID ascending
                filtered_regras.sort(key=lambda x: x.id)

                for regra in filtered_regras:
                    # Create an expandable card for each rule
                    with st.expander(
                        f"{regra.id}: {format_rule_display(regra, salas_dict, tipos_sala_dict, {})}"
                    ):
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            # Extract discipline code from config and show name
                            try:
                                config = (
                                    json.loads(regra.config_json)
                                    if regra.config_json
                                    else {}
                                )
                                cod_disc = config.get("codigo_disciplina", "")
                                if cod_disc and cod_disc in disc_options:
                                    st.markdown(
                                        f"**Disciplina:** {disc_options[cod_disc]}"
                                    )
                                elif cod_disc:
                                    st.markdown(f"**Disciplina:** {cod_disc}")
                            except (json.JSONDecodeError, TypeError):
                                pass

                            st.markdown(f"**Descrição:** {regra.descricao}")
                            st.markdown(f"**Tipo:** {regra.tipo_regra}")
                            st.markdown(
                                f"**Prioridade:** {regra.prioridade} ({'🏆 Rígida' if regra.prioridade == 0 else f'⭐ Preferência (P{regra.prioridade})'})"
                            )

                            # Show parsed configuration
                            try:
                                config = (
                                    json.loads(regra.config_json)
                                    if regra.config_json
                                    else {}
                                )
                                if config:
                                    st.markdown("**Configuração:**")
                                    st.json(config)
                            except (json.JSONDecodeError, TypeError):
                                st.markdown("*Não foi possível exibir configuração*")

                        with col2:
                            # Delete button for this rule
                            if st.button(
                                "🗑️ Apagar Regra", key=f"delete_rule_{regra.id}"
                            ):
                                confirm_delete_rule(regra, regra_repo)

                        # Display rule delete feedback messages
                        display_session_feedback("rule_delete")

                st.markdown("---")
            else:
                st.info("📭 Nenhuma regra encontrada com os filtros aplicados.")
                st.markdown("---")

            # Add new rule form
            st.subheader("➕ Criar Nova Regra")

            st.info(
                """
                ℹ️ Para adicionar regras a uma disciplina:
                - As regras podem ser rígidas (obrigatórias) ou suaves (preferências).
                - Selecione primeiro o tipo de regra: **Sala Específica** (rígida), **Tipo de Sala** (rígida), **Característica da Sala** (suave) ou **Não requer sala** (rígida).
                - Selecione a disciplina por código ou nome da disciplina.
                - Selecione a sala, tipo de sala ou característica conforme o tipo de regra escolhido. Para **Não requer sala**, apenas a disciplina é necessária.
                - Disciplinas com a regra **Não requer sala** são excluídas da alocação autônoma e do assistente (todas as turmas e semestres).
                - Para regras suaves, você pode definir uma prioridade (número maior = prioridade mais alta).
                - Clique em **💾 Criar Regra** para salvar a nova regra.
                - A descrição da regra será gerada automaticamente com base nas suas seleções.
                """
            )
            # Use session state to store the reactive rule type selection
            if "rule_type_reactive" not in st.session_state:
                st.session_state.rule_type_reactive = "DISCIPLINA_TIPO_SALA"

            # Initialize form selectbox value if not present
            if "rule_type_form" not in st.session_state:
                st.session_state.rule_type_form = st.session_state.rule_type_reactive

            if st.session_state.rule_type_reactive not in DISCIPLINE_RULE_TYPES:
                st.session_state.rule_type_reactive = DISCIPLINE_RULE_TYPES[0]
            if st.session_state.rule_type_form not in DISCIPLINE_RULE_TYPES:
                st.session_state.rule_type_form = st.session_state.rule_type_reactive

            # Reactive rule type selection (outside form for immediate reactivity)
            rule_type_reactive = st.selectbox(
                "Selecionar tipo de regra:",
                options=DISCIPLINE_RULE_TYPES,
                format_func=_format_discipline_rule_type,
                key="rule_type_reactive_selectbox",
                index=DISCIPLINE_RULE_TYPES.index(
                    st.session_state.rule_type_reactive
                ),
            )

            # Update session state when reactive selectbox changes
            if rule_type_reactive != st.session_state.rule_type_reactive:
                st.session_state.rule_type_reactive = rule_type_reactive
                st.session_state.rule_type_form = rule_type_reactive
                st.rerun()

            with st.form("new_rule_form", clear_on_submit=True):
                col1, col2 = st.columns(2)

                with col1:
                    # Rule type selection (inside form, synced with reactive selectbox)
                    rule_type = st.selectbox(
                        "Tipo de Regra:",
                        options=DISCIPLINE_RULE_TYPES,
                        format_func=_format_discipline_rule_type,
                        key="rule_type_form",
                        index=DISCIPLINE_RULE_TYPES.index(
                            st.session_state.rule_type_form
                        ),
                        disabled=True,  # Prevent users from modifying this - use external selectbox
                        help="Use o seletor acima para escolher o tipo de regra",
                    )

                with col2:
                    if rule_type == "DISCIPLINA_CARACTERISTICA":
                        # For soft rules, allow priority selection
                        prioridade = st.number_input(
                            "Prioridade:",
                            min_value=1,
                            value=1,
                            max_value=10,
                            help="número maior = prioridade mais alta",
                        )
                    else:
                        # Hard rules are always priority 0
                        prioridade = 0
                        if rule_type == TIPO_REGRA_DISCIPLINA_SEM_SALA:
                            st.info(
                                "🚫 Disciplinas que não requerem sala têm prioridade 0 "
                                "e são excluídas do ensalamento"
                            )
                        else:
                            st.info(
                                "🔒 Regras de sala específica ou tipo têm prioridade 0 (obrigatórias)"
                            )

                # Dynamic fields based on rule type
                st.markdown("#### 🔧 Configuração Específica")

                if rule_type == "DISCIPLINA_SALA":
                    # Discipline must use specific room
                    col_a, col_b = st.columns(2)
                    with col_a:
                        selected_cod_disciplina = st.selectbox(
                            "Código da Disciplina:",
                            options=list(disc_options.keys()) if disc_options else [],
                            format_func=lambda x: (
                                disc_options.get(x, x) if disc_options else x
                            ),
                            help="Disciplina afetada por esta regra",
                        )
                    with col_b:
                        selected_sala_id = st.selectbox(
                            "Sala Obrigatória:",
                            options=list(salas_dict.keys()),
                            format_func=lambda x: salas_dict.get(x, f"ID {x}"),
                            help="Sala que deve ser usada obrigatoriamente",
                        )

                elif rule_type == "DISCIPLINA_TIPO_SALA":
                    # Discipline must use specific room type
                    col_a, col_b = st.columns(2)
                    with col_a:
                        selected_cod_disciplina = st.selectbox(
                            "Código da Disciplina:",
                            options=list(disc_options.keys()) if disc_options else [],
                            format_func=lambda x: (
                                disc_options.get(x, x) if disc_options else x
                            ),
                            help="Disciplina afetada por esta regra",
                        )
                    with col_b:
                        selected_tipo_sala_id = st.selectbox(
                            "Tipo de Sala Obrigatório:",
                            options=list(tipos_sala_dict.keys()),
                            format_func=lambda x: tipos_sala_dict.get(
                                x, f"Tipo ID {x}"
                            ),
                            help="Tipo de sala que deve ser usado obrigatoriamente",
                        )

                elif rule_type == "DISCIPLINA_CARACTERISTICA":
                    # Soft preference for characteristic
                    col_a, col_b = st.columns(2)
                    with col_a:
                        selected_cod_disciplina = st.selectbox(
                            "Código da Disciplina:",
                            options=list(disc_options.keys()) if disc_options else [],
                            format_func=lambda x: (
                                disc_options.get(x, x) if disc_options else x
                            ),
                            help="Disciplina afetada por esta regra",
                        )
                    with col_b:
                        selected_caracteristica = st.selectbox(
                            "Característica Preferida:",
                            options=caracteristicas_options,
                            help="Característica que a disciplina prefere ter na sala",
                        )

                elif rule_type == TIPO_REGRA_DISCIPLINA_SEM_SALA:
                    selected_cod_disciplina = st.selectbox(
                        "Código da Disciplina:",
                        options=list(disc_options.keys()) if disc_options else [],
                        format_func=lambda x: (
                            disc_options.get(x, x) if disc_options else x
                        ),
                        help="Todas as turmas desta disciplina serão excluídas da alocação de salas",
                    )
                    st.caption(
                        "Esta disciplina será excluída da alocação autônoma e do assistente. "
                        "A regra vale para todas as turmas e semestres. "
                        "Alocações já existentes não são removidas automaticamente."
                    )

                # Auto-generate description (last field in form)
                generated_description = _generate_rule_description(
                    rule_type,
                    (
                        selected_cod_disciplina
                        if "selected_cod_disciplina" in locals()
                        else ""
                    ),
                    selected_sala_id if "selected_sala_id" in locals() else None,
                    (
                        selected_tipo_sala_id
                        if "selected_tipo_sala_id" in locals()
                        else None
                    ),
                    (
                        selected_caracteristica
                        if "selected_caracteristica" in locals()
                        else ""
                    ),
                    prioridade,
                    salas_dict,
                    tipos_sala_dict,
                )

                # Description field (auto-filled and disabled)
                descricao = st.text_area(
                    "Descrição da Regra (gerada automaticamente):",
                    value=generated_description,
                    height=60,
                    disabled=True,
                    help="Esta descrição é gerada automaticamente baseada nas suas seleções acima",
                )

                # Submit button
                submitted = st.form_submit_button(
                    "💾 Criar Regra", type="primary", width="content"
                )

                if submitted:
                    # Validate and create rule
                    if not descricao.strip():
                        st.error("❌ Descrição é obrigatória")
                        st.stop()

                    # Build configuration JSON
                    if rule_type == "DISCIPLINA_SALA":
                        config = {
                            "codigo_disciplina": selected_cod_disciplina,
                            "sala_id": selected_sala_id,
                        }
                    elif rule_type == "DISCIPLINA_TIPO_SALA":
                        config = {
                            "codigo_disciplina": selected_cod_disciplina,
                            "tipo_sala_id": selected_tipo_sala_id,
                        }
                    elif rule_type == "DISCIPLINA_CARACTERISTICA":
                        config = {
                            "codigo_disciplina": selected_cod_disciplina,
                            "caracteristica_nome": selected_caracteristica,
                        }
                    elif rule_type == TIPO_REGRA_DISCIPLINA_SEM_SALA:
                        config = {
                            "codigo_disciplina": selected_cod_disciplina,
                        }
                    else:
                        st.error(f"❌ Tipo de regra desconhecido: {rule_type}")
                        st.stop()

                    # Create the rule
                    try:
                        regra_dto = RegraCreate(
                            descricao=descricao.strip(),
                            tipo_regra=rule_type,
                            config_json=json.dumps(config, ensure_ascii=False),
                            prioridade=prioridade,
                        )
                        regra_repo.create(regra_dto)

                        success_message = f"Regra '{descricao}' criada com sucesso"
                        if rule_type == TIPO_REGRA_DISCIPLINA_SEM_SALA:
                            existing_rules = regra_repo.find_rules_by_disciplina(
                                selected_cod_disciplina
                            )
                            has_room_rules = any(
                                r.tipo_regra in ROOM_CONSTRAINT_RULE_TYPES
                                for r in existing_rules
                            )
                            if has_room_rules:
                                success_message += (
                                    ". Atenção: já existem outras regras de sala/tipo "
                                    "para esta disciplina; a exclusão prevalece."
                                )

                        set_session_feedback(
                            "rule_management",
                            True,
                            success_message,
                        )
                        st.rerun()

                    except Exception as e:
                        set_session_feedback(
                            "rule_management",
                            False,
                            f"Erro ao criar regra: {str(e)}",
                        )

            # Display feedback
            display_session_feedback("rule_management")

    except Exception as e:
        st.error(f"❌ Erro ao carregar preferências de disciplinas: {str(e)}")

# Page Footer
page_footer.show()
