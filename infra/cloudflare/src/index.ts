import { Container, getContainer } from "@cloudflare/containers";
import { env as workerEnv } from "cloudflare:workers";

interface Env {
  SIMCARDS_API: DurableObjectNamespace<SimcardsApi>;
  ASSETS: Fetcher;
  CORS_ORIGINS: string;
  FRONTEND_URL: string;
  DATABASE_URL: string;
  SECRET_KEY: string;
  SMTP_HOST?: string;
  SMTP_PORT?: string;
  SMTP_USER?: string;
  SMTP_PASSWORD?: string;
  SMTP_FROM?: string;
  SMTP_USE_TLS?: string;
}

const API_ROUTES = ["/api", "/health", "/docs", "/redoc", "/openapi.json"];

function isApiRoute(pathname: string): boolean {
  return API_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );
}

function containerEnv(): Record<string, string> {
  const vars: Record<string, string> = {
    ENVIRONMENT: "production",
    DEBUG: "false",
    REDIS_URL: "redis://localhost:6379/0",
    UPLOAD_DIR: "/app/uploads",
    CORS_ORIGINS: workerEnv.CORS_ORIGINS,
    FRONTEND_URL: workerEnv.FRONTEND_URL,
    DATABASE_URL: workerEnv.DATABASE_URL,
    SECRET_KEY: workerEnv.SECRET_KEY,
  };

  // Optional SMTP: if unset, password-reset emails are silently skipped.
  for (const key of [
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "SMTP_FROM",
    "SMTP_USE_TLS",
  ] as const) {
    const value = workerEnv[key];
    if (value) vars[key] = value;
  }

  return vars;
}

export class SimcardsApi extends Container<Env> {
  defaultPort = 8000;
  // Keep the API warm for an hour so in-flight Celery tasks are not killed.
  sleepAfter = "1h";
  envVars = containerEnv();
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const { pathname } = new URL(request.url);

    if (isApiRoute(pathname)) {
      const container = getContainer(env.SIMCARDS_API, "default");
      // Cold start runs redis + alembic before uvicorn binds 8000, so allow
      // well beyond the default port-ready window.
      await container.startAndWaitForPorts({
        ports: [8000],
        cancellationOptions: { portReadyTimeoutMS: 120_000 },
      });
      return container.fetch(request);
    }

    // Everything else is served by the SPA (index.html fallback included).
    return env.ASSETS.fetch(request);
  },
};
