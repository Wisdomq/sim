# Ops — Schema migrations

Alembic is wired at `backend/alembic/` (revisions:
`0001_initial_schema`, `0002_add_notifications`, `0003_add_recon_detail_index`).
The backend Dockerfile copies `alembic.ini` + `alembic/` into the image.

## Normal upgrade

```bash
cd backend
PYTHONPATH=src .venv/bin/alembic upgrade head
```

K3s:

```bash
kubectl -n simcards exec -i deploy/simcards-api -- \
  alembic -c /app/alembic.ini upgrade head
```

## Adding a new migration (development)

```bash
# autogenerate from model changes, then REVIEW the output
PYTHONPATH=src .venv/bin/alembic revision --autogenerate -m "add_<table>_column"
```

Rules:
- Review the generated file — autogenerate misses renames/type changes and can
  mis-detect defaults. Add `op.create_index`, backfills, etc. manually.
- Never edit an already-applied revision; append a new one.
- Put bulk data backfills in the migration or in the migration's `data` step
  (guard with `len < threshold` for large tables).
- Postgres is the only supported dialect; don't add DB-specific syntax that
  breaks SQLite test runs.

## Deploy checklist

1. `pg_dump` backup (see backup-restore.runbook).
2. Apply migration (`alembic upgrade head`).
3. Health check `/health` and run the X-13-02 E2E: `scripts/e2e_live.py`
   (fires the real API + Celery). Expect 35/35 PASS.
4. Rollback path ready: forward-fix migration preferred; last-resort
   DB restore documented in backup-restore.md.

## Downgrade (rare)

```bash
PYTHONPATH=src .venv/bin/alembic downgrade -1
```

Down-migrations must reverse the up-migration idempotently. Prefer not to
downgrade on big destructive changes (dropped columns lose data).