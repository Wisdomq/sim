FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        redis-server \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz-subset0 \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml ./
COPY backend/src/ src/
COPY backend/alembic.ini ./
COPY backend/alembic/ alembic/

RUN pip install --no-cache-dir -e .

COPY infra/cloudflare/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV UPLOAD_DIR=/app/uploads

EXPOSE 8000

CMD ["/entrypoint.sh"]
