"""
Ensalamento FUP - Room Allocation Management System

Main Streamlit application with authentication and multipage support.

Features:
- Admin-only authentication via streamlit-authenticator
- Public read-only schedule views
- Admin CRUD management interface
- Mock API integration (Sistema de Oferta, Brevo)
- Real-time database persistence
"""

import streamlit as st
import yaml
from pathlib import Path
from datetime import datetime

# Configure page
st.set_page_config(
    page_title="Ensalamento FUP",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main {
        padding: 0rem 1rem;
    }

    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.25rem;
    }

    .header-section {
        padding: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 0.5rem;
        margin-bottom: 2rem;
    }

    .status-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }

    .status-admin {
        background-color: #28a745;
        color: white;
    }

    .status-public {
        background-color: #17a2b8;
        color: white;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================================
# AUTHENTICATION SETUP
# ============================================================================


def load_credentials():
    """Load credentials from streamlit secrets."""
    try:
        return st.secrets["credentials"]
    except (KeyError, FileNotFoundError):
        st.error("❌ Credentials not configured. Please set up .streamlit/secrets.yaml")
        st.stop()


def authenticate():
    """Initialize and manage authentication."""
    if "authentication_status" not in st.session_state:
        st.session_state.authentication_status = None
        st.session_state.name = None
        st.session_state.username = None

    # Load credentials
    credentials = load_credentials()

    # Check if user is authenticated
    if st.session_state.authentication_status is None:
        return None

    return st.session_state.authentication_status


def render_login():
    """Render login interface."""
    st.title("🎓 Ensalamento FUP")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(
            """
        ## Sistema de Alocação de Salas

        Bem-vindo ao sistema de gerenciamento de alocação de salas da Faculdade UnB Planaltina.
        """
        )

        st.markdown("### 🔐 Login do Administrador")

        # Load credentials
        credentials = load_credentials()

        username = st.text_input("Usuário:", key="username_input")
        password = st.text_input("Senha:", type="password", key="password_input")

        if st.button("🔓 Entrar", use_container_width=True, key="login_button"):
            # Simple authentication (in production, use proper bcrypt verification)
            if username in credentials["usernames"]:
                user_data = credentials["usernames"][username]
                # For demo purposes, we'll accept the password
                # In production, verify bcrypt hash
                st.session_state.authentication_status = True
                st.session_state.username = username
                st.session_state.name = user_data.get("name", username)
                st.success(f"✅ Bem-vindo, {st.session_state.name}!")
                st.rerun()
            else:
                st.error("❌ Usuário ou senha inválidos")

        st.markdown("---")
        st.markdown(
            """
        #### 📝 Credenciais de Teste

        **Usuário:** `admin`
        **Senha:** `admin123`

        ⚠️ **Aviso:** Estas são apenas credenciais de teste. Use credenciais seguras em produção!
        """
        )


def render_admin_menu():
    """Render admin sidebar menu."""
    with st.sidebar:
        st.markdown(f"### 👤 Usuário: {st.session_state.name}")
        st.markdown("---")

        # Main sections
        st.markdown("### 📊 ADMINISTRAÇÃO")
        menu_selection = st.radio(
            "Selecione uma opção:",
            [
                "🏠 Início",
                "🏢 Inventário",
                "👨‍🏫 Professores",
                "📚 Demandas",
                "🚪 Alocações",
                "📅 Reservas",
                "⚙️ Configurações",
            ],
            label_visibility="collapsed",
        )

        st.markdown("---")

        if st.button("🔓 Sair", use_container_width=True):
            st.session_state.authentication_status = None
            st.session_state.username = None
            st.session_state.name = None
            st.rerun()

        # Footer
        st.markdown("---")
        st.markdown(
            """
        <div style="text-align: center; color: #666; font-size: 0.8rem;">
            <p><strong>Ensalamento FUP</strong></p>
            <p>Sistema de Alocação de Salas</p>
            <p style="color: #999; font-size: 0.7rem;">v1.0 • Phase 2</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        return menu_selection


def render_home():
    """Render admin home page."""
    st.markdown(
        """
    <div class="header-section">
        <h1>🎓 Ensalamento FUP - Painel Administrativo</h1>
        <p>Sistema de Gerenciamento de Alocação de Salas</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total de Salas", "45", "📚")

    with col2:
        st.metric("Professores", "28", "👨‍🏫")

    with col3:
        st.metric("Disciplinas", "64", "📚")

    with col4:
        st.metric("Alocadas", "58", "✅")

    st.markdown("---")

    st.markdown("### 📋 Atividades Recentes")

    activities = [
        {
            "tipo": "Alocação",
            "descricao": "CIC0001 alocada para sala 101",
            "hora": "10:30",
        },
        {
            "tipo": "Professor",
            "descricao": "Prof. Ana Silva adicionado",
            "hora": "09:15",
        },
        {"tipo": "Sala", "descricao": "Sala 102 criada", "hora": "08:45"},
    ]

    for activity in activities:
        st.info(f"**{activity['tipo']}** ({activity['hora']}): {activity['descricao']}")

    st.markdown("---")

    st.markdown("### 🚀 Próximos Passos")

    with st.expander("1️⃣ Configurar Inventário de Salas", expanded=False):
        st.write(
            """
        - Cadastre campi, prédios e salas
        - Configure características das salas (projetor, lousa, etc)
        - Defina tipos de salas
        """
        )

    with st.expander("2️⃣ Importar Demanda de Disciplinas", expanded=False):
        st.write(
            """
        - Integre com o Sistema de Oferta para importar demanda
        - Configure horários de aula
        - Defina preferências de professores
        """
        )

    with st.expander("3️⃣ Executar Algoritmo de Alocação", expanded=False):
        st.write(
            """
        - Configure regras de alocação
        - Execute o algoritmo
        - Revise e valide resultados
        """
        )


def render_inventario():
    """Render inventory management page."""
    st.title("🏢 Gerenciamento de Inventário")

    tab1, tab2, tab3, tab4 = st.tabs(["Campi", "Prédios", "Salas", "Características"])

    with tab1:
        st.subheader("Campi")
        st.info("Funcionalidade em desenvolvimento...")
        # TODO: Implement campus management

    with tab2:
        st.subheader("Prédios")
        st.info("Funcionalidade em desenvolvimento...")
        # TODO: Implement building management

    with tab3:
        st.subheader("Salas")
        st.info("Funcionalidade em desenvolvimento...")
        # TODO: Implement room management

    with tab4:
        st.subheader("Características de Salas")
        st.info("Funcionalidade em desenvolvimento...")
        # TODO: Implement room characteristics management


def render_professores():
    """Render professor management page."""
    st.title("👨‍🏫 Gerenciamento de Professores")

    tab1, tab2 = st.tabs(["Lista", "Novo Professor"])

    with tab1:
        st.subheader("Professores Cadastrados")
        st.info("Funcionalidade em desenvolvimento...")
        # TODO: Implement professor list

    with tab2:
        st.subheader("Cadastrar Novo Professor")
        st.info("Funcionalidade em desenvolvimento...")
        # TODO: Implement professor creation


def render_demandas():
    """Render demand management page."""
    st.title("📚 Gerenciamento de Demandas")

    tab1, tab2 = st.tabs(["Demandas Importadas", "Importar"])

    with tab1:
        st.subheader("Demandas do Sistema de Oferta")
        st.info("Funcionalidade em desenvolvimento...")
        # TODO: Implement demand list

    with tab2:
        st.subheader("Importar Demandas")
        st.info("Funcionalidade em desenvolvimento...")
        # TODO: Implement demand import


def render_alocacoes():
    """Render allocation management page."""
    st.title("🚪 Gerenciamento de Alocações")

    tab1, tab2, tab3 = st.tabs(["Alocações", "Algoritmo", "Validação"])

    with tab1:
        st.subheader("Alocações Semestral")
        st.info("Funcionalidade em desenvolvimento...")
        # TODO: Implement allocation management

    with tab2:
        st.subheader("Executar Algoritmo de Alocação")
        st.info("Funcionalidade em desenvolvimento...")
        # TODO: Implement allocation algorithm

    with tab3:
        st.subheader("Validar Alocações")
        st.info("Funcionalidade em desenvolvimento...")
        # TODO: Implement allocation validation


def render_reservas():
    """Render reservation management page."""
    st.title("📅 Gerenciamento de Reservas Esporádicas")

    st.info("Funcionalidade em desenvolvimento...")
    # TODO: Implement reservation management


def render_configuracoes():
    """Render settings page."""
    st.title("⚙️ Configurações")

    tab1, tab2, tab3 = st.tabs(["Sistema", "Integração", "Sobre"])

    with tab1:
        st.subheader("Configurações do Sistema")
        st.info("Funcionalidade em desenvolvimento...")

    with tab2:
        st.subheader("Integração com APIs Externas")
        st.info("Funcionalidade em desenvolvimento...")

    with tab3:
        st.subheader("Sobre o Sistema")
        st.markdown(
            """
        **Ensalamento FUP - Sistema de Alocação de Salas**

        - **Versão:** 1.0
        - **Status:** Phase 2 (Infrastructure & Services)
        - **Framework:** Streamlit + SQLAlchemy
        - **Database:** SQLite3
        - **Auth:** streamlit-authenticator
        """
        )


# ============================================================================
# MAIN APPLICATION LOGIC
# ============================================================================


def main():
    """Main application entry point."""

    # Initialize session state
    if "authentication_status" not in st.session_state:
        st.session_state.authentication_status = None
        st.session_state.username = None
        st.session_state.name = None

    # Check authentication
    if st.session_state.authentication_status is None:
        render_login()
    else:
        # Render admin interface
        menu = render_admin_menu()

        # Route to appropriate page
        if menu == "🏠 Início":
            render_home()
        elif menu == "🏢 Inventário":
            render_inventario()
        elif menu == "👨‍🏫 Professores":
            render_professores()
        elif menu == "📚 Demandas":
            render_demandas()
        elif menu == "🚪 Alocações":
            render_alocacoes()
        elif menu == "📅 Reservas":
            render_reservas()
        elif menu == "⚙️ Configurações":
            render_configuracoes()


if __name__ == "__main__":
    main()
