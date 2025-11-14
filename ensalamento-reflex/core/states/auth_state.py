"""Authentication state with LocalStorage persistence."""

from typing import Optional

import reflex as rx

from .base_state import BaseState


class AuthState(BaseState):
    """Authentication state with LocalStorage persistence.

    Provides login/logout functionality with browser refresh persistence,
    replacing Streamlit's SessionState-based authentication.
    """

    # Persistent state - survives browser refresh
    username: str = rx.LocalStorage(default="")
    is_logged_in: bool = rx.LocalStorage(default=False, name="auth_logged_in")
    role: str = rx.LocalStorage(default="user", name="auth_role")

    # Session-only state - resets on tab close
    current_token: str = rx.SessionStorage(default="", name="auth_token")

    # Volatile state for UI
    login_username: str = ""
    login_password: str = ""
    login_error: str = ""

    @rx.var
    def display_name(self) -> str:
        """Computed property for display name."""
        return f"@{self.username}" if self.username else "Guest"

    @rx.var
    def is_admin(self) -> bool:
        """Computed property for admin role check."""
        return self.role == "admin"

    @rx.var
    def is_coordinator(self) -> bool:
        """Computed property for coordinator role check."""
        return self.role in ["admin", "coordinator"]

    async def login(self, form_data: Optional[dict] = None):
        """Async login with validation and feedback.

        Args:
            form_data: Optional form data dict with username/password
        """
        # Use form data if provided, otherwise use state variables
        username = (
            form_data.get("username", self.login_username)
            if form_data
            else self.login_username
        )
        password = (
            form_data.get("password", self.login_password)
            if form_data
            else self.login_password
        )

        # Reset error state
        self.login_error = ""

        # Basic validation
        if not username or not password:
            self.login_error = "Nome de usuário e senha são obrigatórios"
            yield rx.toast.error("Nome de usuário e senha são obrigatórios")
            return

        try:
            # Call validation function (implement based on existing Streamlit auth)
            user_data = await self._verify_credentials(username, password)

            if user_data and user_data.get("success", False):
                # Set persistent state
                self.username = user_data["username"]
                self.role = user_data.get("role", "user")
                self.is_logged_in = True
                self.current_token = user_data.get("token", "")

                # Clear form
                self.login_username = ""
                self.login_password = ""

                # Success feedback
                yield rx.toast.success(f"Bem-vindo, {user_data['username']}!")

                # Navigate to dashboard
                yield rx.redirect("/dashboard")

            else:
                error_msg = "Credenciais inválidas"
                self.login_error = error_msg
                yield rx.toast.error(error_msg)

        except Exception as e:
            error_msg = f"Erro no login: {str(e)}"
            self.login_error = error_msg
            yield rx.toast.error("Erro interno do servidor")
            print(f"Login error: {error_msg}")  # TODO: Replace with proper logging

    def logout(self):
        """Clear all authentication state."""
        # Clear persistent state
        self.username = ""
        self.is_logged_in = False
        self.role = "user"
        self.current_token = ""

        # Clear session state
        self.login_username = ""
        self.login_password = ""
        self.login_error = ""

        # Navigate to login
        return rx.redirect("/")

    def set_login_username(self, username: str):
        """Set login username."""
        self.login_username = username
        self.login_error = ""  # Clear error when user types

    def set_login_password(self, password: str):
        """Set login password."""
        self.login_password = password
        self.login_error = ""  # Clear error when user types

    async def _verify_credentials(self, username: str, password: str) -> Optional[dict]:
        """Verify credentials against authentication system.

        This method should be implemented to wrap the existing
        Streamlit authentication logic.

        Args:
            username: Username to verify
            password: Password to verify

        Returns:
            Dict with user data if valid, None if invalid
        """
        try:
            # TODO: Import and wrap existing authentication logic
            # For now, return mock data for development
            if username == "admin" and password == "admin":
                return {
                    "success": True,
                    "username": username,
                    "role": "admin",
                    "token": f"token_{username}_123",
                }
            elif username == "coord" and password == "coord":
                return {
                    "success": True,
                    "username": username,
                    "role": "coordinator",
                    "token": f"token_{username}_123",
                }
            else:
                return {"success": False, "error": "Invalid credentials"}

        except Exception as e:
            print(f"Credential verification error: {e}")
            return {"success": False, "error": str(e)}

    def check_auth_status(self):
        """Check and refresh authentication status.

        Can be called periodically or on app initialization.
        """
        # This could verify token validity, refresh tokens, etc.
        # For now, just ensure state consistency
        if not self.is_logged_in:
            self.logout()

    async def refresh_token(self):
        """Refresh authentication token if needed."""
        # TODO: Implement token refresh logic
        pass
