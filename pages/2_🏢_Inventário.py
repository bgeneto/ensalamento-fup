"""
Inventory Management Page - Room/Building/Campus CRUD

Comprehensive inventory management for physical space allocation infrastructure.
Includes CRUD operations for campuses, buildings, and rooms.

Route: /pages/2_🏢_Inventário.py
URL: ?page=Inventário
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
    authenticator.login(location="unrendered", key="authenticator-inventario")
except Exception as exc:
    st.error(f"❌ Erro de autenticação: {exc}")
    st.stop()

auth_status = st.session_state.get("authentication_status")

if auth_status:
    # Show logout button in sidebar
    authenticator.logout(location="sidebar", key="logout-inventario")
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
    page_title="Ensalamento - Inventário",
    page_icon="🏢",
    layout="wide",
)

# ============================================================================
# IMPORTS
# ============================================================================

from src.repositories.sala import SalaRepository
from src.repositories.campus import CampusRepository
from src.repositories.predio import PredioRepository
from src.repositories.tipo_sala import TipoSalaRepository
from src.repositories.caracteristica import CaracteristicaRepository
from src.schemas.academic import ProfessorCreate
from src.schemas.inventory import (
    CampusCreate,
    PredioCreate,
    TipoSalaCreate,
    CaracteristicaCreate,
    SalaRead,
)
from src.config.database import get_db_session
from src.utils.ui_feedback import (
    display_session_feedback,
    set_session_feedback,
)

# ============================================================================
# PAGE HEADER
# ============================================================================

st.title("🏢 Gerenciamento de Inventário")
st.markdown(
    "Gerencie campi, prédios, salas e características da infraestrutura física."
)

# ============================================================================
# TABS STRUCTURE
# ============================================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📍 Campi",
        "🏭 Prédios",
        "🚪 Salas",
        "🏷️ Características",
        "🧩 Assoc. Características",
    ]
)

# =============================================================================
# TAB 1: CAMPUS MANAGEMENT
# =============================================================================

with tab1:
    st.subheader("Gerenciamento de Campi")

    st.info(
        """
        Edite os dados diretamente na tabela abaixo.
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
                    # Detect additions or deletions
                    original_ids = set(df["ID"].astype(int))
                    edited_ids = set(
                        edited_df[edited_df["ID"].notna()]["ID"].astype(int)
                    )

                    # Handle deletions (rows removed from edited_df)
                    deleted_ids = original_ids - edited_ids
                    for campus_id in deleted_ids:
                        try:
                            with get_db_session() as session:
                                campus_repo_delete = CampusRepository(session)
                                campus_repo_delete.delete(int(campus_id))
                            set_session_feedback(
                                "crud_result",
                                True,
                                f"Campus ID {campus_id} removido com sucesso!",
                                action="delete",
                            )
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao deletar campus ID {campus_id}: {str(e)}",
                                action="delete",
                            )
                        st.rerun()

                    # Handle additions (new rows with NaN or 0 ID)
                    new_rows = edited_df[
                        (edited_df["ID"].isna()) | (edited_df["ID"] == 0)
                    ].copy()
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
                            st.rerun()

                        try:
                            with get_db_session() as session:
                                campus_repo_create = CampusRepository(session)
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
                                else:
                                    campus_dto = CampusCreate(
                                        nome=nome,
                                        descricao=descricao,
                                    )
                                    campus_repo_create.create(campus_dto)
                                    set_session_feedback(
                                        "crud_result",
                                        True,
                                        f"Campus {nome} adicionado com sucesso!",
                                        action="create",
                                    )
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao criar campus: {str(e)}",
                                action="create",
                            )
                        st.rerun()

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
                                                f"Campus {nome} atualizado com sucesso!",
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

# =============================================================================
# TAB 2: BUILDING MANAGEMENT
# =============================================================================

with tab2:
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
                    # Detect additions or deletions
                    original_ids = set(df["ID"].astype(int))
                    edited_ids = set(
                        edited_df[edited_df["ID"].notna()]["ID"].astype(int)
                    )

                    # Handle deletions (rows removed from edited_df)
                    deleted_ids = original_ids - edited_ids
                    for predio_id in deleted_ids:
                        try:
                            with get_db_session() as session:
                                predio_repo_delete = PredioRepository(session)
                                predio_repo_delete.delete(int(predio_id))
                            set_session_feedback(
                                "crud_result",
                                True,
                                f"Prédio ID {predio_id} removido com sucesso!",
                                action="delete",
                            )
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao deletar prédio ID {predio_id}: {str(e)}",
                                action="delete",
                            )
                        st.rerun()

                    # Handle additions (new rows with NaN or 0 ID)
                    new_rows = edited_df[
                        (edited_df["ID"].isna()) | (edited_df["ID"] == 0)
                    ].copy()
                    for idx, row in new_rows.iterrows():
                        nome = str(row["Nome"]).strip()
                        campus_id = row["Campus"]

                        if not nome:
                            set_session_feedback(
                                "crud_result",
                                False,
                                "Nome do prédio é obrigatório",
                                action="create",
                            )
                            st.rerun()

                        if not campus_id or pd.isna(campus_id):
                            set_session_feedback(
                                "crud_result",
                                False,
                                "Campus deve ser selecionado",
                                action="create",
                            )
                            st.rerun()

                        try:
                            with get_db_session() as session:
                                predio_repo_create = PredioRepository(session)
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
                                else:
                                    predio_dto = PredioCreate(
                                        nome=nome,
                                        campus_id=int(campus_id),
                                    )
                                    predio_repo_create.create(predio_dto)
                                    campus_name = campus_options.get(
                                        int(campus_id), "N/A"
                                    )
                                    set_session_feedback(
                                        "crud_result",
                                        True,
                                        f"Prédio {nome} adicionado com sucesso ao campus {campus_name}!",
                                        action="create",
                                    )
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao criar prédio: {str(e)}",
                                action="create",
                            )
                        st.rerun()

                # Handle updates (rows with changes in existing records)
                else:
                    for idx, row in edited_df.iterrows():
                        if idx < len(df):
                            original_row = df.iloc[idx]
                            predio_id = int(row["ID"])

                            # Check if any field changed
                            nome_changed = row["Nome"] != original_row["Nome"]
                            campus_changed = row["Campus"] != original_row["Campus"]

                            if nome_changed or campus_changed:
                                nome = str(row["Nome"]).strip()
                                campus_id = row["Campus"]

                                if not nome:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        "Nome do prédio é obrigatório",
                                        action="update",
                                    )
                                    st.rerun()

                                if not campus_id or pd.isna(campus_id):
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        "Campus deve ser selecionado",
                                        action="update",
                                    )
                                    st.rerun()

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
                                                    st.rerun()

                                            # Update fields
                                            predio_dto = PredioCreate(
                                                nome=nome,
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
                                                f"Prédio {nome} atualizado com sucesso (Campus: {campus_name})!",
                                                action="update",
                                            )
                                except Exception as e:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        f"Erro ao atualizar prédio: {str(e)}",
                                        action="update",
                                    )
                                st.rerun()

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

# =============================================================================
# TAB 3: ROOM MANAGEMENT (MAIN)
# =============================================================================

with tab3:
    st.subheader("Gerenciamento de Salas")

    st.info(
        """
        Edite os dados diretamente na tabela abaixo. Para salas, é necessário selecionar um prédio e tipo sala existentes.
        - Para **adicionar**, clique em ✚ no canto superior direito da tabela.
        - Para **remover**, selecione a linha correspondente clicando na primeira coluna e, em seguida, exclua a linha clicando no ícone 🗑️ no canto superior direito da tabela.
        - Para **alterar** um dado, dê um clique duplo na célula da tabela. As edições serão salvas automaticamente.
        """
    )

    # Room list with CRUD
    try:
        with get_db_session() as session:
            sala_repo = SalaRepository(session)
            predio_repo = PredioRepository(session)
            tipo_sala_repo = TipoSalaRepository(session)

            # Get rooms and related data for dropdowns
            salas = sala_repo.get_all()
            predios = predio_repo.get_all()
            tipos_sala = tipo_sala_repo.get_all()

            # Create dropdown options
            predio_options = {predio.id: predio.nome for predio in predios}
            tipo_sala_options = {ts.id: ts.nome for ts in tipos_sala}

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
                            "Prédio": sala.predio_id,
                            "Tipo Sala": sala.tipo_sala_id,
                            "Capacidade": sala.capacidade,
                            "Andar": sala.andar,  # Integer field
                            "Tipo Assento": sala.tipo_assento or "",
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
                    # Detect additions or deletions
                    original_ids = set(df["ID"].astype(int))
                    edited_ids = set(
                        edited_df[edited_df["ID"].notna()]["ID"].astype(int)
                    )

                    # Handle deletions (rows removed from edited_df)
                    deleted_ids = original_ids - edited_ids
                    for sala_id in deleted_ids:
                        try:
                            with get_db_session() as session:
                                sala_repo_delete = SalaRepository(session)
                                sala_repo_delete.delete(int(sala_id))
                            set_session_feedback(
                                "crud_result",
                                True,
                                f"Sala ID {sala_id} removida com sucesso!",
                                action="delete",
                            )
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao deletar sala ID {sala_id}: {str(e)}",
                                action="delete",
                            )
                        st.rerun()

                    # Handle additions (new rows with NaN or 0 ID)
                    new_rows = edited_df[
                        (edited_df["ID"].isna()) | (edited_df["ID"] == 0)
                    ].copy()
                    for idx, row in new_rows.iterrows():
                        nome = str(row["Nome"]).strip()
                        predio_id = row["Prédio"]
                        tipo_sala_id = row["Tipo Sala"]
                        capacidade = row["Capacidade"]
                        andar = row["Andar"]
                        tipo_assento = str(row["Tipo Assento"]).strip()

                        if not nome:
                            set_session_feedback(
                                "crud_result",
                                False,
                                "Nome da sala é obrigatório",
                                action="create",
                            )
                            st.rerun()

                        if not predio_id or pd.isna(predio_id):
                            set_session_feedback(
                                "crud_result",
                                False,
                                "Prédio deve ser selecionado",
                                action="create",
                            )
                            st.rerun()

                        if not tipo_sala_id or pd.isna(tipo_sala_id):
                            set_session_feedback(
                                "crud_result",
                                False,
                                "Tipo sala deve ser selecionado",
                                action="create",
                            )
                            st.rerun()

                        if not capacidade or pd.isna(capacidade) or capacidade < 1:
                            set_session_feedback(
                                "crud_result",
                                False,
                                "Capacidade deve ser um número maior que 0",
                                action="create",
                            )
                            st.rerun()

                        # Clean up optional fields
                        if pd.isna(andar) or andar == "":
                            andar = None
                        else:
                            andar = int(andar)

                        if not tipo_assento:
                            tipo_assento = None

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
                                        tipo_assento=tipo_assento,
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
                            tipo_assento_changed = (
                                row["Tipo Assento"] != original_row["Tipo Assento"]
                            )

                            if any(
                                [
                                    nome_changed,
                                    predio_changed,
                                    tipo_sala_changed,
                                    capacidade_changed,
                                    andar_changed,
                                    tipo_assento_changed,
                                ]
                            ):
                                nome = str(row["Nome"]).strip()
                                predio_id = row["Prédio"]
                                tipo_sala_id = row["Tipo Sala"]
                                capacidade = row["Capacidade"]
                                andar = row["Andar"]
                                tipo_assento = str(row["Tipo Assento"]).strip()

                                if not nome:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        "Nome da sala é obrigatório",
                                        action="update",
                                    )
                                    st.rerun()

                                if not predio_id or pd.isna(predio_id):
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        "Prédio deve ser selecionado",
                                        action="update",
                                    )
                                    st.rerun()

                                if not tipo_sala_id or pd.isna(tipo_sala_id):
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        "Tipo sala deve ser selecionado",
                                        action="update",
                                    )
                                    st.rerun()

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
                                    st.rerun()

                                # Clean up optional fields
                                if pd.isna(andar) or andar == "":
                                    andar = None
                                else:
                                    andar = int(andar)

                                if not tipo_assento:
                                    tipo_assento = None

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
                                                    st.rerun()

                                            # Update fields
                                            from src.schemas.inventory import SalaUpdate

                                            sala_update_dto = SalaUpdate(
                                                nome=nome,
                                                predio_id=int(predio_id),
                                                tipo_sala_id=int(tipo_sala_id),
                                                capacidade=int(capacidade),
                                                andar=andar,
                                                tipo_assento=tipo_assento,
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
                                except Exception as e:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        f"Erro ao atualizar sala: {str(e)}",
                                        action="update",
                                    )
                                st.rerun()

                # Display CRUD result if available
                display_session_feedback("crud_result")

            else:
                st.info(
                    "📭 Nenhuma sala cadastrada ainda. Use a tabela acima para adicionar a primeira sala."
                )
                if not predios:
                    st.warning(
                        "ℹ️ Primeiro, cadastre ao menos um prédio na aba 'Prédios' para poder criar salas."
                    )
                if not tipos_sala:
                    st.warning(
                        "ℹ️ Primeiro, cadastre ao menos um tipo sala na aba 'Características' para poder criar salas."
                    )

    except Exception as e:
        st.error(f"❌ Erro ao carregar salas: {str(e)}")

# =============================================================================
# TAB 4: ROOM CHARACTERISTICS
# =============================================================================

with tab4:
    st.subheader("Gerenciamento de Características de Salas")

    st.info(
        """
        Edite os dados diretamente na tabela abaixo.
        - Para **adicionar**, clique em ✚ no canto superior direito da tabela.
        - Para **remover**, selecione a linha correspondente clicando na primeira coluna e, em seguida, exclua a linha clicando no ícone 🗑️ no canto superior direito da tabela.
        - Para **alterar** um dado, dê um clique duplo na célula da tabela. As edições serão salvas automaticamente.
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
                    # Detect additions or deletions
                    original_ids = set(df["ID"].astype(int))
                    edited_ids = set(
                        edited_df[edited_df["ID"].notna()]["ID"].astype(int)
                    )

                    # Handle deletions (rows removed from edited_df)
                    deleted_ids = original_ids - edited_ids
                    for caracteristica_id in deleted_ids:
                        try:
                            with get_db_session() as session:
                                caracteristica_repo_delete = CaracteristicaRepository(
                                    session
                                )
                                caracteristica_repo_delete.delete(
                                    int(caracteristica_id)
                                )
                            set_session_feedback(
                                "crud_result",
                                True,
                                f"Característica ID {caracteristica_id} removida com sucesso!",
                                action="delete",
                            )
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao deletar característica ID {caracteristica_id}: {str(e)}",
                                action="delete",
                            )
                        st.rerun()

                    # Handle additions (new rows with NaN or 0 ID)
                    new_rows = edited_df[
                        (edited_df["ID"].isna()) | (edited_df["ID"] == 0)
                    ].copy()
                    for idx, row in new_rows.iterrows():
                        nome = str(row["Nome"]).strip()

                        if not nome:
                            set_session_feedback(
                                "crud_result",
                                False,
                                "Nome da característica é obrigatório",
                                action="create",
                            )
                            st.rerun()

                        try:
                            with get_db_session() as session:
                                caracteristica_repo_create = CaracteristicaRepository(
                                    session
                                )
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
                                else:
                                    caracteristica_dto = CaracteristicaCreate(nome=nome)
                                    caracteristica_repo_create.create(
                                        caracteristica_dto
                                    )
                                    set_session_feedback(
                                        "crud_result",
                                        True,
                                        f"Característica {nome} adicionada com sucesso!",
                                        action="create",
                                    )
                        except Exception as e:
                            set_session_feedback(
                                "crud_result",
                                False,
                                f"Erro ao criar característica: {str(e)}",
                                action="create",
                            )
                        st.rerun()

                # Handle updates (rows with changes in existing records)
                else:
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
                                    st.rerun()

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
                                                    st.rerun()

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
                                except Exception as e:
                                    set_session_feedback(
                                        "crud_result",
                                        False,
                                        f"Erro ao atualizar característica: {str(e)}",
                                        action="update",
                                    )
                                st.rerun()

                # Display CRUD result if available
                display_session_feedback("crud_result")

            else:
                st.info(
                    "📭 Nenhuma característica cadastrada ainda. Use a tabela acima para adicionar a primeira característica."
                )

    except Exception as e:
        st.error(f"❌ Erro ao carregar características: {str(e)}")

# =============================================================================
# TAB 5: ROOM CHARACTERISTICS ASSOCIATIONS
# =============================================================================

with tab5:
    st.subheader("Associação de Características com Salas")

    st.info(
        """
        Gerencie a associação entre salas e características.
        - Use o **seletor** abaixo para escolher uma sala ou característica.
        - Clique em **Adicionar Características** ou **Remover Características** para fazer alterações.
        - Visualize o estado atual das associações na tabela abaixo.
        """
    )

    # Room-characteristics associations management
    try:
        with get_db_session() as session:
            sala_repo = SalaRepository(session)
            caracteristica_repo = CaracteristicaRepository(session)

            # Get all rooms and characteristics
            salas = sala_repo.get_all()
            caracteristicas = caracteristica_repo.get_all()

            if not salas or not caracteristicas:
                st.warning(
                    "📭 Você precisa ter ao menos uma sala e uma característica cadastradas para fazer associações."
                )
                if not salas:
                    st.info("Acesse a aba 'Salas' para cadastrar salas.")
                if not caracteristicas:
                    st.info(
                        "Acesse a aba 'Características' para cadastrar características."
                    )
            else:
                # Create dropdown options
                sala_options = {s.id: s.nome for s in salas}
                caracteristica_options = {c.id: c.nome for c in caracteristicas}

                # Room selector spanning full width
                selected_sala_id = st.selectbox(
                    "Selecione uma sala:",
                    options=list(sala_options.keys()),
                    format_func=lambda x: sala_options.get(x, "N/A"),
                    key="sala_selector_associations",
                )

                # Get current characteristics for selected room
                if selected_sala_id:
                    sala_data = sala_repo.get_sala_with_caracteristicas(
                        selected_sala_id
                    )
                    if sala_data:
                        current_caracteristica_ids = [
                            c.id for c in sala_data["caracteristicas"]
                        ]

                        col1, col2 = st.columns([1, 1])

                        with col1:
                            # Multi-select for characteristics
                            selected_caracteristica_ids = st.multiselect(
                                f"Características para {sala_data['sala'].nome}:",
                                options=list(caracteristica_options.keys()),
                                format_func=lambda x: caracteristica_options.get(
                                    x, "N/A"
                                ),
                                default=current_caracteristica_ids,
                                key=f"caracteristica_multiselect_{selected_sala_id}",
                            )

                        with col2:
                            # Display current characteristics status
                            if sala_data["caracteristicas"]:
                                current_names = [
                                    c.nome for c in sala_data["caracteristicas"]
                                ]
                                st.markdown(
                                    f"**Características atuais:** {', '.join(current_names)}"
                                )
                            else:
                                st.info(
                                    "Esta sala não possui características associadas."
                                )

                        # Action buttons below columns (full width)
                        st.markdown("---")
                        col_btn1, col_btn2, col_spacer = st.columns([1, 1, 2])

                        with col_btn1:
                            if st.button(
                                "💾 Atualizar",
                                key=f"update_{selected_sala_id}",
                                help="Salva as alterações das características",
                                use_container_width=True,
                            ):
                                try:
                                    success = sala_repo.set_caracteristicas_for_sala(
                                        selected_sala_id,
                                        selected_caracteristica_ids,
                                    )

                                    if success:
                                        st.success(
                                            f"✅ Características da sala '{sala_data['sala'].nome}' atualizadas com sucesso!"
                                        )
                                        st.rerun()  # Refresh to show changes immediately
                                    else:
                                        st.error(
                                            "❌ Falha ao atualizar características da sala."
                                        )

                                except Exception as e:
                                    st.error(f"❌ Erro ao atualizar: {str(e)}")

                        with col_btn2:
                            if st.button(
                                "🗑️ Limpar Tudo",
                                key=f"clear_{selected_sala_id}",
                                help="Remove todas as características da sala",
                                use_container_width=True,
                            ):
                                try:
                                    success = sala_repo.set_caracteristicas_for_sala(
                                        selected_sala_id, []
                                    )

                                    if success:
                                        st.success(
                                            f"✅ Todas as características removidas da sala '{sala_data['sala'].nome}'!"
                                        )
                                        st.rerun()
                                    else:
                                        st.error("❌ Falha ao remover características.")

                                except Exception as e:
                                    st.error(f"❌ Erro ao limpar: {str(e)}")

                        with col_spacer:
                            st.empty()

                # Display comprehensive associations table
                st.divider()
                st.subheader("Visão Geral das Associações")

                # Build table data
                associations_data = []
                for sala in salas:
                    sala_with_carac = sala_repo.get_sala_with_caracteristicas(sala.id)
                    if sala_with_carac:
                        caracteristica_names = [
                            c.nome for c in sala_with_carac["caracteristicas"]
                        ]

                        associations_data.append(
                            {
                                "Sala": sala_with_carac["sala"].nome,
                                "Prédio": sala_with_carac[
                                    "sala"
                                ].predio_id,  # We'll resolve this later
                                "Capacidade": sala_with_carac["sala"].capacidade,
                                "Características": (
                                    "; ".join(caracteristica_names)
                                    if caracteristica_names
                                    else "Nenhuma"
                                ),
                                "Total Características": len(caracteristica_names),
                            }
                        )

                if associations_data:
                    associations_df = pd.DataFrame(associations_data)
                    st.dataframe(
                        associations_df,
                        column_config={
                            "Sala": st.column_config.TextColumn("Sala", width="medium"),
                            "Prédio": st.column_config.TextColumn(
                                "Prédio", width="medium"
                            ),
                            "Capacidade": st.column_config.NumberColumn(
                                "Capacidade", width="small"
                            ),
                            "Características": st.column_config.TextColumn(
                                "Características", width="large"
                            ),
                            "Total Características": st.column_config.NumberColumn(
                                "Total", width="small"
                            ),
                        },
                        hide_index=True,
                    )

                    # Summary stats
                    total_associations = sum(
                        len(row.split("; ")) if row != "Nenhuma" else 0
                        for row in associations_df["Características"]
                    )
                    avg_carac_per_room = (
                        total_associations / len(associations_df)
                        if associations_df.shape[0] > 0
                        else 0
                    )

                    col_stats1, col_stats2, col_stats3 = st.columns(3)
                    with col_stats1:
                        st.metric("Total de Associações", total_associations)
                    with col_stats2:
                        st.metric("Média por Sala", f"{avg_carac_per_room:.1f}")
                    with col_stats3:
                        st.metric(
                            "Salas sem Características",
                            sum(
                                1
                                for row in associations_df["Características"]
                                if row == "Nenhuma"
                            ),
                        )
                else:
                    st.info("Nenhuma sala encontrada para exibir associações.")

    except Exception as e:
        st.error(f"❌ Erro ao carregar associações: {str(e)}")
