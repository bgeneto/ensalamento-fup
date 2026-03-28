"""
Campus Management Tab Component

Handles CRUD operations for Campi (Campuses).
Extracted from the main inventory page for better maintainability.
"""

import os

# Needs to be imported from auth module for shared imports
import sys

import pandas as pd
import streamlit as st

from src.config.database import get_db_session
from src.repositories.campus import CampusRepository
from src.schemas.inventory import CampusCreate
from src.utils.ui_feedback import display_session_feedback, set_session_feedback

sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def render_campus_tab():
    st.subheader("🏫 Gerenciamento de Campi")

    st.info(
        """
        ℹ️ Edite os dados diretamente na tabela abaixo.
        - Para **adicionar**, clique em ✚ no canto superior direito da tabela.
        - Para **remover**, selecione a linha correspondente clicando na primeira coluna e, em seguida, exclua a linha clicando no ícone 🗑️ no canto superior direito da tabela.
        - Para **alterar** um dado, dê um clique duplo na célula da tabela. As edições serão salvas automaticamente.
        """
    )

    # Campus list with CRUD
    try:
        with get_db_session() as session:
            campus_repo = CampusRepository(session)
            campi = campus_repo.get_all()

            if campi:
                # Display summary
                st.markdown(f"**Total de campi encontrados: {len(campi)}**")

                # Create DataFrame with editable columns
                campus_data = []
                for campus in campi:
                    campus_data.append(
                        {
                            "ID": campus.id,
                            "Nome": campus.nome,
                            "Descrição": campus.descricao or "",
                        }
                    )

                df = pd.DataFrame(campus_data)

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
                            help="Nome do campus",
                        ),
                        "Descrição": st.column_config.TextColumn(
                            "Descrição",
                            help="Descrição opcional do campus",
                        ),
                    },
                    key="campus_table_editor",
                )

                # Process changes from data editor
                if len(edited_df) != len(df):
                    # Batch additions/deletions to avoid repeated reruns
                    changes_made = False

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
                                campus_repo_delete = CampusRepository(session)
                                for campus_id in deleted_ids:
                                    campus_repo_delete.delete(int(campus_id))
                            set_session_feedback(
                                "crud_result",
                                True,
                                f"{len(deleted_ids)} campus(s) removido(s) com sucesso",
                                action="delete",
                            )
                            changes_made = True
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao deletar campus: {str(e)}",
                                action="delete",
                            )

                    # Handle additions (new rows with NaN or 0 ID)
                    new_rows = edited_df[
                        (edited_df["ID"].isna()) | (edited_df["ID"] == 0)
                    ].copy()
                    if not new_rows.empty:
                        created = 0
                        try:
                            with get_db_session() as session:
                                campus_repo_create = CampusRepository(session)
                                for idx, row in new_rows.iterrows():
                                    nome = str(row["Nome"]).strip()
                                    descricao = str(row["Descrição"]).strip()
                                    if not nome:
                                        nome = None
                                    if not descricao:
                                        descricao = None

                                    if not nome:
                                        set_session_feedback(
                                            "crud_result",
                                            False,
                                            "Nome do campus é obrigatório",
                                            action="create",
                                        )
                                        continue

                                    # Check if already exists
                                    existing = campus_repo_create.get_all()
                                    existing_names = [c.nome.lower() for c in existing]
                                    if nome.lower() in existing_names:
                                        set_session_feedback(
                                            "crud_result",
                                            False,
                                            f"Campus '{nome}' já existe no banco de dados",
                                            action="create",
                                        )
                                        continue

                                    campus_dto = CampusCreate(
                                        nome=nome,
                                        descricao=descricao,
                                    )
                                    campus_repo_create.create(campus_dto)
                                    created += 1

                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao criar campus: {str(e)}",
                                action="create",
                            )

                        if created:
                            set_session_feedback(
                                "crud_result",
                                True,
                                f"{created} campus(s) adicionado(s) com sucesso",
                                action="create",
                            )
                            changes_made = True

                    if changes_made:
                        st.rerun()
                    # If only errors occurred, avoid rerun so the user can edit

                # Handle updates (rows with changes in existing records)
                else:
                    for idx, row in edited_df.iterrows():
                        if idx < len(df):
                            original_row = df.iloc[idx]
                            campus_id = int(row["ID"])

                            # Check if any field changed
                            nome_changed = row["Nome"] != original_row["Nome"]
                            descricao_changed = (
                                row["Descrição"] != original_row["Descrição"]
                            )

                            if nome_changed or descricao_changed:
                                nome = str(row["Nome"]).strip()
                                descricao = str(row["Descrição"]).strip()
                                if not nome:
                                    nome = None
                                if not descricao:
                                    descricao = None

                                if not nome:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        "Nome do campus é obrigatório",
                                        action="update",
                                    )
                                    st.rerun()

                                try:
                                    with get_db_session() as session:
                                        campus_repo_update = CampusRepository(session)
                                        # Get current campus
                                        current = campus_repo_update.get_by_id(
                                            campus_id
                                        )

                                        if current:
                                            # Check if new nome already exists (excluding current)
                                            if (
                                                nome_changed
                                                and nome != original_row["Nome"]
                                            ):
                                                existing_all = (
                                                    campus_repo_update.get_all()
                                                )
                                                existing_names = [
                                                    c.nome.lower()
                                                    for c in existing_all
                                                    if c.id != campus_id
                                                ]
                                                if nome.lower() in existing_names:
                                                    set_session_feedback(
                                                        "crud_result",
                                                        False,
                                                        f"Campus '{nome}' já existe",
                                                        action="update",
                                                    )
                                                    st.rerun()

                                            # Update fields
                                            campus_dto = CampusCreate(
                                                nome=nome,
                                                descricao=descricao,
                                            )
                                            campus_repo_update.update(
                                                campus_id, campus_dto
                                            )

                                            set_session_feedback(
                                                "crud_result",
                                                True,
                                                f"Campus {nome} atualizado com sucesso",
                                                action="update",
                                            )
                                except Exception as e:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        f"Erro ao atualizar campus: {str(e)}",
                                        action="update",
                                    )
                                st.rerun()

                # Display CRUD result if available
                display_session_feedback("crud_result")

            else:
                st.info(
                    "📭 Nenhum campus cadastrado ainda. Use a tabela acima para adicionar o primeiro campus."
                )

    except Exception as e:
        st.error(f"❌ Erro ao carregar campi: {str(e)}")
