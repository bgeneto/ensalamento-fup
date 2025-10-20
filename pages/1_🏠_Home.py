"""
Admin Dashboard Page - Home Overview

Displays system status, key metrics, recent activities, and quick actions.
Entry point for authenticated admins.

Route: /pages/1_🏠_Home.py
URL: ?page=Home
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

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
    authenticator.login(location="unrendered", key="authenticator-home")
except Exception as exc:
    st.error(f"❌ Erro de autenticação: {exc}")
    st.stop()

auth_status = st.session_state.get("authentication_status")

if auth_status:
    # Show logout button in sidebar
    authenticator.logout(location="sidebar", key="logout-home")
elif auth_status is False:
    st.error("❌ Acesso negado.")
    st.stop()
else:
    st.warning("👈 Por favor, faça login na página inicial para acessar o sistema.")
    st.page_link("main.py", label="Voltar para o início ↩", icon="🏠")
    # navigate back to main page where login widget is located
    st.switch_page("main.py")
    st.stop()

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Home - Ensalamento",
    page_icon="🏠",
    layout="wide",
)

# ============================================================================
# IMPORTS - Repositories
# ============================================================================

from src.repositories.sala import SalaRepository
from src.repositories.professor import ProfessorRepository
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.alocacao import AlocacaoRepository
from src.config.database import get_db_session

# ============================================================================
# PAGE CONTENT
# ============================================================================

# Header
st.markdown(
    """
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 0.5rem; margin-bottom: 2rem; color: white;">
    <h1>🏠 Painel Administrativo</h1>
    <p style="font-size: 1.1rem; margin: 0.5rem 0;">Sistema de Gerenciamento de Alocação de Salas</p>
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

st.markdown("---")

# ============================================================================
# KEY METRICS
# ============================================================================

st.markdown("## 📊 Indicadores Principais")

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
col1, col2, col3, col4, col5 = st.columns(5)

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

with col5:
    st.metric(
        "📈 Taxa",
        f"{allocation_pct:.1f}%",
        delta="Alocadas",
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
    st.caption("SQLite3 - ensalamento.db")

with col2:
    st.write("**Integração APIs**")
    st.warning("⚠️ Não configurado")
    st.caption("Sistema de Oferta - Aguardando config")

with col3:
    st.write("**Email (Brevo)**")
    st.warning("⚠️ Não configurado")
    st.caption("Notificações - Aguardando config")

st.markdown("---")

# ============================================================================
# HELP & DOCUMENTATION
# ============================================================================

st.markdown("## 📚 Próximos Passos")

with st.expander("1️⃣ Configurar Inventário de Salas", expanded=False):
    st.markdown(
        """
    Comece cadastrando a estrutura física da instituição:

    - **Acesse:** Inventário → Campi/Prédios/Salas
    - **Ações:**
      - Crie os campi (ex: Campus Darcy Ribeiro)
      - Adicione os prédios (ex: Prédio SG)
      - Registre as salas com características (capacidade, projetor, A/C)

    💡 **Dica:** Você pode importar salas via CSV se tiver dados estruturados.
    """
    )

with st.expander("2️⃣ Importar Professores", expanded=False):
    st.markdown(
        """
    Importe o corpo docente da instituição:

    - **Acesse:** Professores → Importar
    - **Opções:**
      - Carregar CSV com dados de professores
      - Sincronizar com SIGAA (se configurado)
      - Importação manual

    💡 **Dica:** Cada professor pode ter preferências de horário e sala.
    """
    )

with st.expander("3️⃣ Importar Demanda de Disciplinas", expanded=False):
    st.markdown(
        """
    Importe as disciplinas que necessitam de salas:

    - **Acesse:** Demandas → Importar
    - **Origem:**
      - Sistema de Oferta (automático, se configurado)
      - CSV manual (se dados estruturados)

    💡 **Dica:** Você pode marcar disciplinas como "não alocar" manualmente.
    """
    )

with st.expander("4️⃣ Executar Algoritmo de Alocação", expanded=False):
    st.markdown(
        """
    Aloque automaticamente as disciplinas às salas:

    - **Acesse:** Alocações → Executar Algoritmo
    - **Configuração:**
      - Escolha o semestre
      - Configure restrições (se houver)
      - Clique em "Processar"

    💡 **Dica:** Revise conflitos e faça ajustes manuais se necessário.
    """
    )

with st.expander("5️⃣ Exportar Resultado Final", expanded=False):
    st.markdown(
        """
    Exporte a grade final de alocações:

    - **Acesse:** Alocações → Exportar
    - **Formatos:**
      - PDF (para publicação)
      - CSV (para processamento)
      - Excel (para ajustes)

    💡 **Dica:** Notifique professores e alunos via email após exportar.
    """
    )

st.markdown("---")

# Footer
st.markdown(
    """
<div style="text-align: center; color: #999; font-size: 0.85rem; padding: 2rem 0;">
    <p><strong>Ensalamento FUP</strong> - Sistema de Alocação de Salas</p>
    <p>Versão 1.0 • Phase 3 Milestone 2 • Multipage Admin Interface</p>
    <p style="font-size: 0.75rem;">© 2024 Faculdade UnB Planaltina</p>
</div>
""",
    unsafe_allow_html=True,
)
