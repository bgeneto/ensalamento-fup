"""
Error handling utilities for Sistema de Ensalamento FUP/UnB
Provides consistent error handling and logging across the application
"""

import streamlit as st
import logging
import traceback
from typing import Callable, Any, Optional
from functools import wraps

# Setup logger
logger = logging.getLogger(__name__)


class DatabaseErrorHandler:
    """Handles database-related errors with enhanced logging"""

    @staticmethod
    def is_detached_instance_error(error: Exception) -> bool:
        """Check if error is a DetachedInstance/session error"""
        error_str = str(error)
        error_type = type(error).__name__

        detached_patterns = [
            "DetachedInstance",
            "detached",
            "not bound to a Session",
            "object is being detached",
            "Unexpected state",
        ]

        return any(
            pattern in error_str or pattern in error_type
            for pattern in detached_patterns
        )

    @staticmethod
    def log_database_error(error: Exception, context: str = "") -> None:
        """Log database error with full traceback"""
        error_type = type(error).__name__
        error_msg = str(error)
        full_traceback = traceback.format_exc()

        logger.error(f"Database Error in {context}")
        logger.error(f"  Type: {error_type}")
        logger.error(f"  Message: {error_msg}")
        logger.error(f"  Traceback:\n{full_traceback}")

    @staticmethod
    def display_database_error(
        error: Exception, action: str = "carregar dados"
    ) -> None:
        """Display user-friendly database error message"""
        is_detached = DatabaseErrorHandler.is_detached_instance_error(error)
        error_type = type(error).__name__

        if is_detached:
            st.error("❌ Erro na conexão com o banco de dados.")
            st.info("📊 **Para resolver este problema:**")
            st.markdown("1. **Atualize a página** (pressione F5)")
            st.markdown("2. **Limpe o cache do navegador** se o problema persistir")
            st.markdown("3. **Feche e reabra o navegador** se necessário")
            if st.button("🔄 Atualizar Página Agora", type="primary"):
                st.rerun()
        else:
            st.error(f"❌ Erro ao {action}.")
            st.warning("Entre em contato com o administrador se o problema persistir.")

        # Debug details for developers
        with st.expander("ℹ️ Detalhes técnicos (para desenvolvedor)"):
            st.code(
                f"Tipo: {error_type}\n"
                f"Mensagem: {str(error)}\n"
                f"Contexto: {action}"
            )

    @staticmethod
    def display_generic_error(error: Exception, context: str = "") -> None:
        """Display generic error message"""
        st.error("❌ Erro crítico na aplicação.")
        st.error("Por favor, recarregue a página ou contate o administrador.")

        with st.expander("ℹ️ Detalhes do erro"):
            st.code(
                f"Tipo: {type(error).__name__}\n"
                f"Mensagem: {str(error)}\n"
                f"Contexto: {context}"
            )


def handle_database_errors(context: str = ""):
    """
    Decorator to handle database errors in functions
    Usage: @handle_database_errors("loading users")
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log the error with full context
                DatabaseErrorHandler.log_database_error(
                    e, f"{func.__name__} - {context}"
                )

                # Display appropriate error message
                if DatabaseErrorHandler.is_detached_instance_error(e):
                    DatabaseErrorHandler.display_database_error(
                        e, f"ao executar {context or func.__name__}"
                    )
                else:
                    DatabaseErrorHandler.display_generic_error(
                        e, f"{func.__name__} - {context}"
                    )

                return None

        return wrapper

    return decorator


def safe_execute_with_logging(
    func: Callable, context: str = "", *args, **kwargs
) -> Any:
    """
    Safely execute a function with error logging
    Returns None if error occurs
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        DatabaseErrorHandler.log_database_error(e, context)
        DatabaseErrorHandler.display_database_error(e, context)
        return None
