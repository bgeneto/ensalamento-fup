"""
Authentication State - Reflex Implementation
Follows patterns documented in docs/Reflex_Architecture_Document.md
"""

import reflex as rx


class AuthState(rx.State):
    """Global authentication state with LocalStorage persistence"""

    # Persistent authentication state (survives browser refresh)
    username: str = rx.LocalStorage(default="")
    is_logged_in: bool = rx.LocalStorage(default=False, name="auth_logged_in")
    role: str = rx.LocalStorage(default="user", name="auth_role")

    # Session-only authentication state (resets on tab close)
    current_token: str = rx.SessionStorage(default="", name="auth_token")

    # Volatile state (resets on navigation/actions)
    login_loading: bool = False
    login_username: str = ""  # Form field
    login_password: str = ""  # Form field
    login_error: str = ""

    @rx.var
    def display_name(self) -> str:
        """Computed property for display name"""
        return f"@{self.username}" if self.username else "Guest"

    @rx.var
    def is_admin(self) -> bool:
        """Computed property for admin role check"""
        return self.role == "admin"

    async def login(self):
        """
        Async login with validation and feedback

        Follows the async loading pattern from docs
        """
        # Prevent concurrent login attempts
        if self.login_loading:
            return rx.toast.info("Login already in progress")

        # Reset error state
        self.login_error = ""

        # Basic client-side validation
        if not self.login_username or not self.login_password:
            self.login_error = "Please enter both username and password"
            return rx.toast.error("Please enter both username and password")

        self.login_loading = True
        yield  # Update UI immediately

        try:
            # Call authentication service (async)
            user_data = await self._verify_credentials(
                self.login_username, self.login_password
            )

            if user_data:
                # Successful login - update persistent state
                self.username = user_data["username"]
                self.role = user_data.get("role", "user")
                self.is_logged_in = True
                self.current_token = user_data.get("token", "")

                # Clear form fields
                self.login_username = ""
                self.login_password = ""

                # Navigate to dashboard
                yield rx.redirect("/dashboard")
                yield rx.toast.success(f"Welcome, {user_data['username']}!")
            else:
                # Failed login
                self.login_error = "Invalid username or password"
                yield rx.toast.error("Invalid username or password")

        except Exception as e:
            # Server error
            self.login_error = "Login service temporarily unavailable"
            yield rx.toast.error(
                "Login service temporarily unavailable. Please try again."
            )
            self._log_error("Login failed", e)

        finally:
            self.login_loading = False

    def logout(self):
        """
        Clear all authentication state and redirect to login

        Follows defensive mutation pattern
        """
        self.username = ""
        self.is_logged_in = False
        self.role = "user"
        self.current_token = ""
        self.login_username = ""
        self.login_password = ""
        self.login_error = ""

        return rx.redirect("/login")

    # Form field setters (following state pattern)
    def set_login_username(self, value: str):
        """Update login username form field"""
        self.login_username = value.strip()
        # Clear previous error when user starts typing
        if self.login_error:
            self.login_error = ""

    def set_login_password(self, value: str):
        """Update login password form field"""
        self.login_password = value.strip()
        # Clear previous error when user starts typing
        if self.login_error:
            self.login_error = ""

    async def _verify_credentials(self, username: str, password: str) -> dict | None:
        """
        Verify credentials against authentication service

        In Phase 1, we'll use a simplified version that integrates with
        the existing authentication system from streamlit-legacy
        """
        try:
            # TODO: Phase 1 - Simple credential check
            # This should integrate with your existing auth mechanism

            # Placeholder implementation - replace with real auth service
            if username == "admin" and password == "admin123":
                return {
                    "username": username,
                    "role": "admin",
                    "token": f"token_{username}_{hash(password)}",  # Simple token
                }
            elif username == "professor" and password == "prof123":
                return {
                    "username": username,
                    "role": "user",
                    "token": f"token_{username}_{hash(password)}",
                }

            # Integration with existing auth system (Phase 2)
            # from streamlit_legacy.src.utils.auth_helper import verify_credentials_sync
            # return await asyncio.to_thread(verify_credentials_sync, username, password)

            return None

        except Exception as e:
            self._log_error("Credential verification failed", e)
            return None

    def _log_error(self, message: str, error: Exception):
        """Log authentication errors for debugging"""
        print(f"AUTH ERROR: {message} - {str(error)}")
        # TODO: Phase 2 - Send to proper logging service
