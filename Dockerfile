# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e

# Pin both the release and manifest digest. Updating a base image is therefore an
# explicit, reviewable dependency update instead of an implicit rebuild change.
ARG PYTHON_IMAGE=python:3.13.14-slim-trixie@sha256:9662417aace5ae7b8e2609cce472b72a8958e134ba372808abe9cc1a0c0125e6
ARG NGINX_IMAGE=nginx:1.31.3-alpine3.24@sha256:4a73073bd557c65b759505da037898b61f1be6cbcc3c2c3aeac22d2a470c1752

FROM ${PYTHON_IMAGE} AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app


# Install production dependencies in an isolated environment. The lock file is
# copied before source code, so normal code edits cannot invalidate this layer.
FROM python-base AS python-dependencies

RUN python -m venv "${VIRTUAL_ENV}"

COPY --link requirements.txt ./

RUN --mount=type=cache,id=ensalamento-pip-production,target=/root/.cache/pip,sharing=locked \
    python -m pip install \
        --require-hashes \
        --no-deps \
        --no-compile \
        --only-binary=:all: \
        --requirement requirements.txt


# Documentation has its own dependency set and native build libraries. Neither
# is copied into the application image.
FROM python-base AS docs-builder

ARG DEBIAN_SNAPSHOT=20260807T000000Z

ENV VIRTUAL_ENV=/opt/docs-venv \
    PATH="/opt/docs-venv/bin:${PATH}" \
    ENABLE_PDF_EXPORT=1

RUN --mount=type=cache,id=ensalamento-apt-lists,target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=ensalamento-apt-cache,target=/var/cache/apt,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean \
    && sed -i \
        -e "s|http://deb.debian.org/debian-security|https://snapshot.debian.org/archive/debian-security/${DEBIAN_SNAPSHOT}|g" \
        -e "s|http://deb.debian.org/debian|https://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT}|g" \
        /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Check-Valid-Until=false update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends --yes \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        shared-mime-info

RUN python -m venv "${VIRTUAL_ENV}"

COPY --link requirements-docs.txt ./

RUN --mount=type=cache,id=ensalamento-pip-docs,target=/root/.cache/pip,sharing=locked \
    python -m pip install \
        --require-hashes \
        --no-deps \
        --no-compile \
        --only-binary=:all: \
        --requirement requirements-docs.txt

COPY --link mkdocs.yml ./
COPY --link docs-manual/ ./docs-manual/

RUN mkdocs build


FROM python-base AS production

ENV HOME=/tmp

RUN groupadd --gid 10001 --system streamlit \
    && useradd --uid 10001 --gid streamlit --no-create-home --shell /usr/sbin/nologin streamlit \
    && install -d --owner=streamlit --group=streamlit \
        /app/data \
        /app/static \
        /app/.streamlit \
    && ln -s /app/data/logs /app/logs

COPY --link --from=python-dependencies /opt/venv /opt/venv

# Copy only runtime files. In particular, .env, Streamlit secrets, tests,
# generated data, and development tooling never enter the production image.
COPY --link --chown=10001:10001 src/ ./src/
COPY --link --chown=10001:10001 pages/ ./pages/
COPY --link --chown=10001:10001 static/ ./static/
COPY --link --chown=10001:10001 docs/*.csv ./docs/
COPY --link --chown=10001:10001 .streamlit/config.toml ./.streamlit/config.toml
COPY --link --chown=10001:10001 \
    "0_🔓_Login.py" \
    init_db.py \
    load_historical_allocations.py \
    ./
COPY --link --chmod=0755 --chown=10001:10001 docker-entrypoint.sh ./
COPY --link --chown=10001:10001 --from=docs-builder /app/docs-site/ ./docs-site/

USER 10001:10001

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=5)"]

ENTRYPOINT ["/app/docker-entrypoint.sh"]

CMD ["streamlit", "run", "0_🔓_Login.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--server.enableCORS=false", \
    "--server.enableXsrfProtection=false", \
    "--browser.gatherUsageStats=false"]


FROM ${NGINX_IMAGE} AS docs

COPY --link --from=docs-builder /app/docs-site/ /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
