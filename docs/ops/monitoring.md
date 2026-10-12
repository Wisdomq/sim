# Ops — Monitoring & logging

## Health endpoints

- `GET /health` — liveness/readiness for the API (K8s probes use it).
- API `/api/v1/...` route families: `stock`, `reconciliation`, `commission`,
  `reports`, `flags`, `brand-ambassadors`, `branches`, `auth`, `onboarding`.

## Existing telemetry hooks (what to enable)

The app already:
- Writes an audit log via `services/audit.py` (`write_audit_log`).
- Creates `AccountFlag` + `Notification` on BA/branch inactivity (Celery beat,
  daily).
- Rate-limits logins (`LOGIN_RATE_LIMIT_ATTEMPTS`, `LOGIN_RATE_LIMIT_WINDOW_SECONDS`)
  and clear the limiter on successful login.
- Returns structured Celery task status from import/export endpoints
  (`task_id`, then poll the resource until COMPLETED).

Integration points to plug in:
- **Structured request logging**: add a FastAPI middleware logging
  `method path status duration_ms user_id role`; ship to
  Loki/Cloudwatch/ELK. Log nothing sensitive (no password hashes, no tokens).
- **Celery observability**: `inflight`/`reserved` queues via
  `celery -A simcards_backend.celery_app inspect active`; alert if import /
  report queues back up (Redis `LLEN` on the queue keys).
- **Errors to Sentry**: init `sentry_sdk` in `main.py` reading a
  `SENTRY_DSN` env var (config has `extra="ignore"` so add the field to
  `Settings` first).

## Operational playbooks

### "Recon import stuck PROCESSING"
1. `kubectl -n simcards logs deploy/simcards-celery-worker --tail=200` (or
   `tail -f /tmp/simcards_celery.log` in dev) and look for task errors.
2. Confirm Redis is healthy (`redis-cli ping`) — the broker is required.
3. If the worker crashed, restart the worker Deployment; pending messages are
   safe in Redis and will redeliver.
4. Never re-upload the same `report_date` blindly — the import may
   409-duplicate; prefer retrying the failed task.

### Export/upload files missing
Files live under `UPLOAD_DIR`. API + worker must share that storage (K3s:
the `simcards-uploads` RWX PVC; S3 when configured). A symptom of split
storage is "export PROCESSING forever" or "Not found" on a known
`file_reference`.

### Login spikes / rate-limit lockouts
`LOGIN_RATE_LIMIT_ATTEMPTS=10` per email per 60s. "account locked" support
interactions: check Redis keys for that email; confirm not a password-compromise
brute force before clearing.

### Performance snapshot looks 0%
Snapshots match on exact `(period_type, period_start, period_end)`. A custom
Dashboard range that doesn't match a snapshot returns 0/blank — seed or
backfill the snapshot for the range, or use period computing like the
`scripts/seed_demo.py` (see X-13-01).

## Capacity & retention

- Postgres: retain audit/log tables trimmed via nightly job
  (`DELETE FROM audit_logs WHERE created_at < now() - interval '180 days'`
  with confirmation).
- Uploads: move older reconciled exports to cold storage (S3 IA/Glacier).
- Redis: small by design (rate-limits, broker, revoke); monitor memory, set
  `maxmemory` + `allkeys-lru`.

## Alerting thresholds (starter Prometheus rules)

| Signal | Threshold |
|--------|-----------|
| `/health` probe failure | 3 consecutive / 5 min |
| Celery queue backlog | > 50 pending tasks for 5 min |
| API 5xx rate | > 2% of requests over 10 min |
| Postgres connections | > 80% of `max_connections` |
| Login success rate dip | deviates > 3σ daily baseline |