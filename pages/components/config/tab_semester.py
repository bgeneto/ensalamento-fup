"""
Semester Management Tab Component

CRUD operations for semester management.
"""

from datetime import date, datetime

import pandas as pd
import streamlit as st

from src.config.database import get_db_session
from src.models.academic import Semestre
from src.repositories.semestre import SemestreRepository
from src.services.semester_service import validate_semester_name
from src.utils.cache_helpers import get_semester_options
from src.utils.ui_feedback import display_session_feedback, set_session_feedback


def _normalize_optional_date(value):
    """Convert editor values to Python date objects or None."""
    if value is None:
        return None
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        return datetime.strptime(text, "%Y-%m-%d").date()
    raise ValueError("Formato de data inválido. Use AAAA-MM-DD.")


def _validate_semester_date_range(data_inicial, data_final):
    """Validate semester date ordering when both dates are present."""
    if data_inicial and data_final and data_final < data_inicial:
        raise ValueError(
            "Data final do semestre deve ser maior ou igual à data inicial"
        )


def render_semester_tab():
    """Render the semester management tab."""

    st.subheader("📝 Gerenciamento de Semestres")

    st.info(
        """
        ℹ️ Edite os dados diretamente na tabela abaixo.
        - Para **adicionar**, clique em ✚ no canto superior direito da tabela.
        - Para **remover**, selecione a linha correspondente clicando na primeira coluna e, em seguida, exclua a linha clicando no ícone 🗑️ no canto superior direito da tabela.
        - Para **alterar** um dado, dê um clique duplo na célula da tabela. As edições serão salvas automaticamente.
        - Para **ativar** um semestre existente, marque o checkbox na coluna "Ativo" (todos os outros serão automaticamente desativados).

        **⚠️ IMPORTANTE:** O sistema mantém automaticamente apenas um semestre ativo por vez.
        """
    )

    # Semester list with CRUD
    try:
        with get_db_session() as session:
            semester_repo = SemestreRepository(session)
            semestres = semester_repo.get_all()

            if semestres:
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
                            "Data Inicial": sem.data_inicial,
                            "Data Final": sem.data_final,
                        }
                    )

                df = pd.DataFrame(semester_data)

                # Sort by Nome (Name) in descending order (most recent first)
                df = df.sort_values(by=["Nome"], ascending=False).reset_index(drop=True)

                # Use st.data_editor with dynamic num_rows for CRUD operations
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
                        "Data Inicial": st.column_config.DateColumn(
                            "Data Inicial",
                            help="Data de início do semestre (opcional)",
                            format="DD/MM/YYYY",
                        ),
                        "Data Final": st.column_config.DateColumn(
                            "Data Final",
                            help="Data de término do semestre (opcional)",
                            format="DD/MM/YYYY",
                        ),
                        "Ativo": st.column_config.CheckboxColumn(
                            "Ativo",
                            help="Marque para ativar este semestre (desativa todos os outros automaticamente)",
                            disabled=False,
                        ),
                    },
                    key="semester_table_editor",
                )

                # Process changes
                changes_made = False

                # Detect additions or deletions
                original_ids = set(df["ID"].astype(int))
                edited_ids = set(edited_df[edited_df["ID"].notna()]["ID"].astype(int))

                # Handle deletions
                deleted_ids = original_ids - edited_ids
                if deleted_ids:
                    try:
                        with get_db_session() as session:
                            semester_repo_delete = SemestreRepository(session)
                            for semester_id in deleted_ids:
                                semester_repo_delete.delete(int(semester_id))

                            activated = (
                                semester_repo_delete.activate_highest_id_semester()
                            )
                            if activated:
                                st.session_state.global_semester_id = activated.id
                                set_session_feedback(
                                    "crud_result",
                                    True,
                                    f"{len(deleted_ids)} semestre(s) removido(s). Semestre '{activated.nome}' (ID: {activated.id}) foi automaticamente ativado.",
                                    action="delete",
                                )
                            else:
                                st.session_state.global_semester_id = None
                                set_session_feedback(
                                    "crud_result",
                                    True,
                                    f"{len(deleted_ids)} semestre(s) removido(s). Nenhum semestre restante para ativar.",
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

                # Handle additions
                new_rows = edited_df[
                    (edited_df["ID"].isna()) | (edited_df["ID"] == 0)
                ].copy()
                if not new_rows.empty:
                    created = 0
                    for idx, row in new_rows.iterrows():
                        nome = str(row["Nome"]).strip()
                        data_inicial = _normalize_optional_date(row.get("Data Inicial"))
                        data_final = _normalize_optional_date(row.get("Data Final"))

                        if not nome:
                            set_session_feedback(
                                "crud_result",
                                False,
                                "Nome do semestre é obrigatório",
                                action="create",
                            )
                            continue

                        try:
                            validated_name = validate_semester_name(nome)
                            _validate_semester_date_range(data_inicial, data_final)

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
                                    continue

                                session.query(Semestre).update({"status": False})
                                session.flush()

                                new_semester_obj = Semestre(
                                    nome=validated_name,
                                    status=True,
                                    data_inicial=data_inicial,
                                    data_final=data_final,
                                )
                                session.add(new_semester_obj)
                                session.commit()

                                new_semester = semester_repo_create.orm_to_dto(
                                    new_semester_obj
                                )

                                st.session_state.global_semester_id = new_semester.id

                                created += 1
                                set_session_feedback(
                                    "crud_result",
                                    True,
                                    f"Semestre '{validated_name}' criado e ativado automaticamente (todos os outros desativados).",
                                    action="create",
                                )

                        except ValueError as ve:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro de validação: {str(ve)}",
                                action="create",
                            )
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao criar semestre: {str(e)}",
                                action="create",
                            )

                    if created > 0:
                        changes_made = True

                # Handle updates
                for idx, row in edited_df.iterrows():
                    if idx < len(df):
                        original_row = df.iloc[idx]
                        semester_id = int(row["ID"])

                        current_data_inicial = _normalize_optional_date(
                            row.get("Data Inicial")
                        )
                        current_data_final = _normalize_optional_date(
                            row.get("Data Final")
                        )
                        original_data_inicial = _normalize_optional_date(
                            original_row.get("Data Inicial")
                        )
                        original_data_final = _normalize_optional_date(
                            original_row.get("Data Final")
                        )

                        nome_changed = row["Nome"] != original_row["Nome"]
                        ativo_changed = row["Ativo"] != original_row["Ativo"]
                        data_inicial_changed = (
                            current_data_inicial != original_data_inicial
                        )
                        data_final_changed = current_data_final != original_data_final

                        if (
                            nome_changed
                            or ativo_changed
                            or data_inicial_changed
                            or data_final_changed
                        ):
                            nome = str(row["Nome"]).strip()
                            ativo = bool(row["Ativo"])

                            if not nome:
                                set_session_feedback(
                                    "crud_result",
                                    False,
                                    "Nome do semestre é obrigatório",
                                    action="update",
                                )
                                continue

                            try:
                                validated_name = nome
                                if nome_changed:
                                    validated_name = validate_semester_name(nome)
                                _validate_semester_date_range(
                                    current_data_inicial, current_data_final
                                )

                                with get_db_session() as session:
                                    semester_repo_update = SemestreRepository(session)
                                    current = session.get(Semestre, semester_id)

                                    if current:
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
                                                continue

                                        if nome_changed:
                                            current.nome = validated_name
                                        if data_inicial_changed:
                                            current.data_inicial = current_data_inicial
                                        if data_final_changed:
                                            current.data_final = current_data_final

                                        if ativo_changed:
                                            if ativo:
                                                session.query(Semestre).update(
                                                    {"status": False}
                                                )
                                                session.flush()
                                                current.status = True
                                                session.commit()

                                                st.session_state.global_semester_id = (
                                                    semester_id
                                                )

                                                set_session_feedback(
                                                    "crud_result",
                                                    True,
                                                    f"Semestre '{validated_name}' ativado (outros desativados automaticamente).",
                                                    action="update",
                                                )
                                                changes_made = True
                                                continue
                                            else:
                                                current.status = False
                                                session.flush()

                                                highest = (
                                                    session.query(Semestre)
                                                    .filter(Semestre.id != semester_id)
                                                    .order_by(Semestre.id.desc())
                                                    .first()
                                                )

                                                if highest:
                                                    highest.status = True
                                                    session.commit()

                                                    st.session_state.global_semester_id = highest.id

                                                    set_session_feedback(
                                                        "crud_result",
                                                        True,
                                                        f"Semestre '{validated_name}' desativado. Semestre '{highest.nome}' (ID: {highest.id}) foi automaticamente ativado.",
                                                        action="update",
                                                    )
                                                else:
                                                    session.commit()
                                                    st.session_state.global_semester_id = None
                                                    set_session_feedback(
                                                        "crud_result",
                                                        True,
                                                        f"Semestre '{validated_name}' desativado. Nenhum outro semestre disponível para ativar.",
                                                        action="update",
                                                    )

                                                changes_made = True
                                                continue

                                        session.commit()

                                        set_session_feedback(
                                            "crud_result",
                                            True,
                                            f"Semestre '{validated_name}' atualizado com sucesso",
                                            action="update",
                                        )
                                        changes_made = True

                            except ValueError as ve:
                                set_session_feedback(
                                    "crud_result",
                                    False,
                                    f"Erro de validação: {str(ve)}",
                                    action="update",
                                )
                            except Exception as e:
                                set_session_feedback(
                                    "crud_result",
                                    False,
                                    f"Erro ao atualizar semestre: {str(e)}",
                                    action="update",
                                )

                if changes_made:
                    get_semester_options.clear()
                    st.rerun()

                display_session_feedback("crud_result")

            else:
                st.info(
                    "📭 Nenhum semestre cadastrado ainda. Adicione uma nova linha na tabela acima para criar o primeiro semestre."
                )

    except Exception as e:
        st.error(f"❌ Erro ao carregar semestres: {str(e)}")
