"""
Professor Management Page - Faculty Import & CRUD

Manage faculty members with import capabilities from CSV and API integration.
Configure professor availability and preferences.

Route: /pages/3_👨‍🏫_Professores.py
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
    st.stop()

# Call login with unrendered location to maintain session (required for page refresh fix)
try:
    authenticator.login(location="unrendered", key="authenticator-professores")
except Exception as exc:
    st.error(f"❌ Erro de autenticação: {exc}")
    st.stop()

auth_status = st.session_state.get("authentication_status")

if auth_status:
    # Show logout button in sidebar
    authenticator.logout(location="sidebar", key="logout-professores")
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
    page_title="Ensalamento - Professores",
    page_icon="👨‍🏫",
    layout="wide",
)

# ============================================================================
# IMPORTS
# ============================================================================

from src.repositories.professor import ProfessorRepository
from src.schemas.academic import ProfessorCreate
from src.models.academic import Professor
from src.config.database import get_db_session
from src.utils.ui_feedback import (
    display_session_feedback,
    set_session_feedback,
)

# ============================================================================
# PAGE HEADER
# ============================================================================

st.title("👨‍🏫 Gerenciamento de Professores")
st.markdown("Importe, cadastre e gerencie dados dos professores e suas preferências.")

st.markdown("---")

# ============================================================================
# TABS STRUCTURE
# ============================================================================

tab1, tab2 = st.tabs(["📋 Lista de Professores", "📥 Importar"])

# =============================================================================
# TAB 1: PROFESSOR LIST - CRUD WITH ST.DATA_EDITOR
# =============================================================================

with tab1:
    st.subheader("Professores Cadastrados")

    st.info(
        """
        Edite os dados diretamente na tabela abaixo.
        - Para **adicionar**, clique em ✚ no canto superior direito da tabela.
        - Para **remover**, selecione a linha correspondente clicando na primeira coluna e, em seguida, exclua a linha clicando no ícone 🗑️ no canto superior direito da tabela.
        - Para **alterar** um dado, dê um clique duplo na célula da tabela. As edições serão salvas automaticamente.
        """
    )

    # Professor list with CRUD
    try:
        with get_db_session() as session:
            prof_repo = ProfessorRepository(session)
            professores = prof_repo.get_all()

            if professores:
                # Display summary
                st.markdown(f"**Total de professores encontrados: {len(professores)}**")

                # Create DataFrame with editable columns
                prof_data = []
                for prof in professores:
                    prof_data.append(
                        {
                            "ID": prof.id,
                            "Nome": prof.nome_completo,
                            "Username": prof.username_login or "",
                            "Mobilidade": prof.tem_baixa_mobilidade,
                        }
                    )

                df = pd.DataFrame(prof_data)

                # Use st.data_editor with dynamic num_rows for CRUD operations
                # Note: ID column is hidden but kept internally to track database records
                edited_df = st.data_editor(
                    df,
                    width="stretch",
                    hide_index=True,
                    num_rows="dynamic",
                    column_config={
                        "ID": None,  # Hide ID column from user view
                        "Nome": st.column_config.TextColumn(
                            "Nome",
                            required=True,
                            help="Nome completo do professor",
                        ),
                        "Username": st.column_config.TextColumn(
                            "Username",
                            required=True,
                            help="Username SIGAA do professor",
                        ),
                        "Mobilidade": st.column_config.CheckboxColumn(
                            "♿ Mobilidade Reduzida",
                            help="Marque se o professor tem restrições de mobilidade",
                        ),
                    },
                    key="prof_table_editor",
                )

                # Process changes from data editor
                if len(edited_df) != len(df):
                    # Detect additions or deletions
                    original_ids = set(df["ID"].astype(int))
                    edited_ids = set(
                        edited_df[edited_df["ID"].notna()]["ID"].astype(int)
                    )

                    # Handle deletions (rows removed from edited_df)
                    deleted_ids = original_ids - edited_ids
                    for prof_id in deleted_ids:
                        try:
                            with get_db_session() as session:
                                prof_repo_delete = ProfessorRepository(session)
                                prof_repo_delete.delete(int(prof_id))
                            set_session_feedback(
                                "crud_result",
                                True,
                                f"Professor ID {prof_id} removido com sucesso!",
                                action="delete",
                            )
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao deletar professor ID {prof_id}: {str(e)}",
                                action="delete",
                            )
                        st.rerun()

                    # Handle additions (new rows with NaN or 0 ID)
                    new_rows = edited_df[
                        (edited_df["ID"].isna()) | (edited_df["ID"] == 0)
                    ].copy()
                    for idx, row in new_rows.iterrows():
                        nome = str(row["Nome"]).strip()
                        username = str(row["Username"]).strip()
                        mobilidade = bool(row["Mobilidade"])

                        if not nome or not username:
                            set_session_feedback(
                                "crud_result",
                                False,
                                "Nome e Username são obrigatórios",
                                action="create",
                            )
                            st.rerun()

                        try:
                            with get_db_session() as session:
                                prof_repo_create = ProfessorRepository(session)
                                # Check if already exists
                                existing = prof_repo_create.get_by_username_login(
                                    username
                                )
                                if existing:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        f"Username '{username}' já existe no banco de dados",
                                        action="create",
                                    )
                                else:
                                    prof_dto = ProfessorCreate(
                                        nome_completo=nome,
                                        username_login=username,
                                        tem_baixa_mobilidade=mobilidade,
                                    )
                                    prof_repo_create.create(prof_dto)
                                    set_session_feedback(
                                        "crud_result",
                                        True,
                                        f"Professor {nome} adicionado com sucesso!",
                                        action="create",
                                    )
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao criar professor: {str(e)}",
                                action="create",
                            )
                        st.rerun()

                # Handle updates (rows with changes in existing records)
                else:
                    for idx, row in edited_df.iterrows():
                        if idx < len(df):
                            original_row = df.iloc[idx]
                            prof_id = int(row["ID"])

                            # Check if any field changed
                            nome_changed = row["Nome"] != original_row["Nome"]
                            username_changed = (
                                row["Username"] != original_row["Username"]
                            )
                            mobilidade_changed = (
                                row["Mobilidade"] != original_row["Mobilidade"]
                            )

                            if nome_changed or username_changed or mobilidade_changed:
                                nome = str(row["Nome"]).strip()
                                username = str(row["Username"]).strip()
                                mobilidade = bool(row["Mobilidade"])

                                if not nome or not username:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        "Nome e Username são obrigatórios",
                                        action="update",
                                    )
                                    st.rerun()

                                try:
                                    with get_db_session() as session:
                                        prof_repo_update = ProfessorRepository(session)
                                        # Get current professor
                                        current = session.get(Professor, prof_id)

                                        if current:
                                            # Check if new username already exists (excluding current)
                                            if (
                                                username_changed
                                                and username != original_row["Username"]
                                            ):
                                                existing = prof_repo_update.get_by_username_login(
                                                    username
                                                )
                                                if existing and existing.id != prof_id:
                                                    set_session_feedback(
                                                        "crud_result",
                                                        False,
                                                        f"Username '{username}' já existe",
                                                        action="update",
                                                    )
                                                    st.rerun()

                                            # Update fields
                                            current.nome_completo = nome
                                            current.username_login = username
                                            current.tem_baixa_mobilidade = mobilidade
                                            session.commit()

                                            set_session_feedback(
                                                "crud_result",
                                                True,
                                                f"Professor(a) {nome} atualizado com sucesso!",
                                                action="update",
                                            )
                                except Exception as e:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        f"Erro ao atualizar professor(a): {str(e)}",
                                        action="update",
                                    )
                                st.rerun()

                # Display CRUD result if available
                display_session_feedback("crud_result")

            else:
                st.info(
                    "📭 Nenhum professor cadastrado ainda. Use a aba 'Importar' para adicionar professores ou adicione uma nova linha na tabela acima."
                )

    except Exception as e:
        st.error(f"❌ Erro ao carregar professores: {str(e)}")

# =============================================================================
# TAB 2: IMPORT PROFESSORS
# =============================================================================

with tab2:
    st.subheader("Importar Professores")

    import_method = st.radio(
        "Escolha o método de importação:",
        ["📥 Upload CSV", "🔗 API Sistema de Oferta", "📝 Importação Manual"],
        horizontal=True,
    )

    # CSV Import
    if import_method == "📥 Upload CSV":
        st.markdown(
            """
        **Formato do arquivo CSV esperado:**

        Colunas obrigatórias (separadas por ponto-e-vírgula `;`):
        - `username_login`: Username do professor
        - `nome_completo`: Nome completo do professor

        Exemplo:
        ```csv
        username_login;nome_completo
        asilva;Ana Silva
        csantos;Carlos Santos
        jpereira;João Pereira
        ```

        **Notas:**
        - O campo `tem_baixa_mobilidade` será sempre iniciado como `Falso` (Não)
        - Após importação, você pode editar cada professor para marcar restrições de mobilidade
        """
        )

        uploaded_file = st.file_uploader(
            "Carregar arquivo CSV", type=["csv"], key="csv_upload"
        )

        if uploaded_file:
            try:
                # Read with semicolon delimiter and handle BOM
                df = pd.read_csv(uploaded_file, delimiter=";", encoding="utf-8-sig")

                st.markdown("**Prévia dos dados:**")
                st.dataframe(df.head(10), width="stretch")

                # Validation
                required_cols = {"username_login", "nome_completo"}
                missing_cols = required_cols - set(df.columns)

                if missing_cols:
                    st.error(f"❌ Colunas faltando: {', '.join(missing_cols)}")
                    st.info(f"Colunas encontradas: {', '.join(df.columns)}")
                else:
                    st.success(f"✅ Arquivo válido com {len(df)} professores")

                    if st.button("✅ Importar Professores"):
                        count = 0
                        errors = []

                        try:
                            with get_db_session() as session:
                                prof_repo = ProfessorRepository(session)

                                for idx, row in df.iterrows():
                                    username = str(row["username_login"]).strip()
                                    nome = str(row["nome_completo"]).strip()

                                    # Validate required fields
                                    if not username or not nome:
                                        errors.append(f"Linha {idx+2}: Campos vazios")
                                        continue

                                    # Check if already exists
                                    existing = prof_repo.get_by_username_login(username)
                                    if existing:
                                        errors.append(
                                            f"Linha {idx+2}: {username} já existe no BD"
                                        )
                                        continue

                                    try:
                                        prof_dto = ProfessorCreate(
                                            nome_completo=nome,
                                            username_login=username,
                                            tem_baixa_mobilidade=False,
                                        )
                                        prof_repo.create(prof_dto)
                                        count += 1
                                    except Exception as e:
                                        errors.append(f"Linha {idx+2}: {str(e)}")

                            # Store result in session state to persist across reruns
                            message = (
                                f"{count} professores importados com sucesso!"
                                if not errors
                                else f"{count} professores importados; {len(errors)} linhas com problemas."
                            )

                            set_session_feedback(
                                "import_result",
                                True,
                                message,
                                count=count,
                                errors=errors,
                            )
                            st.rerun()
                        except Exception as e:
                            set_session_feedback(
                                "import_result",
                                False,
                                f"Erro ao importar professores: {str(e)}",
                                error=str(e),
                            )
                            st.rerun()

                # Display import result if available
                result = display_session_feedback(
                    "import_result", success_icon="✅", error_icon="❌"
                )
                if result and result.get("success") and result.get("errors"):
                    st.warning(
                        f"{len(result['errors'])} linhas tiveram problemas durante a importação:"
                    )
                    for error in result["errors"][:10]:
                        st.write(f"  • {error}")
                    if len(result["errors"]) > 10:
                        st.write(
                            f"  ... e mais {len(result['errors']) - 10} ocorrências"
                        )

            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo: {str(e)}")

    # API Import
    elif import_method == "🔗 API Sistema de Oferta":
        st.markdown(
            """
        Integração com API do Sistema de Oferta ainda não configurada.

        **Passos necessários:**
        1. Configurar credenciais na página de Configurações
        2. Testar conexão com API
        3. Selecionar semestre e campus
        4. Sincronizar dados
        """
        )

        if st.button("🔧 Ir para Configurações", key="goto_config"):
            st.info("Acesse a página de Configurações no menu lateral")

    # Manual Import
    elif import_method == "📝 Importação Manual":
        st.markdown("**Adicionar um professor manualmente:**")

        with st.form("form_professor"):
            nome_completo = st.text_input(
                "Nome Completo", placeholder="ex: Ana Silva dos Santos"
            )
            username_login = st.text_input("Username", placeholder="ex: asilva")
            tem_mobilidade = st.checkbox(
                "Mobilidade Reduzida?",
                value=False,
                help="Marque se o professor tem restrições de mobilidade",
            )

            if st.form_submit_button("➕ Adicionar Professor", width="stretch"):
                if not nome_completo or not username_login:
                    st.error("Preencha ao menos Nome e Username")
                else:
                    try:
                        with get_db_session() as session:
                            prof_repo = ProfessorRepository(session)

                            # Check if already exists
                            existing = prof_repo.get_by_username_login(username_login)
                            if existing:
                                set_session_feedback(
                                    "form_result",
                                    False,
                                    f"Username '{username_login}' já existe no banco de dados",
                                )
                            else:
                                prof_dto = ProfessorCreate(
                                    nome_completo=nome_completo,
                                    username_login=username_login,
                                    tem_baixa_mobilidade=tem_mobilidade,
                                )
                                prof_repo.create(prof_dto)
                                set_session_feedback(
                                    "form_result",
                                    True,
                                    f"Professor {nome_completo} adicionado com sucesso!",
                                )
                        st.rerun()
                    except Exception as e:
                        set_session_feedback(
                            "form_result",
                            False,
                            f"Erro ao adicionar professor: {str(e)}",
                        )
                        st.rerun()

        # Display form result if available
        display_session_feedback("form_result")
