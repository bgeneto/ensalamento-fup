"""Base service class for async wrapping of synchronous business logic."""

import asyncio
from functools import wraps
from typing import Any, Callable, Optional


class BaseService:
    """Base class for all service wrappers with async handling.

    Provides standardized patterns for wrapping synchronous business logic
    with async interfaces for Reflex compatibility.
    """

    @staticmethod
    async def execute_async(
        operation: Callable, *args, timeout: Optional[float] = 30.0, **kwargs
    ) -> Any:
        """Execute synchronous operation asynchronously in thread pool.

        Args:
            operation: Synchronous function to execute
            *args: Positional arguments for the operation
            timeout: Operation timeout in seconds (default: 30.0)
            **kwargs: Keyword arguments for the operation

        Returns:
            Result of the synchronous operation

        Raises:
            asyncio.TimeoutError: If operation exceeds timeout
            Exception: Any exception raised by the synchronous operation
        """
        return await asyncio.wait_for(
            asyncio.to_thread(operation, *args, **kwargs), timeout=timeout
        )

    @staticmethod
    def with_async_wrapper(sync_method: Callable) -> Callable:
        """Decorator to add async wrapper to synchronous service methods.

        Usage:
            @BaseService.with_async_wrapper
            def my_sync_method(self, arg1, arg2):
                # Synchronous implementation
                return result

            # Can now be called as:
            result = await my_sync_method(arg1, arg2)

        Args:
            sync_method: Synchronous method to wrap

        Returns:
            Async wrapper function
        """

        @wraps(sync_method)
        async def async_wrapper(*args, **kwargs):
            return await BaseService.execute_async(sync_method, *args, **kwargs)

        return async_wrapper

    @staticmethod
    async def execute_with_retry(
        operation: Callable,
        *args,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs
    ) -> Any:
        """Execute operation with retry logic for transient failures.

        Args:
            operation: Function to execute (sync or async)
            *args: Positional arguments
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            **kwargs: Keyword arguments

        Returns:
            Result of the operation

        Raises:
            Last exception encountered if all retries fail
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(operation):
                    return await operation(*args, **kwargs)
                else:
                    return await BaseService.execute_async(operation, *args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    await asyncio.sleep(
                        retry_delay * (2**attempt)
                    )  # Exponential backoff

        raise last_exception
