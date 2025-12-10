import os
import streamlit as st


def render_manual_sidebar():
    """
    Renders the User Manual links (PDF download and Online Site) in the sidebar.
    Should be called inside a st.sidebar context or just generally to append to sidebar.
    """
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📘 Ajuda")

        # 1. PDF Download
        # Check potential paths for the PDF (depending on where run from)
        possible_paths = [
            "docs-site/pdf/manual-usuario-ensalamento-fup.pdf",
            "../docs-site/pdf/manual-usuario-ensalamento-fup.pdf",
        ]

        pdf_file = None
        for path in possible_paths:
            if os.path.exists(path):
                pdf_file = path
                break

        if pdf_file:
            try:
                with open(pdf_file, "rb") as f:
                    pdf_data = f.read()

                st.download_button(
                    label="📥 Baixar Manual (PDF)",
                    data=pdf_data,
                    file_name="manual-ensalamento-fup.pdf",
                    mime="application/pdf",
                    help="Baixar o manual completo em PDF",
                    use_container_width=True,
                )
            except Exception as e:
                st.warning(f"Erro ao carregar PDF: {e}")

        # 2. Online Link
        # Default to localhost:8000 for local dev, or use env var for production
        docs_url = os.getenv("DOCS_URL", "http://localhost:8000")

        st.link_button(
            label="🌐 Manual Online",
            url=docs_url,
            help="Acessar o site da documentação (requer servidor rodando)",
            use_container_width=True,
            icon="🔗",
        )

        st.caption("ℹ️ Para ver o manual online, execute `mkdocs serve` no terminal.")
