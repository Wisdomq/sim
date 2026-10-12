# Deployment-level changes (X-13-05)

Everything that must be **supplied or edited at deploy time** — secrets, env
vars, config placeholders and release flags — as opposed to code. Nothing here
is in the repo today. Keep this open while still in dev; work through it when
the first real deploy happens.

Code is already wired for all of it: `backend/src/simcards_backend/core/config.py`
reads every value below, `infra/cloudflare/src/index.ts` forwards them into the
container, `web/src/lib/api.ts:12` needs nothing (relative `/api/v1`).

---

## 1. Accounts & plan prerequisites

| What | Why | Notes |
|------|-----|-------|
| Cloudflare account | hosts Worker + container | **Workers Paid ($5/mo) is required** — Containers do not run on the free plan (includes 25 GiB-h memory / 375 vCPU-min / 200 GB-h disk) |
| Postgres 17 instance | the app's datastore | Neon free tier is fine; direct (non-`-pooler`) URL for migrations, pooled URL for the app |
| Google account + 2-Step Verification | SMTP for password-reset emails | Without 2-Step Verification, `myaccount.google.com/apppasswords` does not offer app passwords |
| Docker + Node 22 | image build / wrangler | container image must be `linux/amd64`; wrangler cross-builds on Apple Silicon |

---

## 2. Secrets

Never commit these. Local → `backend/.env` (git-ignored). Cloudflare →
`npx wrangler secret put <NAME>`.

| Name | Read at | Generate with |
|------|---------|---------------|
| `SECRET_KEY` | `config.py:24` | `openssl rand -hex 32` |
| `DATABASE_URL` | `config.py:18` | Neon connection string (`postgresql://user:pass@host/db?sslmode=require`) |
| `SMTP_USER` | `config.py:47` | your Gmail address |
| `SMTP_PASSWORD` | `config.py:48` | 16-char Google app password (spaces are fine, they are stripped by Gmail) |

`SMTP_PASSWORD` is the only true secret in the Gmail flow — it is only ever
read at runtime and never logged (`email.py:78` logs the recipient, not
credentials).

---

## 3. Local dev `.env` (`backend/.env`)

Copy `.env.example` → `backend/.env` and replace the placeholders. Values that
differ from the example in practice:

```bash
ENVIRONMENT=development            # keeps Base.metadata.create_all (main.py:27)
DEBUG=true                         # SQL echo on; flip to false once stable

DATABASE_URL=postgresql://simcards_user:simcards_password@localhost:5432/simcards
SECRET_KEY=<openssl rand -hex 32>

# Comma-separated is the documented format (.env.example:20, infra/k3s/configmap.yaml:15)
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Password-reset links: {FRONTEND_URL}/reset-password?token=…  (email.py:66)
# 3000 matches web/vite.config.ts:8 exactly — change only if you move the Vite port.
FRONTEND_URL=http://localhost:3000

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<your-email>@gmail.com
SMTP_PASSWORD=<16-char app password>
SMTP_FROM=<your-email>@gmail.com     # Gmail sends as the authenticated account regardless
SMTP_USE_TLS=true
```

Unset SMTP ⇒ `email.py:44-46` logs `Email service not configured - skipping
email send` and the API still returns 200 (anti-enumeration). The flow *looks*
successful but **no mail arrives** — this is the current state.

Leave `ALGORITHM`, token expiry and rate-limit values at their defaults unless
you are deliberately tuning them.

---

## 4. Cloudflare config to edit

`infra/cloudflare/wrangler.jsonc`:

```jsonc
// currently placeholders — replace after the first deploy tells you the URL
"vars": {
  "CORS_ORIGINS":  "https://simcards.<your-subdomain>.workers.dev",
  "FRONTEND_URL":  "https://simcards.<your-subdomain>.workers.dev"
}
```

Both must be the **same origin** as the SPA, because the web app is served from
the same Worker (`assets` + `run_worker_first` on `/api/*`).

Add SMTP vars only if you want them non-secret (`SMTP_HOST`, `SMTP_PORT`,
`SMTP_USE_TLS`, `SMTP_FROM`); `SMTP_USER` and `SMTP_PASSWORD` should be
secrets. `src/index.ts:40-56` already forwards any of these that are set and
silently omits empties.

Per-deploy command list (Neon setup, migrations, `wrangler deploy`, APK build)
is planned for `cloudflare-deploy.md` — this file is only *what* must change.

---

## 5. Environment switch at deploy time

| | dev | deploy |
|---|---|---|
| `ENVIRONMENT` | `development` | `production` — **hard-coded** in `src/index.ts:32` |
| `DEBUG` | `true` | `false` (also set in `src/index.ts:33`) |
| schema | `Base.metadata.create_all` runs at startup (`main.py:27`) | skipped → **`alembic upgrade head` is mandatory before first traffic** |

The RLS `app.current_dealer_id` policies are created **only** by the alembic
migrations, never by `create_all` — a production DB that was only touched by
`create_all` would run without tenant isolation. Never skip this step.

---

## 6. Mobile release flag

Debug builds default to `http://10.0.2.2:8000/api/v1` (`api_config.dart`) —
that is Android-emulator-only, and **release builds block cleartext HTTP**, so
the deployed URL must be passed at build time:

```bash
flutter build apk --release --split-per-abi \
  --dart-define=API_BASE_URL=https://<sub>.workers.dev/api/v1
```

Build this *after* the backend is deployed — the URL is compile-time
(`String.fromEnvironment`), not runtime. Packaging/keystore steps:
`docs/play-store-prep.md`.

---

## 7. Accepted deployment-level limitations

| Limitation | Cause | Mitigation |
|---|---|---|
| Uploaded files vanish on container sleep | container disk is ephemeral (`UPLOAD_DIR=/app/uploads`) | mount R2 (not implemented) or treat uploads as non-durable |
| Daily Celery beat jobs effectively never fire | beat's 24h schedule restarts from zero on every cold start | `sleepAfter = "1h"` in `src/index.ts:46` keeps it warm; real periodic jobs need a cron trigger |
| Single API instance | `max_instances: 1` in `wrangler.jsonc` | raise only after checking Neon connection limits |
| No custom domain | free `*.workers.dev` chosen for now | add a domain + `routes` to `wrangler.jsonc` when ready |
| No k8s parity check | `infra/k3s/` remains an alternative path, untested against these changes | re-verify `configmap.yaml` (comma `CORS_ORIGINS`) before any K3s deploy |

---

## 8. Do not change

- **Web app code** — relative `/api/v1` baseURL already works same-origin.
- **Password-reset URL paths** — backend (`/api/v1/auth/*`), web and mobile are
  aligned; don't reintroduce an unprefixed router.
- **DB driver pin** — `backend/pyproject.toml` must carry `sqlalchemy<2.1`
  (pending, see §9); SQLAlchemy 2.1 resolves `postgresql://` to psycopg v3 and
  the container only ships psycopg2, which crashes the image at import time.
- **Signing/keystore** — handled in `docs/play-store-prep.md`, not here.

---

## 9. Pending code work that blocks a deploy

Not deployment-level, but a deploy cannot succeed until these land:

1. **`backend/pyproject.toml`**: `sqlalchemy>=2.0.0` → `sqlalchemy>=2.0.0,<2.1`.
   The Docker image installs SQLAlchemy 2.1.3 fresh, where `postgresql://`
   resolves to `PGDialect_psycopg` (psycopg v3) → `ModuleNotFoundError: No
   module named 'psycopg'` during `alembic upgrade head`. Local `.venv` is
   2.0.52 (psycopg2) so this only bites the container.
2. **Container end-to-end retest** after (1): throwaway Postgres, comma
  -separated `CORS_ORIGINS` (proves the `NoDecode` fix in
   `config.py:34-39` works in-container), then `/health`, the three
   `/api/v1/auth/*password*` routes, and `celery inspect ping`.
3. **`docs/ops/cloudflare-deploy.md`** — the step-by-step runbook
   (`(X-13-06)`), written last so its commands match verified reality.
