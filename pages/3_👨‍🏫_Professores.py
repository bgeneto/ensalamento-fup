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
from io import BytesIO

# Auth gating
if not st.session_state.get("authentication_status"):
    st.error("❌ Acesso negado. Faça login primeiro.")
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
from src.config.database import get_db_session

# ============================================================================
# PAGE HEADER
# ============================================================================

st.title("👨‍🏫 Gerenciamento de Professores")
st.markdown("Importe, cadastre e gerencie dados dos professores e suas preferências.")

st.markdown("---")

# ============================================================================
# TABS STRUCTURE
# ============================================================================

tab1, tab2, tab3 = st.tabs(
    ["📋 Lista de Professores", "📥 Importar", "🏢 Departamentos"]
)

# =============================================================================
# TAB 1: PROFESSOR LIST
# =============================================================================

with tab1:
    st.subheader("Professores Cadastrados")

    # Filters
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        search_name = st.text_input(
            "Buscar por Nome", placeholder="ex: Ana Silva", key="prof_search_name"
        )

    with col2:
        search_username = st.text_input(
            "Buscar por Username",
            placeholder="ex: asilva",
            key="prof_search_username",
        )

    with col3:
        if st.button("➕ Novo Professor", use_container_width=True):
            st.session_state.show_prof_form = True

    st.markdown("---")

    # Professor list
    try:
        with get_db_session() as session:
            prof_repo = ProfessorRepository(session)
            professores = prof_repo.get_all()

            if professores:
                # Apply filters
                filtered_profs = professores

                if search_name:
                    filtered_profs = [
                        p
                        for p in filtered_profs
                        if search_name.lower() in p.nome_completo.lower()
                    ]

                if search_username:
                    filtered_profs = [
                        p
                        for p in filtered_profs
                        if search_username.lower() in (p.username_login or "").lower()
                    ]

                # Display summary
                st.markdown(
                    f"**Total de professores encontrados: {len(filtered_profs)} de {len(professores)}**"
                )

                # Create DataFrame for display with editable columns
                prof_data = []
                for prof in filtered_profs:
                    prof_data.append(
                        {
                            "ID": prof.id,
                            "Nome": prof.nome_completo,
                            "Username": prof.username_login or "-",
                            "Mobilidade": (
                                "Sim" if prof.tem_baixa_mobilidade else "Não"
                            ),
                            "Deletar": False,  # Checkbox for deletion
                        }
                    )

                df = pd.DataFrame(prof_data)

                # Use st.data_editor for interactive table with deletion support
                edited_df = st.data_editor(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    num_rows="fixed",
                    column_config={
                        "ID": st.column_config.NumberColumn("ID", disabled=True),
                        "Nome": st.column_config.TextColumn("Nome", disabled=True),
                        "Username": st.column_config.TextColumn(
                            "Username", disabled=True
                        ),
                        "Mobilidade": st.column_config.TextColumn(
                            "Mobilidade", disabled=True
                        ),
                        "Deletar": st.column_config.CheckboxColumn(
                            "Deletar",
                            help="Marque para deletar este professor",
                        ),
                    },
                    key="prof_table_editor",
                )

                # Handle deletions
                for idx, row in edited_df.iterrows():
                    if row["Deletar"]:
                        prof_id = int(row["ID"])
                        try:
                            with get_db_session() as session:
                                prof_repo_delete = ProfessorRepository(session)
                                prof_repo_delete.delete(prof_id)
                            st.success(
                                f"✅ Professor ID {prof_id} removido com sucesso!"
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao deletar professor: {str(e)}")

                # Export button
                col1, col2 = st.columns(2)
                with col1:
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Exportar CSV",
                        data=csv,
                        file_name=f"professores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                    )

                st.markdown("---")

                # Professor details
                st.subheader("Detalhes do Professor")

                selected_prof_id = st.selectbox(
                    "Selecione um professor para ver detalhes:",
                    [p.id for p in filtered_profs],
                    format_func=lambda x: f"ID {x} - {next((p.nome_completo for p in filtered_profs if p.id == x), 'N/A')}",
                )

                if selected_prof_id:
                    selected_prof = next(
                        (p for p in filtered_profs if p.id == selected_prof_id), None
                    )

                    if selected_prof:
                        col1, col2 = st.columns([1, 1])

                        with col1:
                            st.markdown(f"**Nome:** {selected_prof.nome_completo}")
                            st.markdown(
                                f"**Usuário SIGAA:** {selected_prof.username_login or 'N/A'}"
                            )

                        with col2:
                            mobility_status = (
                                "🚫 Sim"
                                if selected_prof.tem_baixa_mobilidade
                                else "✅ Não"
                            )
                            st.markdown(f"**Mobilidade Reduzida:** {mobility_status}")
                            st.markdown(
                                f"**Criado em:** {selected_prof.created_at.strftime('%d/%m/%Y %H:%M') if selected_prof.created_at else 'N/A'}"
                            )

                        # Edit / Delete buttons
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            if st.button(
                                "✏️ Editar Professor",
                                key=f"edit_prof_{selected_prof_id}",
                            ):
                                st.session_state.editing_prof_id = selected_prof_id
                                st.info("Funcionalidade em desenvolvimento")

                        with col2:
                            if st.button(
                                "♿ Mobilidade Reduzida",
                                key=f"mobility_prof_{selected_prof_id}",
                                help="Marcar/desmarcar restrição de mobilidade",
                            ):
                                st.info("Funcionalidade em desenvolvimento")

                        with col3:
                            if st.button(
                                "🗑️ Deletar Professor",
                                key=f"delete_prof_{selected_prof_id}",
                            ):
                                try:
                                    prof_repo.delete(selected_prof_id)
                                    st.success(
                                        f"Professor {selected_prof.nome_completo} removido com sucesso!"
                                    )
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao deletar professor: {str(e)}")

            else:
                st.info(
                    "📭 Nenhum professor cadastrado ainda. Use a aba 'Importar' para adicionar professores."
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

    st.markdown("---")

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
                st.dataframe(df.head(10), use_container_width=True)

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
                            st.session_state.import_result = {
                                "success": True,
                                "count": count,
                                "errors": errors,
                            }
                            st.rerun()
                        except Exception as e:
                            st.session_state.import_result = {
                                "success": False,
                                "error": str(e),
                            }
                            st.rerun()

                # Display import result if available
                if "import_result" in st.session_state:
                    result = st.session_state.import_result
                    if result.get("success"):
                        st.success(
                            f"✅ {result['count']} professores importados com sucesso!"
                        )
                        if result.get("errors"):
                            st.warning(
                                f"⚠️ {len(result['errors'])} linhas tiveram problemas:"
                            )
                            for error in result["errors"][:10]:  # Show first 10 errors
                                st.write(f"  • {error}")
                            if len(result["errors"]) > 10:
                                st.write(
                                    f"  ... e mais {len(result['errors']) - 10} erros"
                                )
                        # Clear result after displaying
                        if st.button("🔄 Limpar mensagem", key="clear_import_result"):
                            del st.session_state.import_result
                            st.rerun()
                    else:
                        st.error(
                            f"❌ Erro ao importar: {result.get('error', 'Erro desconhecido')}"
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

            if st.form_submit_button(
                "➕ Adicionar Professor", use_container_width=True
            ):
                if not nome_completo or not username_login:
                    st.error("Preencha ao menos Nome e Username")
                else:
                    try:
                        with get_db_session() as session:
                            prof_repo = ProfessorRepository(session)

                            # Check if already exists
                            existing = prof_repo.get_by_username_login(username_login)
                            if existing:
                                st.session_state.form_result = {
                                    "success": False,
                                    "message": f"❌ Username '{username_login}' já existe no banco de dados",
                                }
                            else:
                                prof_dto = ProfessorCreate(
                                    nome_completo=nome_completo,
                                    username_login=username_login,
                                    tem_baixa_mobilidade=tem_mobilidade,
                                )
                                prof_repo.create(prof_dto)
                                st.session_state.form_result = {
                                    "success": True,
                                    "message": f"✅ Professor {nome_completo} adicionado com sucesso!",
                                }
                        st.rerun()
                    except Exception as e:
                        st.session_state.form_result = {
                            "success": False,
                            "message": f"❌ Erro ao adicionar professor: {str(e)}",
                        }
                        st.rerun()

        # Display form result if available
        if "form_result" in st.session_state:
            result = st.session_state.form_result
            if result["success"]:
                st.success(result["message"])
            else:
                st.error(result["message"])
            # Clear result after displaying
            if st.button("🔄 Limpar", key="clear_form_result"):
                del st.session_state.form_result
                st.rerun()

# =============================================================================
# TAB 3: DEPARTMENT MANAGEMENT
# =============================================================================

with tab3:
    st.subheader("Estatísticas")

    try:
        with get_db_session() as session:
            prof_repo = ProfessorRepository(session)
            all_profs = prof_repo.get_all()

            if all_profs:
                # Count professors with mobility restrictions
                with_mobility = sum(1 for p in all_profs if p.tem_baixa_mobilidade)
                without_mobility = len(all_profs) - with_mobility

                # Display stats
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Total de Professores", len(all_profs))

                with col2:
                    st.metric("Com Mobilidade Reduzida", with_mobility)

                with col3:
                    st.metric("Sem Restrições", without_mobility)

                st.markdown("---")

                # Chart
                st.markdown("**Distribuição de Restrições de Mobilidade:**")
                stats_data = pd.DataFrame(
                    {
                        "Categoria": ["Com Restrição", "Sem Restrição"],
                        "Quantidade": [with_mobility, without_mobility],
                    }
                )
                st.bar_chart(stats_data.set_index("Categoria"))

            else:
                st.info("Nenhum professor cadastrado ainda")

    except Exception as e:
        st.warning(f"Erro ao carregar estatísticas: {str(e)}")

st.markdown("---")

# Footer
