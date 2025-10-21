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
import streamlit_authenticator as stauth
from yaml.loader import SafeLoader
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


def load_config():
    """Load configuration from YAML file."""
    config_path = Path(".streamlit/secrets.yaml")

    if not config_path.exists():
        st.error(f"❌ Configuration file not found: {config_path}")
        st.stop()

    try:
        with open(config_path) as f:
            config = yaml.load(f, Loader=SafeLoader)
        return config
    except Exception as e:
        st.error(f"❌ Error loading config file: {str(e)}")
        st.stop()


def setup_authenticator():
    """Setup streamlit-authenticator with credentials from YAML config."""
    try:
        config = load_config()

        # Pre-hash plain text passwords
        stauth.Hasher.hash_passwords(config["credentials"])

        # Initialize authenticator
        authenticator = stauth.Authenticate(
            credentials=config["credentials"],
            cookie_name=config["cookie"]["name"],
            cookie_key=config["cookie"]["key"],
            cookie_expiry_days=config["cookie"]["expiry_days"],
        )

        return authenticator, config

    except Exception as e:
        st.error(f"❌ Authentication setup error: {str(e)}")
        st.stop()


def render_login(authenticator):
    """Render login interface using streamlit-authenticator."""
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

        # Render login widget
        try:
            authenticator.login(location="main")
        except Exception as e:
            st.error(f"❌ Authentication error: {str(e)}")


# ============================================================================
# MAIN APPLICATION LOGIC
# ============================================================================


def render_admin_menu(authenticator):
    """Render admin sidebar (simplified for multipage).

    Note: Streamlit automatically generates page navigation from pages/ directory.
    This function is mainly for logout and user info display.
    """
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.name}")
        st.markdown(f"*@{st.session_state.username}*")
        st.markdown("---")

        # Logout button
        authenticator.logout(location="sidebar")

        st.markdown("---")

        # Footer
        st.markdown(
            """
        <div style="text-align: center; color: #666; font-size: 0.8rem;">
            <p><strong>Ensalamento FUP</strong></p>
            <p>Sistema de Alocação de Salas</p>
            <p style="color: #999; font-size: 0.7rem;">v1.0 • Phase 3 M2</p>
        </div>
        """,
            unsafe_allow_html=True,
        )


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
    """Main application entry point - handles authentication.

    Note: Streamlit automatically routes to pages/ after authentication.
    This main.py only handles login/logout flow and initialization of authenticator.

    CRITICAL: The authenticator object must be stored in st.session_state
    so that it can be retrieved and used in all other pages (pages/ directory).
    """

    # Setup authenticator
    authenticator, config = setup_authenticator()

    # Store authenticator and config in session state for use in all pages
    st.session_state["authenticator"] = authenticator
    st.session_state["config"] = config

    # Render login widget (only on home page)
    try:
        authenticator.login(location="main", key="login-home")
    except Exception as e:
        st.error(f"❌ Authentication error: {str(e)}")

    # Check authentication status
    if st.session_state.get("authentication_status"):
        # User is authenticated - show user info and logout in sidebar
        with st.sidebar:
            st.markdown(f"### 👤 {st.session_state.name}")
            st.markdown(f"*@{st.session_state.username}*")
            st.markdown("---")
            authenticator.logout(location="sidebar", key="logout-home")
            st.markdown("---")
            st.markdown(
                """
            <div style="text-align: center; color: #666; font-size: 0.8rem;">
                <p><strong>Ensalamento FUP</strong></p>
                <p>Sistema de Alocação de Salas</p>
                <p style="color: #999; font-size: 0.7rem;">v1.0 • Phase 3 M2</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # For multipage apps, Streamlit automatically shows pages from pages/ directory
        # This main.py becomes the home page (accessed via "Home" in sidebar)

        st.markdown(
            """
        <div class="header-section">
            <h1>🎓 Ensalamento FUP - Painel Administrativo</h1>
            <p>Sistema de Gerenciamento de Alocação de Salas</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.info(
            "👈 Use o menu lateral esquerdo para navegar entre as seções de administração. "
            "As páginas carregarão automaticamente."
        )

    elif st.session_state.get("authentication_status") is False:
        st.error("❌ Usuário ou senha inválidos")


if __name__ == "__main__":
    main()
