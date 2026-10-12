FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy source first: the editable install needs src/ present (egg_base).
COPY pyproject.toml ./
COPY src/ ./src/
COPY alembic.ini ./
COPY alembic/ ./alembic/
RUN pip install --no-cache-dir -e .

# Expose port
EXPOSE 8000

CMD ["uvicorn", "simcards_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
