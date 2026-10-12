# Ops — Backup & restore

## What to back up

1. **PostgreSQL `simcards` database** (users, dealers, stock, sales, recon,
   flags, notifications, snapshots, files metadata).
2. **`UPLOAD_DIR`** — pick-list PDFs, Safaricom xlsx reports, generated report
   PDFs (local: `backend/uploads/`; K3s: the `simcards-uploads` PVC; S3 bucket
   if the S3 config is enabled). Restoring the DB alone will leave dangling
   `file_reference` paths.

## Backup (automated)

Local dev:

```bash
# env-var credentials from docker-compose.yml
PGPASSWORD=simcards_password pg_dump -h localhost -U simcards_user -d simcards \
  -Fc -f /backups/simcards_$(date +%Y%m%d_%H%M%S).dump
cp -a backend/uploads/. /backups/uploads_$(date +%Y%m%d_%H%M%S)/
```

K3s:

```bash
kubectl -n simcards exec deploy/simcards-postgres -- \
  pg_dump -U simcards_user -d simcards -Fc \
  > /backups/simcards_k8s_$(date +%Y%m%d_%H%M%S).dump

# uploads PVC via a velero/restic-style backup, or rsync the PVC mount
```

Schedule: nightly at 02:00 local (cron/systemd-timer or k8s CronJob) +
weekly full. Retention: 14 daily, 8 weekly, 12 monthly. Test a restore into a
throwaway database monthly (DR drill) before relying on it.

Compression tip: pipe through `gzip -9` if not using `-Fc` (custom format
already compresses).

## Restore

Normalize the SQLAlchemy URL for the target DB, then:

```bash
# 1) stop traffic (K3s: scale api down or use the ingress; dev: stop uvicorn)
# 2) recreate an empty target database
PGPASSWORD=simcards_password dropdb -h localhost -U simcards_user simcards --if-exists
PGPASSWORD=simcards_password createdb -h localhost -U simcards_user simcards

# 3) restore into it
pg_restore -h localhost -U simcards_user -d simcards --no-owner \
  /backups/simcards_20260921_020000.dump

# 4) restore uploads to the same relative paths used in file_reference rows
rsync -a /backups/uploads_20260921_020000/ backend/uploads/

# 5) verify
curl -s localhost:8000/health   # expect {"status":"healthy",...}
# sanity: log in as HQ and confirm a known recon import returns rows
```

**PITR (point-in-time recovery):** enable WAL archiving (`archive_mode=on`,
`archive_command`) or use a managed provider (RDS/Aurora/Cloud SQL) so you can
recover to just before a bad migration/script. Without PITR you restore to the
last nightly dump and lose the day's changes.

## Rollback after a bad release

If a deploy/migration is bad and you kept the pre-migration dump:

```bash
# 1) offboard traffic
# 2) restore the pre-migration DB dump (above)
# 3) downgrade file storage too (uploads from the matching backup timestamp)
# 4) ship the previous image/tag, run `alembic downgrade -1` if schema differs
```

Prefer "forward-fix" (new migration) over downgrade for schema; keep this
runbook for the worst case.