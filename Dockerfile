FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FINANCE_DATA_DIR=/app/data \
    PORT=8000

WORKDIR /app

RUN groupadd --system finance \
    && useradd --system --gid finance --create-home finance

COPY requirements-prod.txt ./
RUN pip install --no-cache-dir --requirement requirements-prod.txt

COPY --chown=finance:finance . .
RUN mkdir -p /app/data && chown finance:finance /app/data

USER finance

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/health', timeout=3)"

CMD ["sh", "-c", "python -m uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
