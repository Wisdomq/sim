#!/bin/sh
set -eu

UPLOAD_DIR="${UPLOAD_DIR:-/app/uploads}"
mkdir -p "$UPLOAD_DIR"

echo "[entrypoint] starting redis"
redis-server --daemonize yes --bind 127.0.0.1 --port 6379 --save '' --appendonly no --dir /tmp
attempt=0
until redis-cli ping >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "[entrypoint] redis failed to start" >&2
    exit 1
  fi
  sleep 1
done

echo "[entrypoint] running database migrations"
attempt=0
until alembic -c /app/alembic.ini upgrade head; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 5 ]; then
    echo "[entrypoint] migrations failed after $attempt attempts" >&2
    exit 1
  fi
  echo "[entrypoint] migration attempt $attempt failed, retrying in 5s"
  sleep 5
done

echo "[entrypoint] starting api"
uvicorn simcards_backend.main:app --host 0.0.0.0 --port 8000 --workers 1 &
API_PID=$!

echo "[entrypoint] starting celery worker"
celery -A simcards_backend.celery_app worker --loglevel=info --concurrency=2 &
WORKER_PID=$!

echo "[entrypoint] starting celery beat"
celery -A simcards_backend.celery_app beat --loglevel=info --pidfile=/tmp/celerybeat.pid &
BEAT_PID=$!

shutdown() {
  echo "[entrypoint] shutting down"
  kill "$BEAT_PID" "$WORKER_PID" "$API_PID" 2>/dev/null || true
}
trap shutdown TERM INT

while kill -0 "$API_PID" 2>/dev/null; do
  sleep 5
done

echo "[entrypoint] api process exited" >&2
exit 1
