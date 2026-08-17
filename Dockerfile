FROM node:24-alpine AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim

ARG FINANCE_RELEASE_VERSION=development
ARG FINANCE_COMMIT_SHA=unknown
ARG FINANCE_BUILD_DATE=unknown

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FINANCE_RELEASE_VERSION=${FINANCE_RELEASE_VERSION} \
    FINANCE_COMMIT_SHA=${FINANCE_COMMIT_SHA} \
    FINANCE_BUILD_DATE=${FINANCE_BUILD_DATE} \
    FINANCE_DATA_DIR=/app/data \
    FINANCE_BACKUP_DIR=/app/backups \
    FINANCE_UI_DIST=/app/frontend/dist \
    PORT=8000

LABEL org.opencontainers.image.title="ArthNivo" \
    org.opencontainers.image.source="https://github.com/chetan1804/arthnivo" \
    org.opencontainers.image.version=${FINANCE_RELEASE_VERSION} \
    org.opencontainers.image.revision=${FINANCE_COMMIT_SHA} \
    org.opencontainers.image.created=${FINANCE_BUILD_DATE}

WORKDIR /app

RUN groupadd --system finance \
    && useradd --system --gid finance --create-home finance \
    && apt-get update \
    && apt-get install --yes --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt ./
RUN pip install --no-cache-dir --requirement requirements-prod.txt

COPY --chown=finance:finance . .
COPY --from=frontend-build --chown=finance:finance /frontend/dist /app/frontend/dist
RUN mkdir -p /app/data /app/backups && chown finance:finance /app/data /app/backups

USER finance

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; request=urllib.request.Request('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/ready', headers={'X-Forwarded-Proto':'https'}); urllib.request.urlopen(request, timeout=3)"

CMD ["sh", "-c", "python -m uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips \"${FINANCE_FORWARDED_ALLOW_IPS:-127.0.0.1}\""]
