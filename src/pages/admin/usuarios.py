"""
User management page for Sistema de Ensalamento FUP/UnB
Administrative interface for managing system users
"""

import streamlit as st
from typing import Optional
from src.services.auth_service import AuthService
from models import UsuarioCreate, UsuarioUpdate


def render_usuarios_page():
    """Render user management page"""
    st.title("👥 Gestão de Usuários")
    st.caption("Gerencie usuários e permissões do sistema")

    # Check if user is admin
    if not is_current_user_admin():
        st.error("❌ Acesso negado. Esta página requer privilégios de administrador.")
        return

    # Create tabs for different operations
    tab1, tab2, tab3 = st.tabs(
        ["📋 Lista de Usuários", "➕ Criar Usuário", "🔧 Gerenciar"]
    )

    with tab1:
        render_user_list()

    with tab2:
        render_create_user()

    with tab3:
        render_manage_user()


def render_user_list():
    """Render list of all users"""
    st.header("📋 Lista de Usuários")

    # Get all users
    users = AuthService.get_all_users()

    if not users:
        st.info("Nenhum usuário encontrado no sistema.")
        return

    # Display user statistics
    stats = AuthService.get_user_stats()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Usuários", stats["total"])
    with col2:
        st.metric("Administradores", stats["admin"])
    with col3:
        st.metric("Professores", stats["professor"])

    st.markdown("---")

    # Display users in a table format
    for user in users:
        with st.expander(f"👤 {user.username} ({user.nome_completo or 'Sem nome'})"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write(f"**Função:** {user.role}")
                st.write(f"**Nome:** {user.nome_completo or 'Não definido'}")

            with col2:
                st.write(f"**Usuário:** {user.username}")

            with col3:
                # Action buttons
                if st.button(f"Editar {user.username}", key=f"edit_{user.username}"):
                    st.session_state["editing_user"] = user.username
                    st.rerun()

                if st.button(
                    f"Excluir {user.username}",
                    key=f"delete_{user.username}",
                    type="secondary",
                ):
                    if AuthService.delete_user(user.username):
                        st.success(f"Usuário {user.username} excluído com sucesso!")
                        st.rerun()
                    else:
                        st.error(f"Não foi possível excluir o usuário {user.username}")

    # Check if there's a user being edited
    if "editing_user" in st.session_state:
        render_edit_user_form(st.session_state["editing_user"])


def render_create_user():
    """Render create user form"""
    st.header("➕ Criar Novo Usuário")

    with st.form("create_user_form"):
        st.subheader("Informações do Usuário")

        col1, col2 = st.columns(2)

        with col1:
            username = st.text_input(
                "Nome de Usuário",
                placeholder="ex: joao.silva",
                help="Nome de usuário único para login",
            )

            password = st.text_input(
                "Senha",
                type="password",
                placeholder="Mínimo 6 caracteres",
                help="Senha para acesso ao sistema",
            )

            confirm_password = st.text_input(
                "Confirmar Senha",
                type="password",
                placeholder="Digite a senha novamente",
            )

        with col2:
            nome_completo = st.text_input(
                "Nome Completo", placeholder="ex: João Silva Santos"
            )

            role = st.selectbox(
                "Função",
                options=["professor", "admin"],
                help="Administradores têm acesso total ao sistema",
            )

        st.markdown("---")

        submitted = st.form_submit_button(
            "Criar Usuário", type="primary", use_container_width=True
        )

        if submitted:
            # Validate inputs
            if not username or not password:
                st.error("❌ Nome de usuário e senha são obrigatórios.")
                return

            if len(password) < 6:
                st.error("❌ A senha deve ter pelo menos 6 caracteres.")
                return

            if password != confirm_password:
                st.error("❌ As senhas não coincidem.")
                return

            # Create user
            if AuthService.create_user(username, password, nome_completo, role):
                st.success(f"✅ Usuário '{username}' criado com sucesso!")
            else:
                st.error(
                    f"❌ Falha ao criar usuário '{username}'. O nome de usuário já pode estar em uso."
                )


def render_manage_user():
    """Render user management operations"""
    st.header("🔧 Gerenciar Usuários")

    # User selection
    users = AuthService.get_all_users()
    if not users:
        st.info("Nenhum usuário disponível para gerenciamento.")
        return

    user_options = [f"{u.username} ({u.nome_completo or 'Sem nome'})" for u in users]
    user_map = {f"{u.username} ({u.nome_completo or 'Sem nome'})": u for u in users}

    selected_user_str = st.selectbox(
        "Selecione um usuário para gerenciar:", user_options
    )
    selected_user = user_map[selected_user_str]

    if not selected_user:
        return

    st.markdown("---")

    # Display user information
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Informações Atuais")
        st.write(f"**Usuário:** {selected_user.username}")
        st.write(f"**Nome:** {selected_user.nome_completo or 'Não definido'}")
        st.write(f"**Função:** {selected_user.role}")

    with col2:
        st.subheader("Operações")

        # Password reset
        if st.button("🔑 Redefinir Senha", type="secondary"):
            st.session_state["reset_password_user"] = selected_user.username
            st.rerun()

        # Change role
        new_role = st.selectbox(
            "Alterar Função",
            options=["professor", "admin"],
            index=0 if selected_user.role == "professor" else 1,
        )

        if st.button("💾 Salvar Alterações", type="primary"):
            if AuthService.update_user(
                selected_user.username,
                UsuarioUpdate(nome_completo=selected_user.nome_completo, role=new_role),
            ):
                st.success("✅ Alterações salvas com sucesso!")
                st.rerun()
            else:
                st.error("❌ Falha ao salvar alterações.")

    # Password reset form
    if (
        "reset_password_user" in st.session_state
        and st.session_state["reset_password_user"] == selected_user.username
    ):
        st.markdown("---")
        st.subheader("🔑 Redefinir Senha")

        with st.form(f"reset_password_form_{selected_user.username}"):
            new_password = st.text_input(
                "Nova Senha", type="password", placeholder="Mínimo 6 caracteres"
            )

            confirm_password = st.text_input("Confirmar Nova Senha", type="password")

            submitted = st.form_submit_button("Redefinir Senha", type="primary")

            if submitted:
                if len(new_password) < 6:
                    st.error("❌ A senha deve ter pelo menos 6 caracteres.")
                    return

                if new_password != confirm_password:
                    st.error("❌ As senhas não coincidem.")
                    return

                # For admin users, we can update directly, for others we need current password
                if selected_user.role == "admin":
                    # Admin password reset (no old password required)
                    with DatabaseSession() as session:
                        import bcrypt

                        # Hash new password
                        password_hash = bcrypt.hashpw(
                            new_password.encode("utf-8"), bcrypt.gensalt()
                        ).decode("utf-8")
                        selected_user.password_hash = password_hash
                        session.commit()

                        st.success("✅ Senha redefinida com sucesso!")
                        del st.session_state["reset_password_user"]
                        st.rerun()
                else:
                    st.info(
                        "Para usuários não administradores, a senha atual é necessária para alteração."
                    )


def render_edit_user_form(username):
    """Render edit user form"""
    user = AuthService.get_user_by_username(username)

    if not user:
        st.error(f"Usuário '{username}' não encontrado.")
        return

    st.subheader(f"✏️ Editar Usuário: {username}")

    with st.form(f"edit_user_form_{username}"):
        col1, col2 = st.columns(2)

        with col1:
            nome_completo = st.text_input(
                "Nome Completo", value=user.nome_completo or ""
            )

        with col2:
            role = st.selectbox(
                "Função",
                options=["professor", "admin"],
                index=0 if user.role == "professor" else 1,
            )

        col1, col2 = st.columns(2)

        with col1:
            st.form_submit_button("💾 Salvar Alterações", type="primary")

        with col2:
            if st.form_submit_button("❌ Cancelar", type="secondary"):
                del st.session_state["editing_user"]
                st.rerun()

    # Process form submission
    if submitted:
        if AuthService.update_user(
            username, UsuarioUpdate(nome_completo=nome_completo, role=role)
        ):
            st.success(f"✅ Usuário '{username}' atualizado com sucesso!")
            del st.session_state["editing_user"]
            st.rerun()
        else:
            st.error(f"❌ Falha ao atualizar usuário '{username}'.")


# Helper function to check if current user is admin
def is_current_user_admin():
    """Check if current user has admin role"""
    from src.services.auth_service import get_current_user, AuthService

    username = get_current_user()
    return username is not None and AuthService.is_admin(username)


def main():
    """Main entry point for the users page"""
    render_usuarios_page()


if __name__ == "__main__":
    main()
