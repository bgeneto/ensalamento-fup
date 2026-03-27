"""
Visualização da Demanda Semestral

Página para que o administrador inspecione as demandas importadas do
Sistema de Oferta: seleção de semestre, métricas de resumo, avisos
acionáveis (professores não cadastrados) e tabela filtrável com colunas
amigáveis geradas pelo parser Sigaa.
"""

from typing import List

import pandas as pd
import streamlit as st

from pages.components.auth import initialize_page

# Initialize page with authentication and configuration
if not initialize_page(
    page_title="Demanda - Ensalamento",
    page_icon="🧭",
    layout="wide",
    key_suffix="demanda",
):
    st.stop()

# ============================================================================
# IMPORTS
# ============================================================================

from pages.components.ui import page_footer
from src.config.database import get_db_session
from src.repositories.alocacao import AlocacaoRepository
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.professor import ProfessorRepository
from src.repositories.semestre import SemestreRepository
from src.services.demanda_sync_service import DemandaSyncService
from src.services.semester_service import sync_semester_from_api
from src.utils.cache_helpers import (
    get_semester_options,
    get_sigaa_discrepancy_service,
    get_sigaa_parser,
)
from src.utils.demanda_ui import (
    build_course_ignore_options,
    default_ignored_courses,
    sanitize_ignored_courses,
)
from src.utils.ui_feedback import display_session_feedback, set_session_feedback

st.title("🧭 Demanda Semestral")

st.info(
    """
    ℹ️ Use esta página para visualizar, importar, editar, remover ou adicionar demandas de oferta de disciplinas.
    - A importação de demandas é realizada por meio da integração com Sistema de Oferta FUP/UnB.
    - Antes de importar, você pode **ignorar** cursos específicos que não devem ser considerados na alocação de salas.
    - `LEDOC` e `OUTROS` vêm pré-selecionados para ignorar por padrão, mas você pode desmarcá-los a qualquer momento.
    - Para importar, basta garantir que o semestre correto esteja pré-selecionado e então clicar em **🔄 Sincronizar Demanda**.
    - Só é possível importar demandas para semestres que estejam ativos (veja página **⚙️ Configurações**).
    - A importação é uma etapa necessária **antes** de realizar o ensalamento, garantindo que as demandas sejam atendidas.
    """,
)

# Display any persisted feedback from prior action
display_session_feedback("sync_semestre_result")
display_session_feedback("sigaa_compare_result")


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
                "origem": data.get("origem") or "manual",
                "sync_status": data.get("sync_status") or "manual",
                "tem_override": "Sim"
                if (data.get("local_overrides_json") or {})
                else "",
                "revalidation_required": "Sim"
                if data.get("revalidation_required")
                else "",
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
                "origem",
                "sync_status",
                "tem_override",
                "revalidation_required",
            ]
        )

    return df


def _sigaa_compare_cache_key(semester_id: int) -> str:
    return f"sigaa_compare_result_{semester_id}"


def _clear_sigaa_compare_cache(semester_id: int) -> None:
    st.session_state.pop(_sigaa_compare_cache_key(semester_id), None)


def _comparison_table_df(records: list[dict]) -> pd.DataFrame:
    """Build a display DataFrame hiding columns intentionally omitted from the UI."""
    df_result = pd.DataFrame(records)
    return df_result.drop(
        columns=[
            "Demanda IDs",
            "Similaridade Professores",
            "Somente no Sistema",
            "Somente no SIGAA",
            "Subofertas Locais",
        ],
        errors="ignore",
    )


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
    help="Para alterar o semestre, use o menu lateral.",
    key="readonly_semester_display_demanda",
    width=400,
)

selected_semester_id = current_semester_id
current_semester_name = semester_options_dict.get(
    current_semester_id, f"Semestre {current_semester_id}"
)
compare_cache_key = _sigaa_compare_cache_key(selected_semester_id)

semestre_status_active = False
with get_db_session() as session:
    semestre_repo = SemestreRepository(session)
    semestre = semestre_repo.get_by_name(current_semester_name)
    if semestre:
        semestre_status_active = semestre.status

# Build a stable ignore-courses selector using DB codes plus known fallbacks
with get_db_session() as session:
    dem_repo = DisciplinaRepository(session)
    cursos_from_db = dem_repo.get_unique_course_codes()

options_cursos = build_course_ignore_options(cursos_from_db)
ignored_courses_key = f"demanda_cursos_ignorados_{selected_semester_id}"
if ignored_courses_key not in st.session_state:
    st.session_state[ignored_courses_key] = default_ignored_courses(options_cursos)
else:
    st.session_state[ignored_courses_key] = sanitize_ignored_courses(
        st.session_state.get(ignored_courses_key), options_cursos
    )

cursos_ignorados = st.multiselect(
    "Cursos a Ignorar:",
    options=options_cursos,
    key=ignored_courses_key,
    help="Selecione apenas os cursos que devem ficar fora desta sincronização.",
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

    removed_count = (
        int((df["sync_status"] == "removed_in_api").sum()) if not df.empty else 0
    )
    revalidation_count = (
        int((df["revalidation_required"] == "Sim").sum()) if not df.empty else 0
    )

    if removed_count:
        st.warning(
            f"⚠️ {removed_count} demanda(s) foram removidas na API e seguem preservadas localmente."
        )
    if revalidation_count:
        st.error(
            f"❗ {revalidation_count} demanda(s) exigem revalidação por mudança crítica na API ou remoção com alocação existente."
        )

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

    # Collect unique course codes for filter (include all courses for display filtering)
    cursos_unicos = sorted(df["codigo_curso"].fillna("").unique())
    cursos_unicos = [c for c in cursos_unicos if c.strip()]  # Remove empty entries
    filtro_curso = st.multiselect("Filtrar por Curso", options=cursos_unicos)

    lista_professores = sorted(list(profs_from_dem))
    filtro_professor = st.multiselect(
        "Filtrar por Professor", options=lista_professores
    )

    # Apply display filters (work independently on all database data)
    df_filtrado = df.copy()
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
        - Não é possível **adicionar** demandas diretamente via tabela (vide formulário abaixo). Nem todos os dados são editáveis.
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
                    "Origem": row["origem"],
                    "Status Sync": row["sync_status"],
                    "Override": row["tem_override"],
                    "Revalidar": row["revalidation_required"],
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
                    if isinstance(k, str) and k.startswith("demanda_table_editor")
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
                    help="Código do curso (ex: CND, GEAGRO)",
                ),
                "Código": st.column_config.TextColumn(
                    "Código",
                    required=True,
                    help="Código da disciplina (ex: FUP0011)",
                ),
                "Disciplina": st.column_config.TextColumn(
                    "Disciplina",
                    required=True,
                    help="Nome da disciplina",
                ),
                "Turma": st.column_config.TextColumn(
                    "Turma",
                    required=True,
                    help="Código da turma (ex: 1, 12)",
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
                "Origem": st.column_config.TextColumn(
                    "Origem",
                    disabled=True,
                    help="Origem da demanda: API ou manual.",
                ),
                "Status Sync": st.column_config.TextColumn(
                    "Status Sync",
                    disabled=True,
                    help="Estado atual da sincronização com a API.",
                ),
                "Override": st.column_config.TextColumn(
                    "Override",
                    disabled=True,
                    help="Indica se há override local em algum campo sincronizado.",
                ),
                "Revalidar": st.column_config.TextColumn(
                    "Revalidar",
                    disabled=True,
                    help="Indica se a demanda precisa ser revisada antes do ensalamento.",
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
                    allocation_repo = AlocacaoRepository(session)
                    deleted_list = []
                    blocked_list = []
                    for demanda_id in deleted_ids:
                        demanda = demanda_repo_delete.get_by_id(int(demanda_id))
                        allocations = allocation_repo.get_by_demanda(int(demanda_id))
                        if allocations:
                            if demanda:
                                blocked_list.append(
                                    f"{demanda.codigo_disciplina}-{demanda.turma_disciplina}"
                                )
                            continue
                        if demanda:
                            deleted_list.append(
                                f"{demanda.codigo_disciplina}-{demanda.turma_disciplina}"
                            )
                        demanda_repo_delete.delete(int(demanda_id))
                    if deleted_list:
                        set_session_feedback(
                            "demanda_crud_result",
                            True,
                            f"{len(deleted_list)} demanda(s) removida(s) com sucesso: {', '.join(deleted_list)}",
                            action="delete",
                        )
                        changes_made = True
                    if blocked_list:
                        set_session_feedback(
                            "demanda_crud_result",
                            False,
                            f"Não é possível remover demandas com alocações salvas. Remova antes as alocações de: {', '.join(blocked_list)}",
                            action="delete",
                        )
                        errors_occurred = True
            except Exception as e:
                set_session_feedback(
                    "demanda_crud_result",
                    False,
                    f"Erro ao deletar demanda(s): {str(e)}",
                    action="delete",
                )
                errors_occurred = True

        # Compare each row for changes (only for rows that still exist)
        for row_position, row in enumerate(edited_df.to_dict("records")):
            if row_position < len(edit_df):
                original_row = edit_df.iloc[row_position]

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
                            demanda_sync_service = DemandaSyncService(session)
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

                                demanda_sync_service.apply_manual_edit(
                                    demanda_id, update_data
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
            _clear_sigaa_compare_cache(selected_semester_id)
            st.rerun()
        # If only errors occurred, don't rerun so user can fix values

        # Display CRUD feedback
        display_session_feedback("demanda_crud_result")

# Track sync processing state in session state
if "sync_semestre_processing" not in st.session_state:
    st.session_state.sync_semestre_processing = False

# Show spinner if processing is active from a previous rerun
if st.session_state.sync_semestre_processing:
    with st.spinner(
        "🔄 Sincronizando dados da API... Isso pode levar alguns segundos."
    ):
        # Complete the sync operation
        try:
            summary = sync_semester_from_api(current_semester_name, cursos_ignorados)
            # success
            sync_message = (
                f"Sincronização concluída: {summary['created']} nova(s), "
                f"{summary['updated_from_api']} atualizada(s) da API, "
                f"{summary['unchanged']} sem alteração, "
                f"{summary['removed_in_api']} removida(s) na API e "
                f"{summary['professores']} professor(es) criado(s)."
            )
            if summary.get("skipped"):
                sync_message += f" {summary['skipped']} oferta(s) foram ignorada(s) ou descartada(s)."
            if summary.get("revalidation_required"):
                sync_message += f" {summary['revalidation_required']} demanda(s) exigem revalidação."
            set_session_feedback(
                "sync_semestre_result",
                True,
                sync_message,
                ttl=8,
                summary=summary,
            )
            _clear_sigaa_compare_cache(selected_semester_id)
        except Exception as e:
            # store error feedback
            set_session_feedback(
                "sync_semestre_result",
                False,
                f"Erro na sincronização: {type(e).__name__}: {e}",
                ttl=12,
            )

        # Reset processing state
        st.session_state.sync_semestre_processing = False

        # Rerun to refresh the page and show results
        st.rerun()

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
            "Sincronização disponível apenas para semestres ativos. Selecione um semestre ativo na página ⚙️ Configurações.",
            ttl=6,
        )
        st.rerun()
    else:
        # Set processing state and rerun to start spinner
        st.session_state.sync_semestre_processing = True
        st.rerun()

st.markdown("---")

# Manual Demanda Addition Form
st.subheader("➕ Adicionar Demanda Manualmente")

st.info(
    """
Adicione uma nova demanda manualmente preenchendo os campos obrigatórios abaixo.
Isso permite criar demandas que não estão disponíveis via API de sincronização.
"""
)

# Form for manual demanda creation
with st.form("form_demanda_manual"):
    col1, col2 = st.columns(2)

    with col1:
        codigo_curso = st.text_input(
            "Código do Curso *",
            placeholder="ex: CND",
            help="Código do curso (ex: CND, PPGCA-M). Obrigatório.",
        )
        codigo_disciplina = st.text_input(
            "Código da Disciplina *",
            placeholder="ex: FUP0011",
            help="Código da disciplina. Obrigatório.",
        )
        nome_disciplina = st.text_input(
            "Nome da Disciplina *",
            placeholder="ex: CALCULO DIFERENCIAL E INTEGRAL I",
            help="Nome completo da disciplina. Obrigatório.",
        )
        turma_disciplina = st.text_input(
            "Turma", placeholder="ex: 1", help="Código da turma (ex: 1, 12). Opcional."
        )

    with col2:
        professores_disciplina = st.text_input(
            "Professores",
            placeholder="ex: João Silva, Maria Santos",
            help="Lista de professores separados por vírgula. Opcional.",
        )
        vagas_disciplina = st.number_input(
            "Vagas",
            min_value=1,
            value=30,
            step=1,
            help="Número de vagas disponíveis. Deve ser maior que 0.",
        )
        horario_sigaa_bruto = st.text_input(
            "Horário SIGAA *",
            placeholder="ex: 24M12 6T34",
            help="Horário bruto no formato SIGAA (ex: 24M12 6T34). Obrigatório. Use espaços entre blocos.",
        )
        # Add a preview of the parsed schedule
        if horario_sigaa_bruto.strip():
            try:
                parser = get_sigaa_parser()
                horario_legivel = parser.parse_to_human_readable(
                    horario_sigaa_bruto.strip()
                )
                num_slots = len(
                    parser.split_to_atomic_array(horario_sigaa_bruto.strip())
                )
            except Exception as e:
                st.warning(f"⚠️ Erro ao analisar horário: {str(e)}")

    if st.form_submit_button("➕ Adicionar Demanda", width="content"):
        # Validation
        errors = []

        # Check required fields
        if not codigo_curso.strip():
            errors.append("Código do curso é obrigatório")
        if not codigo_disciplina.strip():
            errors.append("Código da disciplina é obrigatório")
        else:
            # Validate codigo_disciplina format: only [A-Z] and [0-9], 7-11 chars
            codigo_clean = codigo_disciplina.strip()
            if len(codigo_clean) < 7:
                errors.append("Código da disciplina deve ter pelo menos 7 caracteres")
            elif len(codigo_clean) > 11:
                errors.append("Código da disciplina deve ter no máximo 11 caracteres")
            elif not codigo_clean.isupper() or not all(
                c.isalnum() for c in codigo_clean
            ):
                errors.append(
                    "Código da disciplina deve conter apenas letras maiúsculas [A-Z] e números [0-9]"
                )
        if not nome_disciplina.strip():
            errors.append("Nome da disciplina é obrigatório")
        if not horario_sigaa_bruto.strip():
            errors.append("Horário SIGAA é obrigatório")

        # Validate schedule format
        if horario_sigaa_bruto.strip():
            try:
                parser = get_sigaa_parser()
                # Validate that we can parse and split the schedule
                atomic_array = parser.split_to_atomic_array(horario_sigaa_bruto.strip())
                if not atomic_array:
                    errors.append("Horário SIGAA não produziu blocos atômicos válidos")
            except Exception as e:
                errors.append(f"Formato de horário inválido: {str(e)}")

        if errors:
            for error in errors:
                set_session_feedback("demanda_manual_form_result", False, error)
        else:
            try:
                with get_db_session() as session:
                    demanda_sync_service = DemandaSyncService(session)

                    # Clean input data
                    cleaned_codigo_curso = codigo_curso.strip().upper()
                    cleaned_codigo_disciplina = codigo_disciplina.strip().upper()
                    cleaned_nome_disciplina = nome_disciplina.strip().upper()
                    cleaned_turma = (
                        turma_disciplina.strip().upper()
                        if turma_disciplina.strip()
                        else ""
                    )
                    cleaned_professores = (
                        professores_disciplina.strip()
                        if professores_disciplina.strip()
                        else ""
                    )

                    # Convert the user input schedule to atomic format for database storage
                    horario_atomic = " ".join(
                        atomic_array
                    )  # Join atomic blocks with spaces

                    demanda_sync_service.create_manual_demanda(
                        {
                            "semestre_id": selected_semester_id,
                            "codigo_disciplina": cleaned_codigo_disciplina,
                            "nome_disciplina": cleaned_nome_disciplina,
                            "professores_disciplina": cleaned_professores,
                            "turma_disciplina": cleaned_turma,
                            "vagas_disciplina": int(vagas_disciplina),
                            "horario_sigaa_bruto": horario_atomic,
                            "codigo_curso": cleaned_codigo_curso,
                            "id_oferta_externo": None,
                        }
                    )

                    set_session_feedback(
                        "demanda_manual_form_result",
                        True,
                        f"Demanda {cleaned_codigo_disciplina}-{cleaned_turma or 'única'} adicionada com sucesso!",
                    )
                    _clear_sigaa_compare_cache(selected_semester_id)
                    st.rerun()

            except Exception as e:
                set_session_feedback(
                    "demanda_manual_form_result",
                    False,
                    f"Erro ao criar demanda: {str(e)}",
                )
                st.rerun()

# Display form result feedback
display_session_feedback("demanda_manual_form_result")

st.markdown("---")
st.subheader("🔎 Comparar com SIGAA")
st.caption(
    "Consulta todas as demandas do semestre ativo consolidando por professores e horários. Os filtros da grade acima não alteram esta comparação."
)

if st.button(
    "🔎 Comparar demanda com SIGAA",
    disabled=not semestre_status_active,
    help="Consulta a página pública de turmas do SIGAA e compara com todas as demandas do semestre ativo.",
    key=f"compare_sigaa_{selected_semester_id}",
):
    if not semestre_status_active:
        set_session_feedback(
            "sigaa_compare_result",
            False,
            "A comparação com o SIGAA está disponível apenas para o semestre ativo.",
            ttl=8,
        )
        st.rerun()

    with st.spinner(
        "Consultando turmas públicas do SIGAA e comparando com a demanda local..."
    ):
        try:
            comparison_service = get_sigaa_discrepancy_service()
            comparison_result = comparison_service.compare_local_dataframe_to_sigaa(
                current_semester_name,
                df,
            )
            st.session_state[compare_cache_key] = comparison_result
            set_session_feedback(
                "sigaa_compare_result",
                True,
                "Comparação com o SIGAA concluída com sucesso.",
                ttl=8,
            )
        except Exception as e:
            _clear_sigaa_compare_cache(selected_semester_id)
            set_session_feedback(
                "sigaa_compare_result",
                False,
                f"Erro ao comparar com o SIGAA: {type(e).__name__}: {e}",
                ttl=12,
            )
        st.rerun()

comparison_result = st.session_state.get(compare_cache_key)
if comparison_result:
    metric_cols = st.columns(5)
    metric_cols[0].metric("Local Consolidado", comparison_result["local_total"])
    metric_cols[1].metric("Turmas SIGAA", comparison_result["sigaa_total"])
    metric_cols[2].metric("Divergências", comparison_result["discrepancy_count"])
    metric_cols[3].metric(
        "Ausentes no SIGAA",
        comparison_result["missing_in_sigaa_count"],
    )
    metric_cols[4].metric(
        "Ausentes na Demanda",
        comparison_result["missing_in_local_count"],
    )

    st.markdown("**Divergências encontradas**")
    if comparison_result["discrepancies"]:
        st.dataframe(
            _comparison_table_df(comparison_result["discrepancies"]),
            width="stretch",
            hide_index=True,
        )
    else:
        st.success("Nenhuma divergência foi encontrada nas turmas comparadas.")

    st.markdown("**Ofertas locais ausentes no SIGAA**")
    if comparison_result["missing_in_sigaa"]:
        st.dataframe(
            _comparison_table_df(comparison_result["missing_in_sigaa"]),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Nenhuma oferta local ficou sem correspondência no SIGAA.")

    st.markdown("**Turmas do SIGAA ausentes na demanda local**")
    if comparison_result["missing_in_local"]:
        st.dataframe(
            _comparison_table_df(comparison_result["missing_in_local"]),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Nenhuma turma do SIGAA ficou sem correspondência na demanda local.")

    with st.expander("Diagnóstico técnico da consulta SIGAA"):
        st.json(comparison_result.get("probe", {}))

# Page Footer
page_footer.show()
