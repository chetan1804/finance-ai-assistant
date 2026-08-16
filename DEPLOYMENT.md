# Deployment

The application ships as one multi-stage container. Node builds the React
frontend, then FastAPI serves the compiled frontend and authenticated API from
the Python runtime image. Finance, authentication data, and LangGraph
checkpoints can use PostgreSQL. Local and single-instance deployments retain
SQLite as the default.

## Production requirements

- Python 3.12 or the provided Docker image
- A persistent volume mounted at `/app/data`
- One application process and one running instance while SQLite storage or the
  in-memory rate limiter is in use
- HTTPS supplied by the hosting platform or reverse proxy
- `GROQ_API_KEY` configured as a secret
- `FINANCE_REDIS_URL` configured for any multi-process or multi-replica release

Never bake `.env`, database files, API tokens, or provider keys into an image.

## Deploy with Docker Compose

Create `.env` from `.env.example` and set the provider key:

```bash
docker compose build
docker compose up -d
```

Create the first profile from the React registration screen. The optional
`scripts.bootstrap_user` and `FINANCE_API_TOKENS` flow remains available only
for importing an older local deployment.

Verify the deployment:

```bash
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/ready
docker compose ps
```

Open `http://127.0.0.1:8000/` and enter the generated bearer token.

## Managed container platforms

Use the repository `Dockerfile` and configure:

- Liveness path: `/health`
- Readiness and platform health-check path: `/ready`
- Prometheus scrape path: `/metrics`
- Container port: the platform-provided `PORT`, falling back to `8000`
- Persistent volume mount: `/app/data`
- Secret: `GROQ_API_KEY`
- Instance count: `1`

Set the following production security values:

```text
FINANCE_ENVIRONMENT=production
FINANCE_ALLOWED_HOSTS=finance.example.com
FINANCE_HTTPS_REDIRECT=true
FINANCE_FORWARDED_ALLOW_IPS=127.0.0.1
```

Replace the forwarded-IP value with the exact proxy IP addresses or networks
that connect to the container. Never use `*` unless the container is network
isolated so that only a trusted proxy can reach it. Uvicorn ignores forwarded
scheme and client headers from other addresses.

If the React application is served from a different origin, configure exact
origins without paths:

```text
FINANCE_CORS_ORIGINS=https://app.example.com
```

Same-origin deployments should leave `FINANCE_CORS_ORIGINS` unset. Production
rejects wildcard allowed hosts. `FINANCE_ROOT_PATH` may be set when a proxy
publishes the application below a stripped URL prefix.

The application applies pending versioned migrations for the selected database
before startup. Users and their first accounts are created through registration.

Check a mounted database before deployment with:

```bash
python -m scripts.migrate_database --check
```

Back up both database files before releasing a new migration. Applied migration
files are checksum-protected and must never be edited.

## Storage configuration

`FINANCE_DATA_DIR` changes the directory containing both default SQLite files.
The two files can instead be configured independently:

- `FINANCE_DATABASE_URL`: PostgreSQL URL for finance and authentication data
- `FINANCE_DATABASE_PATH`: finance SQLite path when no URL is configured
- `FINANCE_CHECKPOINT_URL`: optional separate PostgreSQL checkpoint URL
- `FINANCE_CHECKPOINT_PATH`: explicit SQLite checkpoint path
- `FINANCE_REDIS_URL`: shared Redis connection for API and authentication limits

When neither checkpoint override is present, checkpoints follow
`FINANCE_DATABASE_URL` and therefore share the finance PostgreSQL database. Set
only `FINANCE_CHECKPOINT_PATH` to retain SQLite checkpoints alongside a
PostgreSQL finance database. Never configure both checkpoint overrides.

PostgreSQL pooling is configured per application process:

- `FINANCE_DB_POOL_MIN_SIZE` and `FINANCE_DB_POOL_MAX_SIZE`: finance queries
- `FINANCE_DB_POOL_TIMEOUT_SECONDS`: maximum wait for a finance connection
- `FINANCE_CHECKPOINT_POOL_MIN_SIZE` and `FINANCE_CHECKPOINT_POOL_MAX_SIZE`:
  LangGraph checkpoint operations

Multiply both maximums by the planned worker and replica count when checking the
database provider's connection limit.

## Observability configuration

The API emits JSON logs to standard output. Configure them with:

- `FINANCE_ENVIRONMENT`: deployment name included in each log record
- `FINANCE_LOG_LEVEL`: standard Python logging level, defaulting to `INFO`
- `FINANCE_LOG_FORMAT`: `json` by default; another value selects plain text

Forward `X-Request-ID` from the edge proxy when available. The application
accepts only a restricted identifier format and generates a safe replacement
otherwise. Configure Prometheus to scrape `/metrics`, and restrict that path to
the monitoring network at the gateway or platform level. Metrics use an
in-process registry, so run one Uvicorn worker per container and scale with
separately scraped replicas.

## HTTPS and proxy boundary

TLS terminates at the managed platform or reverse proxy. With
`FINANCE_HTTPS_REDIRECT=true`, the application redirects requests that Uvicorn
identifies as HTTP and sends HSTS on HTTPS responses. Correct behavior therefore
depends on an exact `FINANCE_FORWARDED_ALLOW_IPS` trust boundary. Keep the
container port private when possible and test redirects, callback URLs, and
health probes through the real proxy before release.

For a managed PostgreSQL database, store a URL such as the following in the
platform secret manager rather than committing it:

```text
postgresql://finance:password@database-host:5432/finance
```

Back up the selected finance database and the checkpoint SQLite database. Test
restoration regularly and stop application writes while taking a raw SQLite
file-level copy.

## Scaling boundary

With PostgreSQL-backed finance data and checkpoints plus `FINANCE_REDIS_URL`,
the application no longer depends on per-process state. PostgreSQL pools default
to 1–10 finance connections and 1–5 checkpoint connections per application
process. Validate total database connection capacity and load-test the target
environment before increasing worker or replica counts.
