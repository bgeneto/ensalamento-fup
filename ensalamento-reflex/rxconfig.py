"""Reflex application configuration."""

import reflex as rx

# Application configuration
config = rx.Config(
    app_name="ensalamento_reflex",
    # Database configuration - using existing Streamlit database
    db_url="sqlite:///ensalamento.db",
    # Development settings
    loglevel=rx.constants.LogLevel.INFO,
    host="0.0.0.0",
    # Disable default plugins to avoid warnings
    disable_plugins=[
        "reflex.plugins.sitemap.SitemapPlugin",
    ],
    # Disable auto-reload in production
    reload=True,
)
