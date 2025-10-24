"""
Rooms Management Tab Component

Handles CRUD operations for Salas (Rooms), Caracteristicas (Characteristics),
and TipoSala (Room Types). This is the most complex tab as it includes
three related entities.
Extracted from the main inventory page for better maintainability.
"""

import streamlit as st
import pandas as pd
from src.repositories.sala import SalaRepository
from src.repositories.predio import PredioRepository
from src.repositories.tipo_sala import TipoSalaRepository
from src.repositories.caracteristica import CaracteristicaRepository
from src.schemas.inventory import (
    SalaRead,
    SalaUpdate,
    TipoSalaCreate,
    CaracteristicaCreate,
)
from src.config.database import get_db_session
from src.utils.ui_feedback import display_session_feedback, set_session_feedback
from src.utils.cache_helpers import (
    get_predio_options,
    get_tipo_sala_options,
    get_caracteristica_options,
)

# Needs to be imported from auth module for shared imports
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def render_rooms_tab():
    st.subheader("🚪 Gerenciamento de Salas")

    st.info(
        """
        Edite os dados diretamente na tabela abaixo. Para salas, é necessário selecionar um prédio e tipo de sala existentes.
        - Para **adicionar**, clique em ✚ no canto superior direito da tabela.
        - Para **remover**, selecione a linha correspondente clicando na primeira coluna e, em seguida, exclua a linha clicando no ícone 🗑️ no canto superior direito da tabela.
        - Para **alterar** um dado, dê um clique duplo na célula da tabela. As edições serão salvas automaticamente.
        """
    )

    # Room list with CRUD
    try:
        with get_db_session() as session:
            sala_repo = SalaRepository(session)

            # Get rooms
            salas = sala_repo.get_all()

            # Get cached lookup dictionaries
            predio_options = get_predio_options()
            tipo_sala_options = get_tipo_sala_options()

            if salas:
                # Display summary
                st.markdown(f"**Total de salas encontradas: {len(salas)}**")

                # Create DataFrame with editable columns
                sala_data = []
                for sala in salas:
                    sala_data.append(
                        {
                            "ID": sala.id,
                            "Nome": sala.nome,
                            "Descrição": sala.descricao or "",
                            "Tipo Sala": sala.tipo_sala_id,
                            "Prédio": sala.predio_id,
                            "Capacidade": sala.capacidade,
                            "Andar": sala.andar,  # Integer field
                        }
                    )

                df = pd.DataFrame(sala_data)

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
                            help="Nome da sala",
                        ),
                        "Prédio": st.column_config.SelectboxColumn(
                            "Prédio",
                            options=list(predio_options.keys()),
                            format_func=lambda x: (
                                predio_options.get(x, "N/A") if x else "Selecionar..."
                            ),
                            required=True,
                            help="Prédio onde a sala está localizada",
                        ),
                        "Tipo Sala": st.column_config.SelectboxColumn(
                            "Tipo Sala",
                            options=list(tipo_sala_options.keys()),
                            format_func=lambda x: (
                                tipo_sala_options.get(x, "N/A")
                                if x
                                else "Selecionar..."
                            ),
                            required=True,
                            help="Tipo da sala (sala de aula, laboratório, etc.)",
                        ),
                        "Capacidade": st.column_config.NumberColumn(
                            "Capacidade",
                            min_value=1,
                            help="Número de pessoas que a sala comporta",
                        ),
                        "Andar": st.column_config.NumberColumn(
                            "Andar",
                            help="Andar onde a sala está localizada (opcional)",
                        ),
                        "Tipo Assento": st.column_config.TextColumn(
                            "Tipo Assento",
                            help="Tipo de assento (ex: carteira, poltrona)",
                        ),
                    },
                    key="sala_table_editor",
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
                                sala_repo_delete = SalaRepository(session)
                                for sala_id in deleted_ids:
                                    sala_repo_delete.delete(int(sala_id))
                            set_session_feedback(
                                "crud_result",
                                True,
                                f"{len(deleted_ids)} sala(s) removida(s) com sucesso!",
                                action="delete",
                            )
                            changes_made = True
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao deletar sala(s): {str(e)}",
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
                                sala_repo_create = SalaRepository(session)
                                for idx, row in new_rows.iterrows():
                                    nome = str(row["Nome"]).strip()
                                    descricao = str(row["Descrição"]).strip()
                                    predio_id = row["Prédio"]
                                    tipo_sala_id = row["Tipo Sala"]
                                    capacidade = row["Capacidade"]
                                    andar = row["Andar"]

                                    if not nome:
                                        set_session_feedback(
                                            "crud_result",
                                            False,
                                            "Nome da sala é obrigatório",
                                            action="create",
                                        )
                                        errors_occurred = True
                                        continue

                                    if not predio_id or pd.isna(predio_id):
                                        set_session_feedback(
                                            "crud_result",
                                            False,
                                            "Prédio deve ser selecionado",
                                            action="create",
                                        )
                                        errors_occurred = True
                                        continue

                                    if not tipo_sala_id or pd.isna(tipo_sala_id):
                                        set_session_feedback(
                                            "crud_result",
                                            False,
                                            "Tipo de sala deve ser selecionado",
                                            action="create",
                                        )
                                        errors_occurred = True
                                        continue

                                    if (
                                        not capacidade
                                        or pd.isna(capacidade)
                                        or capacidade < 1
                                    ):
                                        set_session_feedback(
                                            "crud_result",
                                            False,
                                            "Capacidade deve ser um número maior que 0",
                                            action="create",
                                        )
                                        errors_occurred = True
                                        continue

                                    # Clean up optional fields
                                    if pd.isna(andar) or andar == "":
                                        andar = None
                                    else:
                                        andar = int(andar)

                                    if not descricao:
                                        descricao = None

                                    # Create room - repository should validate foreign keys
                                    sala_dto = SalaRead(
                                        nome=nome,
                                        predio_id=int(predio_id),
                                        tipo_sala_id=int(tipo_sala_id),
                                        capacidade=int(capacidade),
                                        andar=andar,
                                        descricao=descricao,
                                    )
                                    sala_repo_create.create(sala_dto)
                                    created += 1
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao criar sala(s): {str(e)}",
                                action="create",
                            )
                            errors_occurred = True

                        if created:
                            set_session_feedback(
                                "crud_result",
                                True,
                                f"{created} sala(s) adicionado(s) com sucesso!",
                                action="create",
                            )
                            changes_made = True

                    if changes_made:
                        st.rerun()
                        # If only errors occurred, avoid rerun so user can edit

                        try:
                            with get_db_session() as session:
                                sala_repo_create = SalaRepository(session)
                                # Check if already exists (unique constraint on nome + predio_id)
                                existing = sala_repo_create.get_all()
                                existing_combinations = [
                                    (s.nome.lower(), s.predio_id) for s in existing
                                ]
                                if (
                                    nome.lower(),
                                    int(predio_id),
                                ) in existing_combinations:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        f"Sala '{nome}' já existe neste prédio",
                                        action="create",
                                    )
                                else:
                                    from src.schemas.inventory import SalaCreate

                                    sala_dto = SalaCreate(
                                        nome=nome,
                                        predio_id=int(predio_id),
                                        tipo_sala_id=int(tipo_sala_id),
                                        capacidade=int(capacidade),
                                        andar=andar,
                                        descricao=descricao,
                                    )
                                    sala_repo_create.create(sala_dto)
                                    predio_nome = predio_options.get(
                                        int(predio_id), "N/A"
                                    )
                                    set_session_feedback(
                                        "crud_result",
                                        True,
                                        f"Sala {nome} adicionada com sucesso ao prédio {predio_nome}!",
                                        action="create",
                                    )
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao criar sala: {str(e)}",
                                action="create",
                            )
                        st.rerun()

                # Handle updates (rows with changes in existing records)
                else:
                    changes_made = False
                    errors_occurred = False

                    for idx, row in edited_df.iterrows():
                        if idx < len(df):
                            original_row = df.iloc[idx]
                            sala_id = int(row["ID"])

                            # Check if any field changed
                            nome_changed = row["Nome"] != original_row["Nome"]
                            predio_changed = row["Prédio"] != original_row["Prédio"]
                            tipo_sala_changed = (
                                row["Tipo Sala"] != original_row["Tipo Sala"]
                            )
                            capacidade_changed = (
                                row["Capacidade"] != original_row["Capacidade"]
                            )
                            andar_changed = row["Andar"] != original_row["Andar"]
                            descricao_changed = (
                                row["Descrição"] != original_row["Descrição"]
                            )

                            if any(
                                [
                                    nome_changed,
                                    predio_changed,
                                    tipo_sala_changed,
                                    capacidade_changed,
                                    andar_changed,
                                    descricao_changed,
                                ]
                            ):
                                nome = str(row["Nome"]).strip()
                                predio_id = row["Prédio"]
                                tipo_sala_id = row["Tipo Sala"]
                                capacidade = row["Capacidade"]
                                andar = row["Andar"]
                                descricao = str(row["Descrição"]).strip()

                                if not nome:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        "Nome da sala é obrigatório",
                                        action="update",
                                    )
                                    errors_occurred = True
                                    continue

                                if not predio_id or pd.isna(predio_id):
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        "Prédio deve ser selecionado",
                                        action="update",
                                    )
                                    errors_occurred = True
                                    continue

                                if not tipo_sala_id or pd.isna(tipo_sala_id):
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        "Tipo de sala deve ser selecionado",
                                        action="update",
                                    )
                                    errors_occurred = True
                                    continue

                                if (
                                    not capacidade
                                    or pd.isna(capacidade)
                                    or capacidade < 1
                                ):
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        "Capacidade deve ser um número maior que 0",
                                        action="update",
                                    )
                                    errors_occurred = True
                                    continue

                                # Clean up optional fields
                                if pd.isna(andar) or andar == "":
                                    andar = None
                                else:
                                    andar = int(andar)

                                if not descricao:
                                    descricao = None

                                try:
                                    with get_db_session() as session:
                                        sala_repo_update = SalaRepository(session)
                                        # Get current sala
                                        current = sala_repo_update.get_by_id(sala_id)

                                        if current:
                                            # Check if new nome/predio combination already exists (excluding current)
                                            if nome_changed or predio_changed:
                                                existing_all = (
                                                    sala_repo_update.get_all()
                                                )
                                                existing_combinations = [
                                                    (s.nome.lower(), s.predio_id)
                                                    for s in existing_all
                                                    if s.id != sala_id
                                                ]
                                                if (
                                                    nome.lower(),
                                                    int(predio_id),
                                                ) in existing_combinations:
                                                    set_session_feedback(
                                                        "crud_result",
                                                        False,
                                                        f"Sala '{nome}' já existe neste prédio",
                                                        action="update",
                                                    )
                                                    errors_occurred = True
                                                    continue

                                            # Update fields
                                            from src.schemas.inventory import SalaUpdate

                                            sala_update_dto = SalaUpdate(
                                                nome=nome,
                                                predio_id=int(predio_id),
                                                tipo_sala_id=int(tipo_sala_id),
                                                capacidade=int(capacidade),
                                                andar=andar,
                                                descricao=descricao,
                                            )
                                            sala_repo_update.update(
                                                sala_id, sala_update_dto
                                            )

                                            predio_nome = predio_options.get(
                                                int(predio_id), "N/A"
                                            )
                                            set_session_feedback(
                                                "crud_result",
                                                True,
                                                f"Sala {nome} atualizada com sucesso (Prédio: {predio_nome})!",
                                                action="update",
                                            )
                                            changes_made = True
                                except Exception as e:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        f"Erro ao atualizar sala: {str(e)}",
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
                    "📭 Nenhuma sala cadastrada ainda. Use a tabela acima para adicionar a primeira sala."
                )
                if not predio_options:
                    st.warning(
                        "ℹ️ Primeiro, cadastre ao menos um prédio na aba 'Prédios' para poder criar salas."
                    )
                if not tipo_sala_options:
                    st.warning(
                        "ℹ️ Primeiro, cadastre ao menos um tipo de sala na aba 'Características' para poder criar salas."
                    )

    except Exception as e:
        st.error(f"❌ Erro ao carregar salas: {str(e)}")

    st.subheader("🏷️ Gerenciamento de Características de Salas")

    st.info(
        """Adicione, remova ou edite as características que podem ser associadas às salas.
           Tais associações podem ser realizadas na aba acima (🔗 Assoc. Características).
        """
    )

    # Caracteristica list with CRUD
    try:
        with get_db_session() as session:
            caracteristica_repo = CaracteristicaRepository(session)
            caracteristicas = caracteristica_repo.get_all()

            if caracteristicas:
                # Display summary
                st.markdown(
                    f"**Total de características encontradas: {len(caracteristicas)}**"
                )

                # Create DataFrame with editable columns
                caracteristica_data = []
                for caracteristica in caracteristicas:
                    caracteristica_data.append(
                        {
                            "ID": caracteristica.id,
                            "Nome": caracteristica.nome,
                        }
                    )

                df = pd.DataFrame(caracteristica_data)

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
                            help="Nome da característica (ex: Projetor, Ar-condicionado, Quadro branco)",
                        ),
                    },
                    key="caracteristica_table_editor",
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
                                caracteristica_repo_delete = CaracteristicaRepository(
                                    session
                                )
                                for caracteristica_id in deleted_ids:
                                    caracteristica_repo_delete.delete(
                                        int(caracteristica_id)
                                    )
                            set_session_feedback(
                                "crud_result",
                                True,
                                f"{len(deleted_ids)} característica(s) removida(s) com sucesso!",
                                action="delete",
                            )
                            changes_made = True
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao deletar característica(s): {str(e)}",
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
                                caracteristica_repo_create = CaracteristicaRepository(
                                    session
                                )
                                for idx, row in new_rows.iterrows():
                                    nome = str(row["Nome"]).strip()

                                    if not nome:
                                        set_session_feedback(
                                            "crud_result",
                                            False,
                                            "Nome da característica é obrigatório",
                                            action="create",
                                        )
                                        errors_occurred = True
                                        continue

                                    # Check if already exists
                                    existing = caracteristica_repo_create.get_all()
                                    existing_names = [c.nome.lower() for c in existing]
                                    if nome.lower() in existing_names:
                                        set_session_feedback(
                                            "crud_result",
                                            False,
                                            f"Característica '{nome}' já existe no banco de dados",
                                            action="create",
                                        )
                                        errors_occurred = True
                                        continue

                                    caracteristica_dto = CaracteristicaCreate(nome=nome)
                                    caracteristica_repo_create.create(
                                        caracteristica_dto
                                    )
                                    created += 1

                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao criar característica: {str(e)}",
                                action="create",
                            )
                            errors_occurred = True

                        if created:
                            set_session_feedback(
                                "crud_result",
                                True,
                                f"{created} característica(s) adicionada(s) com sucesso!",
                                action="create",
                            )
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
                            caracteristica_id = int(row["ID"])

                            # Check if any field changed
                            nome_changed = row["Nome"] != original_row["Nome"]

                            if nome_changed:
                                nome = str(row["Nome"]).strip()

                                if not nome:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        "Nome da característica é obrigatório",
                                        action="update",
                                    )
                                    errors_occurred = True
                                    continue

                                try:
                                    with get_db_session() as session:
                                        caracteristica_repo_update = (
                                            CaracteristicaRepository(session)
                                        )
                                        # Get current caracteristica
                                        current = caracteristica_repo_update.get_by_id(
                                            caracteristica_id
                                        )

                                        if current:
                                            # Check if new nome already exists (excluding current)
                                            if nome != original_row["Nome"]:
                                                existing_all = (
                                                    caracteristica_repo_update.get_all()
                                                )
                                                existing_names = [
                                                    c.nome.lower()
                                                    for c in existing_all
                                                    if c.id != caracteristica_id
                                                ]
                                                if nome.lower() in existing_names:
                                                    set_session_feedback(
                                                        "crud_result",
                                                        False,
                                                        f"Característica '{nome}' já existe",
                                                        action="update",
                                                    )
                                                    errors_occurred = True
                                                    continue

                                            # Update fields
                                            caracteristica_dto = CaracteristicaCreate(
                                                nome=nome
                                            )
                                            caracteristica_repo_update.update(
                                                caracteristica_id, caracteristica_dto
                                            )

                                            set_session_feedback(
                                                "crud_result",
                                                True,
                                                f"Característica {nome} atualizada com sucesso!",
                                                action="update",
                                            )
                                            changes_made = True
                                except Exception as e:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        f"Erro ao atualizar característica: {str(e)}",
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
                    "📭 Nenhuma característica cadastrada ainda. Use a tabela acima para adicionar a primeira característica."
                )

    except Exception as e:
        st.error(f"❌ Erro ao carregar características: {str(e)}")

    st.subheader("🧩 Gerenciamento de Tipos de Salas")

    st.info(
        """Adicione, remova ou edite os tipos de salas disponíveis.
           Tipos sala são necessários para criar salas na seção acima.
        """
    )

    # TipoSala list with CRUD
    try:
        with get_db_session() as session:
            tipo_sala_repo = TipoSalaRepository(session)
            tipos_sala = tipo_sala_repo.get_all()

            if tipos_sala:
                # Display summary
                st.markdown(f"**Total de tipos sala encontrados: {len(tipos_sala)}**")

                # Create DataFrame with editable columns
                tipo_sala_data = []
                for tipo_sala in tipos_sala:
                    tipo_sala_data.append(
                        {
                            "ID": tipo_sala.id,
                            "Nome": tipo_sala.nome,
                        }
                    )

                df = pd.DataFrame(tipo_sala_data)

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
                            help="Nome do tipo de sala (ex: Sala de Aula, Laboratório)",
                        ),
                    },
                    key="tipo_sala_table_editor",
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
                                tipo_sala_repo_delete = TipoSalaRepository(session)
                                for tipo_sala_id in deleted_ids:
                                    tipo_sala_repo_delete.delete(int(tipo_sala_id))
                            set_session_feedback(
                                "crud_result",
                                True,
                                f"{len(deleted_ids)} tipo(s) sala removido(s) com sucesso!",
                                action="delete",
                            )
                            changes_made = True
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao deletar tipo(s) sala: {str(e)}",
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
                                tipo_sala_repo_create = TipoSalaRepository(session)
                                for idx, row in new_rows.iterrows():
                                    nome = str(row["Nome"]).strip()

                                    if not nome:
                                        set_session_feedback(
                                            "crud_result",
                                            False,
                                            "Nome do tipo de sala é obrigatório",
                                            action="create",
                                        )
                                        errors_occurred = True
                                        continue

                                    # Check if already exists
                                    existing = tipo_sala_repo_create.get_all()
                                    existing_names = [
                                        ts.nome.lower() for ts in existing
                                    ]
                                    if nome.lower() in existing_names:
                                        set_session_feedback(
                                            "crud_result",
                                            False,
                                            f"Tipo de sala '{nome}' já existe no banco de dados",
                                            action="create",
                                        )
                                        errors_occurred = True
                                        continue

                                    tipo_sala_dto = TipoSalaCreate(nome=nome)
                                    tipo_sala_repo_create.create(tipo_sala_dto)
                                    created += 1

                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao criar tipo(s) sala: {str(e)}",
                                action="create",
                            )
                            errors_occurred = True

                        if created:
                            set_session_feedback(
                                "crud_result",
                                True,
                                f"{created} tipo(s) sala adicionado(s) com sucesso!",
                                action="create",
                            )
                            changes_made = True

                    if changes_made:
                        st.rerun()
                    # If only errors occurred, avoid rerun so the user can edit

                # Handle updates (rows with changes in existing records)
                else:
                    changes_made = False
                    errors_occurred = False

                    for idx, row in edited_df.iterrows():
                        if idx < len(df):
                            original_row = df.iloc[idx]
                            tipo_sala_id = int(row["ID"])

                            # Check if any field changed
                            nome_changed = row["Nome"] != original_row["Nome"]

                            if nome_changed:
                                nome = str(row["Nome"]).strip()

                                if not nome:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        "Nome do tipo de sala é obrigatório",
                                        action="update",
                                    )
                                    errors_occurred = True
                                    continue

                                try:
                                    with get_db_session() as session:
                                        tipo_sala_repo_update = TipoSalaRepository(
                                            session
                                        )
                                        # Get current tipo_sala
                                        current = tipo_sala_repo_update.get_by_id(
                                            tipo_sala_id
                                        )

                                        if current:
                                            # Check if new nome already exists (excluding current)
                                            if (
                                                nome_changed
                                                and nome != original_row["Nome"]
                                            ):
                                                existing_all = (
                                                    tipo_sala_repo_update.get_all()
                                                )
                                                existing_names = [
                                                    ts.nome.lower()
                                                    for ts in existing_all
                                                    if ts.id != tipo_sala_id
                                                ]
                                                if nome.lower() in existing_names:
                                                    set_session_feedback(
                                                        "crud_result",
                                                        False,
                                                        f"Tipo de sala '{nome}' já existe",
                                                        action="update",
                                                    )
                                                    errors_occurred = True
                                                    continue

                                            # Update fields
                                            tipo_sala_dto = TipoSalaCreate(nome=nome)
                                            tipo_sala_repo_update.update(
                                                tipo_sala_id, tipo_sala_dto
                                            )

                                            set_session_feedback(
                                                "crud_result",
                                                True,
                                                f"Tipo de sala {nome} atualizado com sucesso!",
                                                action="update",
                                            )
                                            changes_made = True
                                except Exception as e:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        f"Erro ao atualizar tipo de sala: {str(e)}",
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
                    "📭 Nenhum tipo de sala cadastrado ainda. Use a tabela acima para adicionar o primeiro tipo de sala."
                )

    except Exception as e:
        st.error(f"❌ Erro ao carregar tipos sala: {str(e)}")
