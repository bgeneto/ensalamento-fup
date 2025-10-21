"""
Preferences Management Page

Configure professor and courses preferences.

Route: /pages/4_📌_Preferências.py
URL: ?page=Professores
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
    # navigate back to main page where login widget is located
    st.switch_page("main.py")
    st.stop()

# Call login with unrendered location to maintain session (required for page refresh fix)
try:
    authenticator.login(location="unrendered", key="authenticator-preferencias")
except Exception as exc:
    st.error(f"❌ Erro de autenticação: {exc}")
    st.stop()

auth_status = st.session_state.get("authentication_status")

if auth_status:
    # Show logout button in sidebar
    authenticator.logout(location="sidebar", key="logout-preferencias")
elif auth_status is False:
    st.error("❌ Acesso negado.")
    st.stop()
else:
    # Not authenticated - redirect to main page
    st.warning("👈 Por favor, faça login na página inicial para acessar o sistema.")
    st.page_link("main.py", label="Voltar para o início ↩", icon="🏠")
    # navigate back to main page where login widget is located
    st.switch_page("main.py")
    st.stop()


# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Preferências - Ensalamento",
    page_icon="📌",
    layout="wide",
)

# ============================================================================
# IMPORTS
# ============================================================================

from src.repositories.professor import ProfessorRepository
from src.repositories.regra import RegraRepository
from src.repositories.sala import SalaRepository
from src.repositories.caracteristica import CaracteristicaRepository
from src.repositories.tipo_sala import TipoSalaRepository
from src.repositories.predio import PredioRepository
from src.repositories.disciplina import DisciplinaRepository
from src.schemas.academic import ProfessorCreate
from src.schemas.allocation import RegraCreate, RegraRead
from src.models.academic import Professor
from src.models.inventory import Sala, Caracteristica, TipoSala
from src.models.allocation import Regra
from src.config.database import get_db_session
from src.utils.ui_feedback import (
    display_session_feedback,
    set_session_feedback,
)
import json


def format_rule_display(
    regra: RegraRead,
    salas_dict: dict,
    tipos_sala_dict: dict,
    caracteristicas_dict: dict,
) -> str:
    """Create user-friendly display for a rule instead of showing raw JSON."""
    config = regra.get_config()

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

    else:
        # Unknown rule type - fallback to generic
        return f"{regra.tipo_regra}: {regra.descricao}"


# ============================================================================
# PAGE HEADER
# ============================================================================

st.title("📌 Gerenciamento de Preferências")
st.markdown(
    "Gerencie as preferências de professores e disciplinas em relação às salas."
)

# ============================================================================
# TABS STRUCTURE
# ============================================================================

tab1, tab2 = st.tabs(["👨‍🏫 Professores", "📚 Disciplinas"])

# =============================================================================
# TAB 1: PROFESSOR PREFERENCES
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
                from src.models.inventory import Sala, Predio

                salas_orm = (
                    session.query(Sala).join(Predio, Sala.predio_id == Predio.id).all()
                )
                salas_options = {
                    sala.id: f"{sala.predio.nome}/{sala.nome}" for sala in salas_orm
                }

                st.subheader("Preferências dos Professores")

                # Select professor to manage preferences
                prof_options = {prof.id: prof.nome_completo for prof in professores}
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
                                f"Preferências de {current_prof.nome_completo} atualizadas com sucesso!",
                            )
                            st.rerun()

                # Display feedback
                display_session_feedback("prof_prefs")

                st.markdown("---")

                st.write("### 📋 Listagem das Preferências dos Professores")

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

                st.dataframe(
                    prof_data,
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
# TAB 2: DISCIPLINE PREFERENCES (RULES)
# =============================================================================

with tab2:
    st.subheader("Preferências de Disciplinas")
    st.markdown(
        "Configure regras de alocação focadas em disciplinas (regras estáticas/duras e dinâmicas/suaves)."
    )

    try:
        with get_db_session() as session:
            # Initialize repositories
            regra_repo = RegraRepository(session)
            sala_repo = SalaRepository(session)
            tipo_sala_repo = TipoSalaRepository(session)
            caract_repo = CaracteristicaRepository(session)
            disc_repo = DisciplinaRepository(session)

            # Get data for lookups - use ORM objects to access related data like building names
            from src.models.inventory import Sala, Predio, Caracteristica, TipoSala

            salas_orm = (
                session.query(Sala).join(Predio, Sala.predio_id == Predio.id).all()
            )
            tipos_sala_orm = tipo_sala_repo.get_all()
            caracteristicas_orm = caract_repo.get_all()

            # Create lookup dictionaries
            salas = salas_orm  # Use full ORM objects
            tipos_sala = tipos_sala_orm
            caracteristicas = caracteristicas_orm
            # Get unique discipline codes from demands (we need to handle this carefully since the repo might not exist)
            disc_codes = []
            try:
                demandas = disc_repo.get_all()
                if demandas:
                    disc_codes = sorted(
                        list(set([d.codigo_disciplina for d in demandas]))
                    )
                else:
                    disc_codes = []
            except Exception as e:
                st.warning(f"Não foi possível carregar códigos de disciplina: {str(e)}")
            finally:
                # Always ensure we have some default options for testing
                if not disc_codes:
                    disc_codes = (
                        None  # Nenhum código de disciplina disponível na demanda atual
                    )

            # Create lookup dictionaries
            salas_dict = {sala.id: f"{sala.predio.nome}/{sala.nome}" for sala in salas}
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
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                rule_type_filter = st.selectbox(
                    "Filtrar por tipo:",
                    options=["Todos"]
                    + [
                        "DISCIPLINA_TIPO_SALA",
                        "DISCIPLINA_SALA",
                        "DISCIPLINA_CARACTERISTICA",
                    ],
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
                if "Duras" in rule_priority_filter:
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

                # Sort rules by priority ascending (hard rules first)
                filtered_regras.sort(
                    key=lambda x: (x.prioridade, x.tipo_regra, x.descricao)
                )

                for regra in filtered_regras:
                    # Create an expandable card for each rule
                    with st.expander(
                        f"{regra.id}: {format_rule_display(regra, salas_dict, tipos_sala_dict, {})}"
                    ):

                        col1, col2 = st.columns([3, 1])

                        with col1:
                            st.markdown(f"**Descrição:** {regra.descricao}")
                            st.markdown(f"**Tipo:** {regra.tipo_regra}")
                            st.markdown(
                                f"**Prioridade:** {regra.prioridade} ({'🏆 Dura' if regra.prioridade == 0 else f'⭐ Suave (P{regra.prioridade})'})"
                            )

                            # Show parsed configuration
                            config = regra.get_config()
                            if config:
                                st.markdown("**Configuração:**")
                                st.json(config)

                        with col2:
                            # Delete button for this rule
                            if st.button("🗑️ Apagar", key=f"delete_rule_{regra.id}"):

                                try:
                                    regra_repo.delete(regra.id)
                                    set_session_feedback(
                                        "rule_management",
                                        True,
                                        f"Regra '{regra.descricao}' removida com sucesso!",
                                    )
                                    st.rerun()
                                except Exception as e:
                                    set_session_feedback(
                                        "rule_management",
                                        False,
                                        f"Erro ao remover regra: {str(e)}",
                                    )

                st.markdown("---")
            else:
                st.info("📭 Nenhuma regra encontrada com os filtros aplicados.")
                st.markdown("---")

            # Add new rule form
            st.subheader("➕ Criar Nova Regra")

            # Use session state to make the rule type reactive outside the form
            if "selected_rule_type" not in st.session_state:
                st.session_state.selected_rule_type = "DISCIPLINA_TIPO_SALA"

            # Rule type selection outside the form for reactivity
            rule_type = st.selectbox(
                "Tipo de Regra:",
                options=[
                    "DISCIPLINA_TIPO_SALA",  # Hard: discipline must use room type
                    "DISCIPLINA_SALA",  # Hard: discipline must use specific room
                    "DISCIPLINA_CARACTERISTICA",  # Soft: discipline prefers room with characteristic
                ],
                format_func=lambda x: {
                    "DISCIPLINA_TIPO_SALA": "🔒 Regra Rígida: Tipo de Sala",
                    "DISCIPLINA_SALA": "🔒 Regra Rígida: Sala Específica",
                    "DISCIPLINA_CARACTERISTICA": "⭐ Preferência Suave: Característica",
                }.get(x, x),
                key="rule_type_selector",
                on_change=lambda: st.session_state.update(
                    {"selected_rule_type": st.session_state.rule_type_selector}
                ),
            )

            with st.form("new_rule_form", clear_on_submit=True):
                col1, col2 = st.columns(2)

                with col1:
                    # Rule type selection (inside form for submission)
                    rule_type_form = st.selectbox(
                        "Tipo de Regra:",
                        options=[
                            "DISCIPLINA_TIPO_SALA",  # Hard: discipline must use room type
                            "DISCIPLINA_SALA",  # Hard: discipline must use specific room
                            "DISCIPLINA_CARACTERISTICA",  # Soft: discipline prefers room with characteristic
                        ],
                        format_func=lambda x: {
                            "DISCIPLINA_TIPO_SALA": "🔒 Cobrança Dura - Tipo de Sala",
                            "DISCIPLINA_SALA": "🔒 Cobrança Dura - Sala Específica",
                            "DISCIPLINA_CARACTERISTICA": "⭐ Preferência Suave - Característica",
                        }.get(x, x),
                        index=[
                            "DISCIPLINA_TIPO_SALA",
                            "DISCIPLINA_SALA",
                            "DISCIPLINA_CARACTERISTICA",
                        ].index(rule_type),
                        key="rule_type_form",
                    )

                    # Description
                    descricao = st.text_input(
                        "Descrição da Regra:",
                        placeholder="Ex: Laboratório de Química deve usar sala de laboratório",
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
                        st.info(
                            "🔒 Regras de sala ou tipo têm prioridade 0 (obrigatórias)"
                        )

                # Dynamic fields based on rule type
                st.markdown("#### 🔧 Configuração Específica")

                if rule_type == "DISCIPLINA_SALA":
                    # Discipline must use specific room
                    col_a, col_b = st.columns(2)
                    with col_a:
                        selected_cod_disciplina = st.selectbox(
                            "Código da Disciplina:",
                            options=(
                                disc_codes
                                if disc_codes is not None
                                else ["Nenhuma disciplina na demanda"]
                            ),
                            disabled=disc_codes is None,
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
                            options=(
                                disc_codes
                                if disc_codes is not None
                                else ["Nenhuma disciplina na demanda"]
                            ),
                            disabled=disc_codes is None,
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
                            options=(
                                disc_codes
                                if disc_codes is not None
                                else ["Nenhuma disciplina na demanda"]
                            ),
                            disabled=disc_codes is None,
                            help="Disciplina afetada por esta regra",
                        )
                    with col_b:
                        selected_caracteristica = st.selectbox(
                            "Característica Preferida:",
                            options=caracteristicas_options,
                            help="Característica que a disciplina prefere ter na sala",
                        )

                # Submit button
                submitted = st.form_submit_button(
                    "💾 Criar Regra", type="primary", width="stretch"
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

                        set_session_feedback(
                            "rule_management",
                            True,
                            f"Regra '{descricao}' criada com sucesso!",
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
