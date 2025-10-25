"""
Visualização da Demanda Semestral

Página para que o administrador inspecione as demandas importadas do
Sistema de Oferta: seleção de semestre, métricas de resumo, avisos
acionáveis (professores não cadastrados) e tabela filtrável com colunas
amigáveis geradas pelo parser Sigaa.

Route: pages/5_👁️_Demanda.py
URL: /Demanda
"""

import streamlit as st
from typing import List
import pandas as pd
from pages.components.auth import initialize_page

# Initialize page with authentication and configuration
if not initialize_page(
    page_title="Demanda - Ensalamento",
    page_icon="👁️",
    layout="wide",
    key_suffix="demanda",
):
    st.stop()

# ============================================================================
# IMPORTS
# ============================================================================

from src.config.database import get_db_session
from src.repositories.semestre import SemestreRepository
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.professor import ProfessorRepository
from src.utils.cache_helpers import get_sigaa_parser, get_semester_options
from src.utils.ui_feedback import set_session_feedback, display_session_feedback
from src.services.semester_service import sync_semester_from_api
from pages.components.ui import page_footer

st.title("👁️ Demanda Semestral")

st.info(
    """
    ℹ️ INFORMAÇÃO

    - Esta página permite importar, visualizar, editar e remover as demandas de disciplinas de um determinado semestre.
    - A importação de demandas é realizada por meio da integração com Sistema de Oferta FUP/UnB.
    - Para importar, basta selecionar o semestre desejado e clicar em "🔄 Sincronizar Demanda" para buscar os dados mais recentes do sistema de oferta.
    - A importação é uma etapa necessária antes de realizar o ensalamento, garantindo que as demandas sejam atendidas.
    """,
)

# Display any persisted feedback from prior action
display_session_feedback("sync_semestre_result")


def _demanda_dtos_to_df(dtos: List) -> pd.DataFrame:
    """Converte uma lista de DemandaRead DTOs para um DataFrame com colunas amigáveis."""
    parser = get_sigaa_parser()
    rows = []
    for d in dtos:
        # Support Pydantic models or plain dicts
        if hasattr(d, "model_dump"):
            data = d.model_dump()
        elif hasattr(d, "__dict__"):
            data = getattr(d, "__dict__")
        else:
            data = dict(d)

        horario_raw = data.get("horario_sigaa_bruto") or ""
        horario_legivel = parser.parse_to_human_readable(horario_raw)
        num_slots = len(parser.split_to_atomic_array(horario_raw))

        rows.append(
            {
                "id": data.get("id"),
                "codigo_disciplina": data.get("codigo_disciplina"),
                "nome_disciplina": data.get("nome_disciplina"),
                "turma_disciplina": data.get("turma_disciplina"),
                "vagas_disciplina": data.get("vagas_disciplina"),
                "professores_disciplina": data.get("professores_disciplina") or "",
                "horario_sigaa_bruto": horario_raw,
                "horario_legivel": horario_legivel,
                "num_slots": num_slots,
                "id_oferta_externo": data.get("id_oferta_externo"),
                "codigo_curso": data.get("codigo_curso"),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        # ensure columns exist
        df = pd.DataFrame(
            columns=[
                "id",
                "codigo_disciplina",
                "nome_disciplina",
                "turma_disciplina",
                "vagas_disciplina",
                "professores_disciplina",
                "horario_sigaa_bruto",
                "horario_legivel",
                "num_slots",
                "id_oferta_externo",
                "codigo_curso",
            ]
        )

    return df


# Validate current global semester exists - semester_badge component handles initialization
semester_options = get_semester_options()
if not semester_options:
    st.info(
        "Nenhum semestre encontrado. Importe um semestre na página de sincronização."
    )
    st.stop()

semester_options_dict = {sem_id: sem_name for sem_id, sem_name in semester_options}
current_semester_id = st.session_state.get("global_semester_id")

# Fallback to most recent if current semester is invalid (shouldn't happen due to badge initialization)
if current_semester_id not in semester_options_dict:
    current_semester_id = semester_options[0][0]
    st.session_state.global_semester_id = current_semester_id

# Display readonly semester selector with help text
st.selectbox(
    "📅 Semestre (Global):",
    options=[current_semester_id],
    format_func=lambda x: semester_options_dict.get(x, f"Semestre {x}"),
    disabled=True,
    help="Para alterar o semestre, acesse a página Painel",
    key="readonly_semester_display_demanda",
    width=400,
)

selected_semester_id = current_semester_id

# Allow ignoring some courses by default
# Get list of unique course codes from demandas table or use predefined list if empty
with get_db_session() as session:
    dem_repo = DisciplinaRepository(session)
    cursos_from_db = dem_repo.get_unique_course_codes()

# Use course codes from DB or fallback to predefined list if DB is empty
if cursos_from_db:
    options_cursos = cursos_from_db
else:
    options_cursos = [
        "PPGCIMA",
        "PPGCA-M",
        "PPGCA-D",
        "CND",
        "CNN",
        "LEDOC",
        "PPGEC",
        "GAM",
        "GEAGRO",
        "PROFAGUA",
        "PPGP",
        "PPG-MADER",
        "OUTROS",
    ]

# Determine default ignored courses (LEDOC if available)
default_ignored = [c for c in ("LEDOC", "OUTROS") if c in options_cursos]

cursos_ignorados = st.multiselect(
    "Cursos Ignorados:",
    options=options_cursos,
    default=default_ignored,  # LEDOC by default is ignored (if available)
    width=400,
)

with get_db_session() as session:
    dem_repo = DisciplinaRepository(session)
    prof_repo = ProfessorRepository(session)

    demandas = dem_repo.get_by_semestre(selected_semester_id)
    df = _demanda_dtos_to_df(demandas)

    # --- Métricas de Resumo ---
    total_demandas = len(df)

    # Collect unique professor names from imported demandas
    profs_from_dem = set()
    for val in df["professores_disciplina"].fillna(""):
        for name in [x.strip() for x in val.split(",") if x.strip()]:
            profs_from_dem.add(name)

    total_professores = len(profs_from_dem)

    # total atomic slots
    total_slots_atomicos = int(df["num_slots"].sum()) if not df.empty else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Demandas", f"{total_demandas}")
    col2.metric("Professores Envolvidos", f"{total_professores}")
    col3.metric("Slots de Horários", f"{total_slots_atomicos}")

    # --- Avisos Acionáveis: Professores não cadastrados ---
    registered_profs = {p.nome_completo for p in prof_repo.get_all()}
    missing_profs = sorted(
        [p for p in profs_from_dem if p and p not in registered_profs]
    )

    if missing_profs:
        st.warning("⚠️ Professores Não Cadastrados Encontrados!")
        st.markdown(
            """
            Os seguintes professores foram importados da API, mas **não existem** na
            base de dados de Professores do sistema.

            **Isso é crítico:** As restrições (ex: baixa mobilidade) e preferências
            **NÃO** serão aplicadas para eles.
            """
        )

        with st.expander(f"Ver os {len(missing_profs)} professores não cadastrados"):
            st.dataframe(
                pd.DataFrame({"nome_completo": missing_profs}), width="stretch"
            )

        st.info(
            "Acesse a página 'Professores' e importe ou cadastre os nomes antes de alocar."
        )

    # --- Filtros e Tabela de Demandas ---
    st.subheader("🔍 Filtrar Demanda")

    filtro_disciplina = st.text_input("Buscar por Nome ou Código da Disciplina")

    # Collect unique course codes for filter (excluding ignored courses)
    df_para_filtros = df.copy()
    if cursos_ignorados:
        df_para_filtros = df_para_filtros[
            ~df_para_filtros["codigo_curso"].isin(cursos_ignorados)
        ]
    cursos_unicos = sorted(df_para_filtros["codigo_curso"].fillna("").unique())
    cursos_unicos = [c for c in cursos_unicos if c.strip()]  # Remove empty entries
    filtro_curso = st.multiselect("Filtrar por Curso", options=cursos_unicos)

    lista_professores = sorted(list(profs_from_dem))
    filtro_professor = st.multiselect(
        "Filtrar por Professor", options=lista_professores
    )

    # Apply all filters step by step
    df_filtrado = df.copy()

    # 1. Filter ignored courses first (this one affects what gets saved, others are just display filters)
    if cursos_ignorados:
        df_filtrado = df_filtrado[~df_filtrado["codigo_curso"].isin(cursos_ignorados)]

    # 2. Apply display filters
    if filtro_disciplina:
        term = filtro_disciplina.lower()
        df_filtrado = df_filtrado[
            df_filtrado["codigo_disciplina"].str.lower().str.contains(term, na=False)
            | df_filtrado["nome_disciplina"].str.lower().str.contains(term, na=False)
        ]

    if filtro_curso:
        # Filter by selected course codes
        df_filtrado = df_filtrado[df_filtrado["codigo_curso"].isin(filtro_curso)]

    if filtro_professor:
        # keep rows where any of the selected professor names appear in the professores_disciplina cell
        mask = df_filtrado["professores_disciplina"].apply(
            lambda cell: any(
                p in [x.strip() for x in str(cell).split(",") if x.strip()]
                for p in filtro_professor
            )
        )
        df_filtrado = df_filtrado[mask]

    # Editable table instructions
    st.info(
        """
        Edite os dados diretamente na tabela abaixo.
        - Para **remover**, selecione a linha correspondente clicando na primeira coluna e, em seguida, exclua a linha clicando no ícone 🗑️ no canto superior direito da tabela.
        - Para **alterar** um dado, dê um clique duplo na célula da tabela. As edições serão salvas automaticamente.
        - Não é possível **adicionar** demandas diretamente por aqui. Nem todos os dados são editáveis.
        """
    )

    # Show total demandes found after ALL filters are applied
    st.markdown(
        f"**Total de demandas encontradas: {len(df_filtrado)}**"
    )  # DON'T use metric here, this is the layout in other pages!

    # Display editable table if there are demandes
    if df_filtrado.empty:
        st.warning(
            "Nenhuma demanda encontrada para o semestre/filtragem selecionada. Use outro semestre ou sincronize os dados novamente clicando no botão abaixo.",
            icon="⚠️",
        )
        # Clear any cached editor state when empty by using a different key
        # This forces Streamlit to create a fresh empty editor on next data load
        if f"demanda_table_editor_empty_{selected_semester_id}" not in st.session_state:
            st.session_state[f"demanda_table_editor_empty_{selected_semester_id}"] = (
                True
            )
    else:
        # Prepare data for editing
        edit_data = []
        for idx, row in df_filtrado.iterrows():
            edit_data.append(
                {
                    "ID": row["id"],  # Keep internal ID for updates
                    "Curso": row["codigo_curso"],
                    "Código": row["codigo_disciplina"],
                    "Disciplina": row["nome_disciplina"],
                    "Turma": row["turma_disciplina"],
                    "Vagas": row["vagas_disciplina"],
                    "Professores": row["professores_disciplina"],
                    "Horário": row["horario_legivel"],
                    "Slots": row["num_slots"],
                }
            )

        edit_df = pd.DataFrame(edit_data)

        # Handle widget state management for cache issues
        # Detect when data has been emptied and force widget recreation
        current_data_size = len(edit_df)
        prev_data_size_key = f"demanda_prev_data_size_{selected_semester_id}"

        # Check if data was emptied (previous size was > 0 and now is 0)
        force_recreation = False
        if prev_data_size_key in st.session_state:
            prev_size = st.session_state[prev_data_size_key]
            if prev_size > 0 and current_data_size == 0:
                force_recreation = True
                # Clean up old widget state if it exists
                editor_keys_to_clean = [
                    k
                    for k in st.session_state.keys()
                    if k.startswith("demanda_table_editor")
                ]
                for key in editor_keys_to_clean:
                    del st.session_state[key]

        # Update stored data size
        st.session_state[prev_data_size_key] = current_data_size

        # Use different key when forcing recreation due to emptied data
        editor_key = (
            "demanda_table_editor_fresh" if force_recreation else "demanda_table_editor"
        )

        # Create edited_df with data_editor
        edited_df = st.data_editor(
            edit_df,
            width="stretch",
            hide_index=True,
            num_rows="dynamic",  # Allow deletions for imported data
            column_config={
                "ID": None,  # Hide ID column
                "Curso": st.column_config.TextColumn(
                    "Curso",
                    required=True,
                    help="Código do curso (ex: ENM, ENGENHARIA MECÂNICA)",
                ),
                "Código": st.column_config.TextColumn(
                    "Código",
                    required=True,
                    help="Código da disciplina (ex: ENM0011)",
                ),
                "Disciplina": st.column_config.TextColumn(
                    "Disciplina",
                    required=True,
                    help="Nome da disciplina",
                ),
                "Turma": st.column_config.TextColumn(
                    "Turma",
                    required=True,
                    help="Código da turma (ex: A, B)",
                ),
                "Vagas": st.column_config.NumberColumn(
                    "Vagas",
                    min_value=1,
                    help="Número de vagas disponíveis",
                ),
                "Professores": st.column_config.TextColumn(
                    "Professores",
                    help="Lista de professores separados por vírgula",
                ),
                "Horário": st.column_config.TextColumn(
                    "Horário",
                    disabled=True,  # Read-only, calculated from raw schedule
                    help="Horário legível (calculado automaticamente)",
                ),
                "Slots": st.column_config.NumberColumn(
                    "Slots",
                    disabled=True,  # Read-only, calculated from raw schedule
                    help="Número de slots de horário",
                ),
            },
            key=editor_key,
        )

        # Detect and process changes
        changes_made = False
        errors_occurred = False

        # Detect additions or deletions
        original_ids = set(edit_df["ID"].astype(int))
        edited_ids = set(edited_df[edited_df["ID"].notna()]["ID"].astype(int))

        # Handle deletions (rows removed from edited_df)
        deleted_ids = original_ids - edited_ids
        if deleted_ids:
            try:
                with get_db_session() as session:
                    demanda_repo_delete = DisciplinaRepository(session)
                    deleted_list = []
                    for demanda_id in deleted_ids:
                        demanda = demanda_repo_delete.get_by_id(int(demanda_id))
                        if demanda:
                            deleted_list.append(
                                f"{demanda.codigo_disciplina}-{demanda.turma_disciplina}"
                            )
                        demanda_repo_delete.delete(int(demanda_id))
                    set_session_feedback(
                        "demanda_crud_result",
                        True,
                        f"{len(deleted_ids)} demanda(s) removida(s) com sucesso: {', '.join(deleted_list)}",
                        action="delete",
                    )
                    changes_made = True
            except Exception as e:
                set_session_feedback(
                    "demanda_crud_result",
                    False,
                    f"Erro ao deletar demanda(s): {str(e)}",
                    action="delete",
                )
                errors_occurred = True

        # Compare each row for changes (only for rows that still exist)
        for idx, row in edited_df.iterrows():
            if idx < len(edit_df):
                original_row = edit_df.iloc[idx]

                # Check which fields changed
                curso_changed = row["Curso"] != original_row["Curso"]
                codigo_changed = row["Código"] != original_row["Código"]
                disciplina_changed = row["Disciplina"] != original_row["Disciplina"]
                turma_changed = row["Turma"] != original_row["Turma"]
                vagas_changed = row["Vagas"] != original_row["Vagas"]
                professores_changed = row["Professores"] != original_row["Professores"]

                # If any field changed, validate and update
                if any(
                    [
                        curso_changed,
                        codigo_changed,
                        disciplina_changed,
                        turma_changed,
                        vagas_changed,
                        professores_changed,
                    ]
                ):

                    demanda_id = int(row["ID"])

                    # Validate required fields
                    curso = str(row["Curso"]).strip()
                    codigo = str(row["Código"]).strip()
                    disciplina = str(row["Disciplina"]).strip()
                    turma = str(row["Turma"]).strip()
                    vagas = row["Vagas"]
                    professores = str(row["Professores"]).strip()

                    validation_errors = []

                    if not curso:
                        validation_errors.append("Curso é obrigatório")
                    if not codigo:
                        validation_errors.append("Código da disciplina é obrigatório")
                    if not disciplina:
                        validation_errors.append("Nome da disciplina é obrigatório")
                    if not turma:
                        validation_errors.append("Turma é obrigatória")

                    if pd.isna(vagas) or vagas < 1:
                        validation_errors.append("Vagas deve ser um número maior que 0")
                    else:
                        vagas = int(vagas)

                    if validation_errors:
                        for error in validation_errors:
                            set_session_feedback(
                                "demanda_crud_result",
                                False,
                                f"Erro na demanda {codigo}-{turma}: {error}",
                                action="update",
                            )
                        errors_occurred = True
                        continue

                    # Attempt update
                    try:
                        with get_db_session() as session:
                            demanda_repo_update = DisciplinaRepository(session)
                            current = demanda_repo_update.get_by_id(demanda_id)

                            if current:
                                # Create update DTO with changed fields
                                update_data = {}
                                if curso_changed:
                                    update_data["codigo_curso"] = curso
                                if codigo_changed:
                                    update_data["codigo_disciplina"] = codigo
                                if disciplina_changed:
                                    update_data["nome_disciplina"] = disciplina
                                if turma_changed:
                                    update_data["turma_disciplina"] = turma
                                if vagas_changed:
                                    update_data["vagas_disciplina"] = vagas
                                if professores_changed:
                                    update_data["professores_disciplina"] = professores

                                from src.schemas.academic import DemandaUpdate

                                demanda_update_dto = DemandaUpdate(**update_data)

                                demanda_repo_update.update(
                                    demanda_id, demanda_update_dto
                                )

                                set_session_feedback(
                                    "demanda_crud_result",
                                    True,
                                    f"Demanda {codigo}-{turma} atualizada com sucesso!",
                                    action="update",
                                )
                                changes_made = True
                            else:
                                set_session_feedback(
                                    "demanda_crud_result",
                                    False,
                                    f"Demanda ID {demanda_id} não encontrada",
                                    action="update",
                                )
                                errors_occurred = True

                    except Exception as e:
                        set_session_feedback(
                            "demanda_crud_result",
                            False,
                            f"Erro ao atualizar demanda {codigo}-{turma}: {str(e)}",
                            action="update",
                        )
                        errors_occurred = True

        # Rerun only if changes were successful, avoid rerun if only errors occurred
        if changes_made:
            st.rerun()
        # If only errors occurred, don't rerun so user can fix values

        # Display CRUD feedback
        display_session_feedback("demanda_crud_result")

# Track sync processing state in session state
if "sync_semestre_processing" not in st.session_state:
    st.session_state.sync_semestre_processing = False

# Get current semester name for sync operations
current_semester_name = semester_options_dict.get(
    current_semester_id, f"Semestre {current_semester_id}"
)

# Show spinner if processing is active from a previous rerun
if st.session_state.sync_semestre_processing:
    with st.spinner(
        "🔄 Sincronizando dados da API... Isso pode levar alguns segundos."
    ):
        # Complete the sync operation
        try:
            summary = sync_semester_from_api(current_semester_name, cursos_ignorados)
            # success
            set_session_feedback(
                "sync_semestre_result",
                True,
                f"Sincronização concluída: {summary['demandas']} demandas importadas, {summary['professores']} professores criados.",
                ttl=8,
                summary=summary,
            )
        except Exception as e:
            # store error feedback
            set_session_feedback(
                "sync_semestre_result",
                False,
                f"❌ Erro na sincronização: {type(e).__name__}: {e}",
                ttl=12,
            )

        # Reset processing state
        st.session_state.sync_semestre_processing = False

        # Rerun to refresh the page and show results
        st.rerun()

# Check semester status before allowing sync
semestre_status_active = False
with get_db_session() as session:
    semestre_repo = SemestreRepository(session)
    semestre = semestre_repo.get_by_name(current_semester_name)
    if semestre:
        semestre_status_active = semestre.status

# Sync button (disabled during processing)
if st.button(
    f"🔄 Sincronizar Demanda {current_semester_name}",
    help="Importar demanda por salas do Sistema de Oferta",
    disabled=st.session_state.sync_semestre_processing,
):
    # Check if selected semester is active
    if not semestre_status_active:
        set_session_feedback(
            "sync_semestre_result",
            False,
            "Sincronização disponível apenas para semestres ativos. Selecione um semestre ativo para importar a demanda.",
            ttl=6,
        )
        st.rerun()
    else:
        # Set processing state and rerun to start spinner
        st.session_state.sync_semestre_processing = True
        st.rerun()

st.markdown("---")

# TODO: Create a form to add new demandas manually with all fields required (like those in the above data editor )


# Page Footer
page_footer.show()
