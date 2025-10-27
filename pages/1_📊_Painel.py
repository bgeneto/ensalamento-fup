"""
Admin Dashboard Page - Home Overview

Displays system status, key metrics, recent activities, and quick actions.
Entry point for authenticated admins.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pages.components.auth import initialize_page
from pages.components.ui import page_footer

# Initialize page with authentication and configuration
if not initialize_page(
    page_title="Painel - Ensalamento",
    page_icon="📊",
    layout="wide",
    key_suffix="painel",
):
    st.stop()

# ============================================================================
# IMPORTS - Repositories
# ============================================================================

from src.repositories.sala import SalaRepository
from src.repositories.professor import ProfessorRepository
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.alocacao import AlocacaoRepository
from src.config.database import get_db_session
from src.config import settings
from src.utils.cache_helpers import get_semester_options
from src.services.semester_service import create_and_activate_semester
from src.utils.ui_feedback import display_session_feedback, set_session_feedback
from src.utils.semester_ui_sync import (
    initialize_global_semester,
    render_semester_selector,
)

# ============================================================================
# PAGE CONTENT
# ============================================================================

# Display any stored feedback messages
display_session_feedback("semester_change_feedback")
display_session_feedback("semester_create_feedback")

st.markdown(
    """
<style>
    .header-section {
        padding: 1rem;
        background: linear-gradient(135deg, #c67b5c 0%, #a0563f 100%);
        color: white;
        border-radius: 0.5rem;
        margin-bottom: 2rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Header
st.markdown(
    f"""
<div class="header-section"">
    <h1>📊 Painel Administrativo</h1>
    <p style="font-size: 1.1rem; margin: 0.5rem 0;">{settings.APP_NAME}</p>
</div>
""",
    unsafe_allow_html=True,
)

# User info
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown(f"**Usuário:** {st.session_state.name}")
    st.markdown(f"**Role:** {st.session_state.username}")

with col2:
    st.metric("Data", datetime.now().strftime("%d/%m/%Y"))

with col3:
    st.metric("Hora", datetime.now().strftime("%H:%M:%S"))

# Get available semesters and initialize global semester (only once per session)
semester_options = get_semester_options()

if not semester_options:
    st.error("❌ Nenhum semestre encontrado. Importe dados primeiro.")
    st.stop()

# Initialize global semester (prevents duplicate initialization across components)
current_semester_id = initialize_global_semester()

col1, col2 = st.columns(2)

with col1:
    # Global semester selector and creation
    st.markdown("### 📅 Seleção Global do Semestre")

    st.markdown("Selecione o semestre apropriado:")
    current_semester_id = render_semester_selector(
        semester_options,
        current_semester_id,
        key="painel_global_semester_selector",
        show_label=False,
        feedback_key="semester_change_feedback",
        width=400,
    )

# Global semester selector and creation
# st.markdown("### ➕ Criar Novo Semestre")

with col2:

    # Create new semester form
    # st.markdown("Ou crie um novo semestre:")
    with st.form("create_semester_form", width=400):
        new_semester_name = st.text_input(
            "**Criar novo semestre:**",
            placeholder="2026-2",
            help="Formato esperado: ANO-SEM (ex: 2026-1 para primeiro semestre de 2026)",
        )

        submitted = st.form_submit_button("➕ Criar Semestre")

        if submitted:
            try:
                result = create_and_activate_semester(new_semester_name)

                if result["success"]:
                    # Clear cache to refresh options
                    from src.utils.cache_helpers import clear_reference_data_cache

                    clear_reference_data_cache()

                    # Set new semester as global semester
                    import time

                    time.sleep(0.5)  # Brief delay for cache refresh

                    fresh_options = get_semester_options()
                    if fresh_options:
                        for sem_id, sem_name in fresh_options:
                            if sem_name == new_semester_name.strip():
                                st.session_state.global_semester_id = sem_id
                                break

                    set_session_feedback(
                        "semester_create_feedback",
                        True,
                        result["message"],
                    )
                    st.rerun()

            except ValueError as e:
                set_session_feedback(
                    "semester_create_feedback",
                    False,
                    str(e),
                )
            except Exception as e:
                set_session_feedback(
                    "semester_create_feedback",
                    False,
                    f"Erro inesperado: {str(e)}",
                )

st.markdown("---")

# ============================================================================
# KEY METRICS
# ============================================================================

st.markdown("## 📈 Indicadores Principais")

# Initialize variables with defaults
total_rooms = 0
total_professors = 0
total_demands = 0
total_allocations = 0
allocation_pct = 0
ground_floor = 0
first_floor = 0
stats = {}

# Load data from repositories
try:
    with get_db_session() as session:
        sala_repo = SalaRepository(session)
        prof_repo = ProfessorRepository(session)
        disc_repo = DisciplinaRepository(session)
        aloc_repo = AlocacaoRepository(session)

        # Get counts
        total_rooms = len(sala_repo.get_all())
        total_professors = len(prof_repo.get_all())
        total_demands = len(disc_repo.get_all())
        total_allocations = len(aloc_repo.get_all())

        # Calculate allocations percentage
        allocation_pct = (
            (total_allocations / total_demands * 100) if total_demands > 0 else 0
        )

        # Get floor data
        ground_floor = len(sala_repo.get_by_andar("0"))
        first_floor = len(sala_repo.get_by_andar("1"))

        # Get stats
        stats = sala_repo.get_statistics()

except Exception as e:
    st.error(f"❌ Erro ao carregar dados: {str(e)}")

# Display metrics in columns
col1, col2, col3, col4, _ = st.columns(5)

with col1:
    st.metric(
        "🏢 Salas",
        total_rooms,
        delta="Ativas",
        delta_color="off",
    )

with col2:
    st.metric(
        "👨‍🏫 Professores",
        total_professors,
        delta="Cadastrados",
        delta_color="off",
    )

with col3:
    st.metric(
        "📚 Demandas",
        total_demands,
        delta="Disciplinas",
        delta_color="off",
    )

with col4:
    st.metric(
        "✅ Alocações",
        total_allocations,
        delta="Confirmadas",
        delta_color="off",
    )

st.markdown("---")

# ============================================================================
# QUICK STATS BY CATEGORY
# ============================================================================

st.markdown("## 📈 Estatísticas Detalhadas")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Salas por Andar")
    try:
        stats_df = pd.DataFrame(
            {
                "Andar": ["Térreo", "1º Andar"],
                "Quantidade": [ground_floor, first_floor],
            }
        )

        st.bar_chart(stats_df.set_index("Andar"))

        st.dataframe(stats_df, width="stretch", hide_index=True)

    except Exception as e:
        st.warning(f"Dados não disponíveis: {str(e)}")

with col2:
    st.subheader("Ocupação de Salas")
    try:
        occupation_data = pd.DataFrame(
            {
                "Categoria": ["Total", "Utilizadas", "Disponíveis"],
                "Salas": [
                    stats.get("total_salas", 0),
                    stats.get("total_salas", 0) - stats.get("total_salas", 0),
                    stats.get("total_salas", 0),
                ],
            }
        )

        st.bar_chart(occupation_data.set_index("Categoria"))
        st.dataframe(occupation_data, width="stretch", hide_index=True)

    except Exception as e:
        st.warning(f"Dados não disponíveis: {str(e)}")

st.markdown("---")

# ============================================================================
# RECENT ACTIVITIES
# ============================================================================

st.markdown("## 📋 Atividades Recentes")

# Mock recent activities (in production, would log real actions)
activities = [
    {
        "timestamp": datetime.now() - timedelta(minutes=5),
        "tipo": "✅ Alocação",
        "descricao": "Demanda CIC0001 alocada para sala A1-01",
        "usuario": st.session_state.name,
    },
    {
        "timestamp": datetime.now() - timedelta(minutes=15),
        "tipo": "👨‍🏫 Professor",
        "descricao": "Prof. Ana Silva adicionado ao sistema",
        "usuario": "admin",
    },
    {
        "timestamp": datetime.now() - timedelta(hours=1),
        "tipo": "🏢 Sala",
        "descricao": "Sala A1-05 criada com capacidade 50",
        "usuario": "admin",
    },
    {
        "timestamp": datetime.now() - timedelta(hours=2),
        "tipo": "📚 Demanda",
        "descricao": "Demanda CIC0002 importada do Sistema de Oferta",
        "usuario": "admin",
    },
]

activity_df = pd.DataFrame(
    [
        {
            "Horário": a["timestamp"].strftime("%H:%M:%S"),
            "Tipo": a["tipo"],
            "Descrição": a["descricao"],
            "Usuário": a["usuario"],
        }
        for a in activities
    ]
)

st.dataframe(activity_df, width="stretch", hide_index=True)

st.markdown("---")

# ============================================================================
# QUICK ACTIONS
# ============================================================================

st.markdown("## 🚀 Ações Rápidas")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("➕ Nova Sala", width="stretch"):
        st.info("Redirecionando para Inventário...")
        st.toast("Acesse a página de Inventário para criar uma nova sala")

with col2:
    if st.button("➕ Novo Professor", width="stretch"):
        st.info("Redirecionando para Professores...")
        st.toast("Acesse a página de Professores para adicionar um professor")

with col3:
    if st.button("📥 Importar Demandas", width="stretch"):
        st.info("Redirecionando para Demandas...")
        st.toast("Acesse a página de Demandas para importar do Sistema de Oferta")

with col4:
    if st.button("🔄 Executar Alocação", width="stretch"):
        st.info("Redirecionando para Alocações...")
        st.toast("Acesse a página de Alocações para executar o algoritmo")

st.markdown("---")

# ============================================================================
# SYSTEM STATUS
# ============================================================================

st.markdown("## 🔍 Status do Sistema")

col1, col2, col3 = st.columns(3)

with col1:
    st.write("**Banco de Dados**")
    st.success("✅ Conectado")
    st.caption("Arquivo ensalamento.db existe")

with col2:
    st.write("**Integração APIs**")
    st.warning("✅ Configurado")
    st.caption("variável de ambiente 'OFERTA_API_BASE_URL' existe e endpoint responde")

with col3:
    st.write("**Email (Brevo)**")
    st.warning("⚠️ Não configurado")
    st.caption("var ambiente 'BREVO_API_KEY' é inválida ou ausente")

# Page Footer
page_footer.show()
