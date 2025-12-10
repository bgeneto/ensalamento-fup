# Multi-stage Dockerfile for Ensalamento FUP/UnB System
# Base image: Python 3.13 slim
# Optimized for caching and production deployment

# Stage 1: Base setup with dependencies
FROM python:3.13-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    sqlite3 \
    curl \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install mkdocs-material

# Stage 3: Production application
FROM base AS production

# Create non-root user for security
RUN groupadd -r streamlit && \
    useradd -r -g streamlit streamlit

# Copy application code
COPY --chown=streamlit:streamlit . .

# Build documentation (HTML + PDF)
ENV ENABLE_PDF_EXPORT=1
RUN mkdocs build

# Create necessary directories and set permissions
RUN mkdir -p /app/data /app/static && \
    chown -R streamlit:streamlit /app

# Switch to non-root user
USER streamlit

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Default command to run Streamlit
CMD ["streamlit", "run", "0_🔓_Login.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--server.enableCORS=false", \
    "--server.enableXsrfProtection=false", \
    "--browser.gatherUsageStats=false"]

# Stage 4: Documentation Server (Nginx)
FROM nginx:alpine AS docs
COPY --from=production /app/docs-site /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
