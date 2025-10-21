"""
Building Management Tab Component

Handles CRUD operations for Prédios (Buildings).
Extracted from the main inventory page for better maintainability.
"""

import streamlit as st
import pandas as pd
from src.repositories.predio import PredioRepository
from src.repositories.campus import CampusRepository
from src.schemas.inventory import PredioCreate
from src.config.database import get_db_session
from src.utils.ui_feedback import display_session_feedback, set_session_feedback

# Needs to be imported from auth module for shared imports
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def render_buildings_tab():
    st.subheader("Gerenciamento de Prédios")

    st.info(
        """
        Edite os dados diretamente na tabela abaixo. Para prédios, é necessário selecionar um campus existente.
        - Para **adicionar**, clique em ✚ no canto superior direito da tabela.
        - Para **remover**, selecione a linha correspondente clicando na primeira coluna e, em seguida, exclua a linha clicando no ícone 🗑️ no canto superior direito da tabela.
        - Para **alterar** um dado, dê um clique duplo na célula da tabela. As edições serão salvas automaticamente.
        """
    )

    # Buildings list with CRUD
    try:
        with get_db_session() as session:
            predio_repo = PredioRepository(session)
            campus_repo = CampusRepository(session)

            # Get buildings and campuses for dropdown
            predios = predio_repo.get_all()
            campi = campus_repo.get_all()

            # Create campus options dict for dropdown
            campus_options = {campus.id: campus.nome for campus in campi}

            if predios:
                # Display summary
                st.markdown(f"**Total de prédios encontrados: {len(predios)}**")

                # Create DataFrame with editable columns
                predio_data = []
                for predio in predios:
                    predio_data.append(
                        {
                            "ID": predio.id,
                            "Nome": predio.nome,
                            "Descricao": predio.descricao,
                            "Campus": predio.campus_id,  # This will be the foreign key ID
                        }
                    )

                df = pd.DataFrame(predio_data)

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
                            help="Nome do prédio",
                        ),
                        "Descricao": st.column_config.TextColumn(
                            "Descrição",
                            required=True,
                            help="Descrição do prédio",
                        ),
                        "Campus": st.column_config.SelectboxColumn(
                            "Campus",
                            options=list(campus_options.keys()),
                            format_func=lambda x: (
                                campus_options.get(x, "N/A") if x else "Selecionar..."
                            ),
                            required=True,
                            help="Campus ao qual o prédio pertence",
                        ),
                    },
                    key="predio_table_editor",
                )

                # Process changes from data editor
                if len(edited_df) != len(df):
                    changes_made = False
                    errors_occurred = False

                    # Detect additions or deletions
                    original_ids = set(df["ID"].astype(int))
                    edited_ids = set(
                        edited_df[edited_df["ID"].notna()]["ID"].astype(int)
                    )

                    # Handle deletions (rows removed from edited_df)
                    deleted_ids = original_ids - edited_ids
                    if deleted_ids:
                        try:
                            with get_db_session() as session:
                                predio_repo_delete = PredioRepository(session)
                                for predio_id in deleted_ids:
                                    predio_repo_delete.delete(int(predio_id))
                            set_session_feedback(
                                "crud_result",
                                True,
                                f"{len(deleted_ids)} prédio(s) removido(s) com sucesso!",
                                action="delete",
                            )
                            changes_made = True
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao deletar prédio(s): {str(e)}",
                                action="delete",
                            )
                            errors_occurred = True

                    # Handle additions (new rows with NaN or 0 ID)
                    new_rows = edited_df[
                        (edited_df["ID"].isna()) | (edited_df["ID"] == 0)
                    ].copy()
                    if not new_rows.empty:
                        created = 0
                        try:
                            with get_db_session() as session:
                                predio_repo_create = PredioRepository(session)
                                for idx, row in new_rows.iterrows():
                                    nome = str(row["Nome"]).strip()
                                    descricao = str(row["Descricao"]).strip()
                                    campus_id = row["Campus"]

                                    if not nome:
                                        set_session_feedback(
                                            "crud_result",
                                            False,
                                            "Nome do prédio é obrigatório",
                                            action="create",
                                        )
                                        errors_occurred = True
                                        continue

                                    if not descricao:
                                        set_session_feedback(
                                            "crud_result",
                                            False,
                                            "Descrição do prédio é obrigatória",
                                            action="create",
                                        )
                                        errors_occurred = True
                                        continue

                                    if not campus_id or pd.isna(campus_id):
                                        set_session_feedback(
                                            "crud_result",
                                            False,
                                            "Campus deve ser selecionado",
                                            action="create",
                                        )
                                        errors_occurred = True
                                        continue

                                    # Check if already exists
                                    existing = predio_repo_create.get_all()
                                    existing_names = [p.nome.lower() for p in existing]
                                    if nome.lower() in existing_names:
                                        set_session_feedback(
                                            "crud_result",
                                            False,
                                            f"Prédio '{nome}' já existe no banco de dados",
                                            action="create",
                                        )
                                        errors_occurred = True
                                        continue

                                    predio_dto = PredioCreate(
                                        nome=nome,
                                        descricao=descricao,
                                        campus_id=int(campus_id),
                                    )
                                    predio_repo_create.create(predio_dto)
                                    created += 1
                                    campus_name = campus_options.get(
                                        int(campus_id), "N/A"
                                    )
                                    set_session_feedback(
                                        "crud_result",
                                        True,
                                        f"Prédio {nome} ({descricao}) adicionado com sucesso ao campus {campus_name}!",
                                        action="create",
                                    )
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao criar prédio: {str(e)}",
                                action="create",
                            )
                            errors_occurred = True

                        if created:
                            changes_made = True

                    if changes_made:
                        st.rerun()
                    # If only errors occurred, avoid rerun so user can edit

                # Handle updates (rows with changes in existing records)
                else:
                    changes_made = False
                    errors_occurred = False

                    for idx, row in edited_df.iterrows():
                        if idx < len(df):
                            original_row = df.iloc[idx]
                            predio_id = int(row["ID"])

                            # Check if any field changed
                            nome_changed = row["Nome"] != original_row["Nome"]
                            descricao_changed = (
                                row["Descricao"] != original_row["Descricao"]
                            )
                            campus_changed = row["Campus"] != original_row["Campus"]

                            if nome_changed or descricao_changed or campus_changed:
                                nome = str(row["Nome"]).strip()
                                descricao = str(row["Descricao"]).strip()
                                campus_id = row["Campus"]

                                if not nome:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        "Nome do prédio é obrigatório",
                                        action="update",
                                    )
                                    errors_occurred = True
                                    continue

                                if not descricao:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        "Descrição do prédio é obrigatória",
                                        action="update",
                                    )
                                    errors_occurred = True
                                    continue

                                if not campus_id or pd.isna(campus_id):
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        "Campus deve ser selecionado",
                                        action="update",
                                    )
                                    errors_occurred = True
                                    continue

                                try:
                                    with get_db_session() as session:
                                        predio_repo_update = PredioRepository(session)
                                        # Get current predio
                                        current = predio_repo_update.get_by_id(
                                            predio_id
                                        )

                                        if current:
                                            # Check if new nome already exists (excluding current)
                                            if (
                                                nome_changed
                                                and nome != original_row["Nome"]
                                            ):
                                                existing_all = (
                                                    predio_repo_update.get_all()
                                                )
                                                existing_names = [
                                                    p.nome.lower()
                                                    for p in existing_all
                                                    if p.id != predio_id
                                                ]
                                                if nome.lower() in existing_names:
                                                    set_session_feedback(
                                                        "crud_result",
                                                        False,
                                                        f"Prédio '{nome}' já existe",
                                                        action="update",
                                                    )
                                                    errors_occurred = True
                                                    continue

                                            # Update fields
                                            predio_dto = PredioCreate(
                                                nome=nome,
                                                descricao=descricao,
                                                campus_id=int(campus_id),
                                            )
                                            predio_repo_update.update(
                                                predio_id, predio_dto
                                            )

                                            campus_name = campus_options.get(
                                                int(campus_id), "N/A"
                                            )
                                            set_session_feedback(
                                                "crud_result",
                                                True,
                                                f"Prédio {nome} ({descricao}) atualizado com sucesso!",
                                                action="update",
                                            )
                                            changes_made = True
                                except Exception as e:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        f"Erro ao atualizar prédio: {str(e)}",
                                        action="update",
                                    )
                                    errors_occurred = True

                    if changes_made:
                        st.rerun()
                    # If only errors occurred, avoid rerun so user can fix values

                # Display CRUD result if available
                display_session_feedback("crud_result")

            else:
                st.info(
                    "📭 Nenhum prédio cadastrado ainda. Use a tabela acima para adicionar o primeiro prédio."
                )
                if not campi:
                    st.warning(
                        "ℹ️ Primeiro, cadastre ao menos um campus na aba 'Campi' para poder criar prédios."
                    )

    except Exception as e:
        st.error(f"❌ Erro ao carregar prédios: {str(e)}")
