# Ops — Runbook index (X-13-04)

| Runbook | When to open it |
|---------|-----------------|
| [backup-restore.md](backup-restore.md) | Daily schedule, DR drills, post-incident restore |
| [migrations.md](migrations.md) | Any schema change / deploy/upgrade / rollback |
| [monitoring.md](monitoring.md) | Incidents, alerting, capacity, log forensics |
| [deployment-checklist.md](deployment-checklist.md) | Before any deploy: secrets, env vars, config placeholders, release flags |

All runbooks assume a Postgres 17 database (`simcards`), Redis 7, the FastAPI
service, and Celery worker/beat. Local dev URL
`postgresql://simcards_user:simcards_password@localhost:5432/simcards`; in
K3s use the `simcards` namespace (see `infra/`).

## Golden rule
- **Back up before migrating.** Never run `alembic upgrade` without a
  pre-migration `pg_dump`.
- The single source of truth is the Postgres database; uploaded files
  (`UPLOAD_DIR`) are secondary but must be backed up in lockstep for a
  correct restore.
- Rotate `SECRET_KEY`/DB passwords via `infra/k3s/secret.yaml` (K3s) and
  never keep them in the repo.