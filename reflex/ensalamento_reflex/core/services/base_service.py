"""
Base Service - Reflex Async Foundation
Provides common async execution patterns for all services

Following service layer patterns from docs/API_Interface_Specifications.md
"""

import asyncio
from abc import ABC
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable


class BaseService(ABC):
    """
    Abstract base class for all Reflex services

    Provides common async execution patterns and error handling
    """

    # Shared thread pool for all services
    _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="reflex-service")

    @staticmethod
    async def execute_async(func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Execute synchronous function asynchronously using thread pool

        This is the core pattern for wrapping existing synchronous business logic
        with async Reflex state management.

        Args:
            func: Synchronous function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the synchronous function execution

        Pattern: This enables seamless integration of existing synchronous
        business logic with Reflex's reactive async state system.
        """
        loop = asyncio.get_event_loop()

        try:
            # Execute in thread pool to not block event loop
            result = await loop.run_in_executor(
                BaseService._executor, func, *args, **kwargs
            )

            return result

        except Exception as e:
            # Log service errors for debugging
            print(f"Service execution error in {func.__name__}: {e}")
            # Re-raise to maintain error handling in calling code
            raise

    @staticmethod
    async def execute_multiple(
        funcs_and_args: list[tuple[Callable, tuple, dict]],
    ) -> list[Any]:
        """
        Execute multiple functions concurrently

        Args:
            funcs_and_args: List of (func, args, kwargs) tuples

        Returns:
            List of results in the same order
        """
        tasks = []

        for func, args, kwargs in funcs_and_args:
            task = BaseService.execute_async(func, *args, **kwargs)
            tasks.append(task)

        # Execute all concurrently and return results
        return await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def validate_arguments(**validators) -> dict[str, Any]:
        """
        Common argument validation helper

        Args:
            **validators: Field name -> validation callable mappings

        Returns:
            Dict with validation results and errors
        """
        errors = []
        warnings = []

        for field_name, validator in validators.items():
            try:
                error = validator(field_name)
                if error:
                    errors.append(error)
            except Exception as e:
                errors.append(f"Validation error for {field_name}: {e}")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    @staticmethod
    def create_error_response(error_message: str, **additional_data) -> dict[str, Any]:
        """
        Standard error response format

        Args:
            error_message: Main error message
            **additional_data: Additional fields to include

        Returns:
            Standardized error response
        """
        return {
            "success": False,
            "error": error_message,
            "timestamp": None,  # Could add timestamp if needed
            **additional_data,
        }

    @staticmethod
    def create_success_response(
        data: Any = None, message: str = None
    ) -> dict[str, Any]:
        """
        Standard success response format

        Args:
            data: Success data payload
            message: Optional success message

        Returns:
            Standardized success response
        """
        response = {"success": True}

        if data is not None:
            response["data"] = data

        if message:
            response["message"] = message

        return response

    @staticmethod
    def log_service_call(service_name: str, operation: str, **context):
        """
        Standard service call logging

        Args:
            service_name: Name of the service
            operation: Operation being performed
            **context: Additional context to log
        """
        context_str = " ".join(f"{k}={v}" for k, v in context.items())
        print(f"SERVICE {service_name}.{operation}: {context_str}")

    @staticmethod
    async def retry_async(
        func: Callable[..., Any],
        *args,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs,
    ) -> Any:
        """
        Execute function with retry logic for transient failures

        Args:
            func: Function to retry
            *args: Positional arguments
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            **kwargs: Keyword arguments

        Returns:
            Result of successful function execution
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return await BaseService.execute_async(func, *args, **kwargs)

            except Exception as e:
                last_exception = e

                if attempt < max_retries:
                    await asyncio.sleep(
                        retry_delay * (attempt + 1)
                    )  # Exponential backoff
                    print(f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}")
                else:
                    print(f"Final retry failed for {func.__name__}: {e}")
                    raise e

        # This should never be reached, but just in case
        raise last_exception

    async def close(self):
        """
        Cleanup method for service shutdown

        Should be called when the application is shutting down
        """
        if hasattr(self._executor, "shutdown"):
            self._executor.shutdown(wait=False)
