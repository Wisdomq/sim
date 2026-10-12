# K3s deployment manifests (X-13-03)

Production-style manifests for running the SIMCARDS stack on a single-node
K3s cluster. The same images run in the dev `docker-compose.yml`.

## Components

| Component     | Manifests      | Notes                                                            |
|---------------|----------------|------------------------------------------------------------------|
| API (FastAPI) | `api.yaml`     | 2 replicas, `/health` probes; `uvicorn --workers 2`              |
| Web (React)   | `web.yaml`     | nginx static host; proxies `/api` and `/health` to the API       |
| Celery worker | `worker.yaml`  | runs imports / reports / exports / scheduled inactivity flags    |
| Celery beat   | `worker.yaml`  | single pod; drives the daily schedule                            |
| PostgreSQL 17 | `postgres.yaml`| StatefulSet + 10Gi RWO PVC                                       |
| Redis 7       | `redis.yaml`   | broker + rate-limit + token revoke store                         |
| Ingress       | `ingress.yaml` | Traefik; `/api` → API svc, `/` → web svc (TLS via cert-manager) |

Shared uploads: the API writes imported pick-lists/Safaricom files, the worker
reads them and writes generated report PDFs, and the API serves them. The
`simcards-uploads` PVC therefore needs **ReadWriteMany** (Traefik/Longhorn/NFS/
CIFS CSI). Alternatively set the commented `AWS_*`/`S3_*` configmap values to
move file storage to S3-compatible object storage (the app checks
`S3_BUCKET` at runtime).

## Build & push images

```bash
# backend image
docker build -t ghcr.io/simcards/backend:latest ./backend
docker push ghcr.io/simcards/backend:latest

# web image (build-time VITE_API_BASE defaults to /api, proxied by nginx)
docker build -t ghcr.io/simcards/web:latest ./web
docker push ghcr.io/simcards/web:latest
```

Create `registry-credentials` for the private registry, or remove
`imagePullSecrets` if images are public:

```bash
kubectl create secret docker-registry registry-credentials \
  --docker-server=ghcr.io \
  --docker-username=<user> \
  --docker-password=<token> \
  -n simcards
```

## Apply

```bash
# edit infra/k3s/secret.yaml first (use openssl rand -hex 32 for SECRET_KEY)
kubectl apply -k infra/k3s
kubectl -n simcards rollout status deployment/simcards-api
kubectl -n simcards get pods
```

Migrate schema on first boot (or run every deployment):

```bash
kubectl -n simcards exec -it deploy/simcards-api -- \
  alembic -c /app/alembic.ini upgrade head
```

## Ingress / TLS

Replace `simcards.example.com` in `ingress.yaml`, point a DNS A record at the
cluster LoadBalancer, then uncomment the `tls:` block and add a
`ClusterIssuer` (the cert-manager annotation is already in place).

## Using an external PostgreSQL / Redis (managed cloud)

Delete `postgres.yaml` and `redis.yaml`, then edit `configmap.yaml`:

```yaml
DATABASE_URL: postgresql://user:pass@cloud-host:5432/simcards
REDIS_URL: redis://cloud-host:6379/0
```

Running with `kubectl apply -k infra/k3s` (Kustomize removes the deleted
resources from the build set).