"""
Config/Settings Page

Comprehensive app settings configuration for things like semester etc...
"""

# Import the auth and setup module
from pages.components.auth import initialize_page
from pages.components.inventory.tab_campus import render_campus_tab
from pages.components.inventory.tab_buildings import render_buildings_tab
from pages.components.inventory.tab_rooms import render_rooms_tab
from pages.components.inventory.tab_associations import render_associations_tab
from pages.components.ui import page_footer

# ============================================================================
# IMPORTS FOR SEMESTER CRUD
# ============================================================================

import pandas as pd
from datetime import datetime

from src.repositories.semestre import SemestreRepository
from src.schemas.academic import SemestreCreate
from src.models.academic import Semestre
from src.config.database import get_db_session
from src.utils.ui_feedback import (
    display_session_feedback,
    set_session_feedback,
)
from src.utils.cache_helpers import get_semester_options
from src.services.semester_service import (
    create_and_activate_semester,
    validate_semester_name,
)

# Initialize page with authentication and configuration
if not initialize_page(
    page_title="Configurações - Ensalamento",
    page_icon="⚙️",
    layout="centered",
    key_suffix="config",
):
    st.stop()

# ============================================================================
# PAGE HEADER
# ============================================================================
import streamlit as st

st.title("🏢 Configurações do Sistema")
st.markdown(
    "Configure as definições globais do sistema, como semestres, usuários e preferências."
)

st.subheader("📝 Gerenciamento de Semestres")

st.info(
    """
    Edite os dados diretamente na tabela abaixo.
    - Para **adicionar**, clique em ✚ no canto superior direito da tabela.
    - Para **remover**, selecione a linha correspondente clicando na primeira coluna e, em seguida, exclua a linha clicando no ícone 🗑️ no canto superior direito da tabela.
    - Para **alterar** um dado, dê um clique duplo na célula da tabela. As edições serão salvas automaticamente.
    """
)

# Semester list with CRUD
try:
    with get_db_session() as session:
        semester_repo = SemestreRepository(session)
        semestres = semester_repo.get_all()

        if semestres:
            # Display tips
            st.markdown(
                "**💡 IMPORTANTE:** *Apenas um semestre pode estar ativo no sistema.*"
            )
            # Display summary
            st.markdown(f"**Total de semestres encontrados: {len(semestres)}**")
            # Create DataFrame with editable columns
            semester_data = []
            for sem in semestres:
                semester_data.append(
                    {
                        "ID": sem.id,
                        "Nome": sem.nome,
                        "Ativo": sem.status,
                    }
                )

            df = pd.DataFrame(semester_data)

            # Sort by Nome (Name) in descending order (most recent first)
            df = df.sort_values(by=["Nome"], ascending=False).reset_index(drop=True)

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
                        help="Nome do semestre (formato: AAAA-N, ex: 2025-1, 2026-2)",
                    ),
                    "Ativo": st.column_config.CheckboxColumn(
                        "Ativo",
                        help="Marque se este é o semestre corrente",
                    ),
                },
                key="semester_table_editor",
            )

            # Process changes from data editor in batch order: deletions, additions, updates
            changes_made = False
            errors_occurred = False

            # Detect additions or deletions
            original_ids = set(df["ID"].astype(int))
            edited_ids = set(edited_df[edited_df["ID"].notna()]["ID"].astype(int))

            # Handle deletions (rows removed from edited_df)
            deleted_ids = original_ids - edited_ids
            if deleted_ids:
                try:
                    with get_db_session() as session:
                        semester_repo_delete = SemestreRepository(session)
                        for semester_id in deleted_ids:
                            semester_repo_delete.delete(int(semester_id))
                    set_session_feedback(
                        "crud_result",
                        True,
                        f"{len(deleted_ids)} semestre(s) removido(s) com sucesso!",
                        action="delete",
                    )
                    changes_made = True
                except Exception as e:
                    set_session_feedback(
                        "crud_result",
                        False,
                        f"Erro ao deletar semestre(s): {str(e)}",
                        action="delete",
                    )
                    errors_occurred = True

            # Handle additions (new rows with NaN or 0 ID)
            new_rows = edited_df[
                (edited_df["ID"].isna()) | (edited_df["ID"] == 0)
            ].copy()
            if not new_rows.empty:
                created = 0
                for idx, row in new_rows.iterrows():
                    nome = str(row["Nome"]).strip()
                    ativo = bool(row["Ativo"])

                    if not nome:
                        set_session_feedback(
                            "crud_result",
                            False,
                            "Nome do semestre é obrigatório",
                            action="create",
                        )
                        errors_occurred = True
                        continue

                    try:
                        # Validate semester name format first (for both active and inactive)
                        validated_name = validate_semester_name(nome)

                        if ativo:
                            # Use service method for active semesters (handles deactivation of others)
                            result = create_and_activate_semester(validated_name)
                            if result["success"]:
                                set_session_feedback(
                                    "crud_result",
                                    True,
                                    result["message"],
                                    action="create",
                                )
                                created += 1
                        else:
                            # Check if already exists
                            with get_db_session() as session:
                                semester_repo_create = SemestreRepository(session)
                                existing = semester_repo_create.get_by_name(
                                    validated_name
                                )
                                if existing:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        f"Nome '{validated_name}' já existe no banco de dados",
                                        action="create",
                                    )
                                    errors_occurred = True
                                    continue

                                # Create inactive semester normally - use dict as expected by repository
                                semester_repo_create.create(
                                    {"nome": validated_name, "status": ativo}
                                )
                            created += 1
                            set_session_feedback(
                                "crud_result",
                                True,
                                f"Semestre '{validated_name}' criado com sucesso!",
                                action="create",
                            )

                    except ValueError as ve:
                        set_session_feedback(
                            "crud_result",
                            False,
                            f"Erro de validação: {str(ve)}",
                            action="create",
                        )
                        errors_occurred = True
                    except Exception as e:
                        set_session_feedback(
                            "crud_result",
                            False,
                            f"Erro ao criar semestre: {str(e)}",
                            action="create",
                        )
                        errors_occurred = True

                if created > 0 and not errors_occurred:
                    changes_made = True

            # Handle updates (rows with changes in existing records)
            for idx, row in edited_df.iterrows():
                if idx < len(df):
                    original_row = df.iloc[idx]
                    semester_id = int(row["ID"])

                    # Check if any field changed
                    nome_changed = row["Nome"] != original_row["Nome"]
                    ativo_changed = row["Ativo"] != original_row["Ativo"]

                    if nome_changed or ativo_changed:
                        nome = str(row["Nome"]).strip()
                        ativo = bool(row["Ativo"])

                        if not nome:
                            set_session_feedback(
                                "crud_result",
                                False,
                                "Nome do semestre é obrigatório",
                                action="update",
                            )
                            errors_occurred = True
                            continue

                        try:
                            # Validate semester name format if it's being changed
                            validated_name = nome
                            if nome_changed:
                                validated_name = validate_semester_name(nome)

                            with get_db_session() as session:
                                semester_repo_update = SemestreRepository(session)
                                # Get current semester
                                current = session.get(Semestre, semester_id)

                                if current:
                                    # Check if new name already exists (excluding current)
                                    if nome_changed:
                                        existing = semester_repo_update.get_by_name(
                                            validated_name
                                        )
                                        if existing and existing.id != semester_id:
                                            set_session_feedback(
                                                "crud_result",
                                                False,
                                                f"Nome '{validated_name}' já existe",
                                                action="update",
                                            )
                                            errors_occurred = True
                                            continue

                                    # Update fields
                                    current.nome = validated_name

                                    # If activating this semester, ensure it's the only active one
                                    if ativo and not current.status:
                                        # First, deactivate ALL active semesters
                                        session.query(Semestre).filter(
                                            Semestre.status == True
                                        ).update({"status": False})

                                        # Then activate the current one
                                        current.status = True
                                    elif not ativo and current.status:
                                        # Just deactivate this one (no need to activate another)
                                        current.status = ativo
                                    else:
                                        # No change to active status, just update fields
                                        current.status = ativo

                                    session.commit()

                                    set_session_feedback(
                                        "crud_result",
                                        True,
                                        f"Semestre {validated_name} atualizado com sucesso!",
                                        action="update",
                                    )
                                    changes_made = True
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao atualizar semestre: {str(e)}",
                                action="update",
                            )
                            errors_occurred = True

            # If any DB changes were made, clear caches and rerun once to refresh the table.
            if changes_made:
                # Clear semester options cache since semester data changed
                get_semester_options.clear()
                st.rerun()
            # If only errors occurred, do NOT rerun so user can edit the row in-place.
            # display_session_feedback will show the error toast below.

            # Display CRUD result if available
            display_session_feedback("crud_result")

        else:
            st.info(
                "📭 Nenhum semestre cadastrado ainda. Adicione uma nova linha na tabela acima para criar o primeiro semestre."
            )

except Exception as e:
    st.error(f"❌ Erro ao carregar semestres: {str(e)}")

# ============================================================================
# OTHER SETTINGS SECTIONS (to be added later)
# ============================================================================

# Page Footer
page_footer.show()
