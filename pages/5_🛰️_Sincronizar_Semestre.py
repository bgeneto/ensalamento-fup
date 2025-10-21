"""
Sincronizar Semestre - Importar ofertas do Sistema de Oferta

Adds a simple UI to trigger `sync_semester_from_api()` and present results
using the project's session-feedback helpers (set_session_feedback / display_session_feedback).

Route: pages/5_🛰️_Sincronizar_Semestre.py
"""

import streamlit as st

# Authentication pattern: retrieve authenticator from session state (set in main.py)
authenticator = st.session_state.get("authenticator")

if authenticator is None:
    st.warning("👈 Por favor, faça login na página inicial para acessar o sistema.")
    st.page_link("main.py", label="Voltar para o início ↩", icon="🏠")
    st.stop()

try:
    authenticator.login(location="unrendered", key="authenticator-sync")
except Exception as exc:
    st.error(f"❌ Erro de autenticação: {exc}")
    st.stop()

if not st.session_state.get("authentication_status"):
    st.error("❌ Acesso negado.")
    st.stop()

st.set_page_config(page_title="Sincronizar Semestre", page_icon="🛰️", layout="centered")

from src.services.semester_service import sync_semester_from_api
from src.utils.ui_feedback import set_session_feedback, display_session_feedback

st.title("🛰️ Sincronizar Semestre - Sistema de Oferta")

# Display any persisted feedback from prior action
display_session_feedback("sync_semestre_result")

st.markdown(
    "Use esta ferramenta para importar as ofertas de um semestre do Sistema de Oferta."
)

col1, col2 = st.columns([2, 1])
with col1:
    semestre_code = st.text_input("Código do semestre (ex: 2025-2)", value="2025-2")
with col2:
    if st.button("🔄 Sincronizar agora"):
        # Run the sync and store result in session state before rerun
        try:
            summary = sync_semester_from_api(semestre_code)
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

st.markdown("---")

st.caption("Observação: o processo é idempotente — re-executar não criará duplicatas.")
