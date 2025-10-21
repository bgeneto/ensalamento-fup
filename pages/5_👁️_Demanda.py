"""
Visualização da Demanda Semestral

Página para que o administrador inspecione as demandas importadas do
Sistema de Oferta: seleção de semestre, métricas de resumo, avisos
acionáveis (professores não cadastrados) e tabela filtrável com colunas
amigáveis geradas pelo parser Sigaa.

Route: pages/5_🎓_Demanda.py
"""

import streamlit as st
from typing import List
import pandas as pd

from src.config.database import get_db_session
from src.repositories.semestre import SemestreRepository
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.professor import ProfessorRepository
from docs.sigaa_parser import SigaaScheduleParser
from src.utils.ui_feedback import set_session_feedback, display_session_feedback
from src.services.semester_service import sync_semester_from_api

# ============================================================================
# AUTHENTICATION CHECK
# ============================================================================
# Retrieve authenticator from session state (set by main.py)
authenticator = st.session_state.get("authenticator")

if authenticator is None:
    st.warning("👈 Por favor, faça login na página inicial para acessar o sistema.")
    st.page_link("main.py", label="Voltar para o início ↩", icon="🏠")
    # navigate back to main page where login widget is located
    st.switch_page("main.py")
    st.stop()

try:
    authenticator.login(location="unrendered", key="authenticator-demandas")
except Exception as exc:
    st.error(f"❌ Erro de autenticação: {exc}")
    st.stop()

if not st.session_state.get("authentication_status"):
    st.error("❌ Acesso negado.")
    st.stop()

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(page_title="Demanda  - Ensalamento", page_icon="👁️", layout="wide")

st.title("👁️ Demanda Semestral")

# Display any persisted feedback from prior action
display_session_feedback("sync_semestre_result")

parser = SigaaScheduleParser()


def _demanda_dtos_to_df(dtos: List) -> pd.DataFrame:
    """Converte uma lista de DemandaRead DTOs para um DataFrame com colunas amigáveis."""
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
            ]
        )

    return df


with get_db_session() as session:
    sem_repo = SemestreRepository(session)
    dem_repo = DisciplinaRepository(session)
    prof_repo = ProfessorRepository(session)

    # Load semesters for the selectbox
    semestres = [s.nome for s in sem_repo.get_all()]
    if not semestres:
        st.info(
            "Nenhum semestre encontrado. Importe um semestre na página de sincronização."
        )
        st.stop()

    semestre_selecionado = st.selectbox(
        "Selecione o Semestre",
        options=semestres,
        width=150,
    )

    # Resolve semestre id
    semestre = sem_repo.get_by_name(semestre_selecionado)
    if not semestre:
        st.error("Semestre selecionado não encontrado.")
        st.stop()

    demandas = dem_repo.get_by_semestre(semestre.id)
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
    st.subheader("Detalhes da Demanda Selecionada")

    filtro_disciplina = st.text_input("Buscar por Nome ou Código da Disciplina")
    lista_professores = sorted(list(profs_from_dem))
    filtro_professor = st.multiselect(
        "Filtrar por Professor", options=lista_professores
    )

    df_filtrado = df.copy()

    if filtro_disciplina:
        term = filtro_disciplina.lower()
        df_filtrado = df_filtrado[
            df_filtrado["codigo_disciplina"].str.lower().str.contains(term, na=False)
            | df_filtrado["nome_disciplina"].str.lower().str.contains(term, na=False)
        ]

    if filtro_professor:
        # keep rows where any of the selected professor names appear in the professores_disciplina cell
        mask = df_filtrado["professores_disciplina"].apply(
            lambda cell: any(
                p in [x.strip() for x in str(cell).split(",") if x.strip()]
                for p in filtro_professor
            )
        )
        df_filtrado = df_filtrado[mask]

    # Select and order columns for display
    display_cols = [
        "codigo_disciplina",
        "nome_disciplina",
        "turma_disciplina",
        "vagas_disciplina",
        "professores_disciplina",
        "horario_legivel",
        "num_slots",
    ]

    # If dataframe empty show a friendly message
    if df_filtrado.empty:
        st.info("Nenhuma demanda encontrada para o semestre/filtragem selecionada.")
    else:
        st.dataframe(
            df_filtrado[display_cols].rename(
                columns={
                    "codigo_disciplina": "Código",
                    "nome_disciplina": "Disciplina",
                    "turma_disciplina": "Turma",
                    "vagas_disciplina": "Vagas",
                    "professores_disciplina": "Professores (API)",
                    "horario_legivel": "Horário (Legível)",
                    "num_slots": "Nº de Slots",
                }
            ),
            width="stretch",
        )

if st.button(
    f"🔄 Sincronizar demanda {semestre_selecionado}",
    help="Importar demanda por salas do Sistema de Oferta",
):
    # Run the sync and store result in session state before rerun
    try:
        summary = sync_semester_from_api(semestre_selecionado)
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

    # Rerun once so display_session_feedback shows the message
    st.rerun()
