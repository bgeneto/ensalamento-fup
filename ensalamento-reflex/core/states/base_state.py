"""Base state class with common patterns for Reflex application."""

from typing import Any, Awaitable, Callable, Optional

import reflex as rx


class BaseState(rx.State):
    """Base state class with common functionality for all Reflex states.

    Provides standardized patterns for:
    - Loading states and progress management
    - Error handling with user-friendly messages
    - Success feedback via toast notifications
    - Generic async operation handling
    - Defensive mutation patterns
    """

    # Common state variables
    loading: bool = False
    error: str = ""
    success_message: str = ""

    def set_error(self, message: str):
        """Set error state and reset loading/success."""
        self.error = message
        self.loading = False
        self.success_message = ""

    def set_success(self, message: str):
        """Set success state and reset error."""
        self.success_message = message
        self.error = ""

    def clear_messages(self):
        """Clear all messages and loading state."""
        self.error = ""
        self.success_message = ""
        self.loading = False

    async def handle_async_operation(
        self,
        operation_name: str,
        operation_func: Callable[..., Awaitable[Any]],
        *args,
        success_message: Optional[str] = None,
        error_prefix: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Handle async operations with standardized error/loading management.

        Args:
            operation_name: Human-readable name for the operation (shown in feedback)
            operation_func: Async function to execute
            *args: Positional arguments for the operation
            success_message: Custom success message (optional)
            error_prefix: Custom error prefix (optional)
            **kwargs: Keyword arguments for the operation

        Returns:
            Result of the operation if successful

        Yields toast notifications for user feedback.
        """
        # Prevent concurrent operations
        if self.loading:
            yield rx.toast.info(f"{operation_name} already in progress")
            return

        # Setup loading state
        self.loading = True
        self.error = ""
        self.success_message = ""
        yield

        try:
            # Execute the operation
            result = await operation_func(*args, **kwargs)

            # Success handling
            success_msg = success_message or f"{operation_name} completed successfully"
            self.success_message = success_msg
            yield rx.toast.success(success_msg)

        except Exception as e:
            # Error handling
            error_prefix_text = error_prefix or f"{operation_name} failed"
            error_msg = f"{error_prefix_text}: {str(e)}"
            self.error = error_msg
            yield rx.toast.error(error_msg)

            # Log error for debugging (would connect to proper logging in production)
            print(f"Operation error: {error_msg}")  # TODO: Replace with proper logging

        finally:
            # Clean up loading state
            self.loading = False

    def set_loading(self, loading: bool):
        """Set loading state."""
        self.loading = loading
        if loading:
            self.error = ""
            self.success_message = ""
