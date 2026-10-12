# SIM Cards Backend

FastAPI backend for the SIM Stock & Sales Tracking Platform.

## Setup

### Local Development

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -e .
```

3. Copy environment variables:
```bash
cp ../.env.example .env
# Edit .env with your configuration
```

4. Start PostgreSQL and Redis (using Docker Compose):
```bash
cd ..
docker-compose up postgres redis
```

5. Run database migrations (when implemented):
```bash
alembic upgrade head
```

6. Start the API server:
```bash
cd backend
uvicorn simcards_backend.main:app --reload --host 0.0.0.0 --port 8000
```

7. Start Celery worker (in a separate terminal):
```bash
cd backend
celery -A simcards_backend.celery_app worker --loglevel=info
```

### Docker Development

Start all services:
```bash
docker-compose up
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

## Project Structure

```
backend/
├── src/
│   └── simcards_backend/
│       ├── api/           # API endpoints
│       ├── core/          # Core functionality (config, DB, logging)
│       ├── models/        # SQLAlchemy models
│       ├── tasks/         # Celery background tasks
│       ├── main.py        # FastAPI application entry point
│       └── celery_app.py  # Celery configuration
├── pyproject.toml         # Python dependencies
├── Dockerfile            # Docker image definition
└── README.md             # This file
```

## Development Tools

### Code Quality
```bash
# Run linter
ruff check src/

# Format code
ruff format src/

# Type checking
mypy src/
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string for Celery
- `SECRET_KEY`: JWT signing key
- `ENVIRONMENT`: development/staging/production
