# Deployment

The application ships as one multi-stage container. Node builds the React
frontend, then FastAPI serves the compiled frontend and authenticated API from
the Python runtime image. Finance, authentication data, and LangGraph
checkpoints can use PostgreSQL. Local and single-instance deployments retain
SQLite as the default.

## Production requirements

- Python 3.12 or the provided Docker image
- A persistent volume mounted at `/app/data`
- A separate persistent or object-storage-backed location for `/app/backups`
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
curl --fail http://127.0.0.1:8000/version
docker compose ps
```

Open `http://127.0.0.1:8000/` and enter the generated bearer token.

For managed production deployments, prefer an immutable GHCR digest generated
by the version-tag release workflow over rebuilding source at deploy time. See
`RELEASE.md` for publication, attestation verification, and rollback guidance.

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

Create and verify a backup before releasing a new migration. Applied migration
files are checksum-protected and must never be edited.

## Storage configuration

`FINANCE_DATA_DIR` changes the directory containing both default SQLite files.
The two files can instead be configured independently:

- `FINANCE_BACKUP_DIR`: backup output directory, defaulting to
  `<FINANCE_DATA_DIR>/backups`
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

## Backup and disaster recovery

The backup command discovers the configured finance and LangGraph checkpoint
storage, creates an online SQLite copy or PostgreSQL custom-format archive, and
then verifies it before publishing the backup directory:

```bash
python -m scripts.backup_data
python -m scripts.verify_backup "${FINANCE_BACKUP_DIR}/<backup-directory>"
```

Docker Compose stores backups on the separate `finance-backups` volume:

```bash
docker compose exec finance-assistant python -m scripts.backup_data
docker compose exec finance-assistant \
  python -m scripts.verify_backup /app/backups/<backup-directory>
```

Copy completed directories to encrypted off-site object storage. The manifest
contains artifact roles, sizes, and SHA-256 checksums but never database URLs or
credentials. Do not treat the checksum as encryption or authentication; protect
backup access because the archive contains financial and identity data.

Schedule `python -m scripts.backup_data` with the platform scheduler or a daily
cron job, alert on a nonzero exit, and apply independent storage retention. The
backup directory must be persistent and separate from the live database volume.
PostgreSQL deployments require `pg_dump` and `pg_restore`; use client tools from
the same major version as the server or a newer supported version. The provided
container installs these tools.

Run a restore drill into new destinations, never directly over the live data:

```bash
python -m scripts.restore_data data/backups/<backup-directory> \
  --finance-path /tmp/finance-restored.db \
  --checkpoint-path /tmp/checkpoints-restored.db
```

For PostgreSQL, create an empty drill database and provide its URL through the
deployment secret mechanism:

```bash
python -m scripts.restore_data /secure/backups/<backup-directory> \
  --finance-url "$RESTORE_DATABASE_URL" \
  --checkpoint-url "$RESTORE_DATABASE_URL"
```

The command verifies every artifact before restoring and rejects existing
SQLite files or non-empty PostgreSQL databases. `--force` deliberately replaces
an existing destination and must be used only during an approved recovery while
application writes are stopped. After a drill, run migration status checks and
application smoke tests against the restored destination. Record the recovery
time and repeat the drill at least quarterly and before changing backup tooling.

Recommended production objectives are a 24-hour recovery point (daily backup)
and a four-hour recovery time. Tighten those values if the acceptable data-loss
window requires more frequent snapshots.

## Scaling boundary

With PostgreSQL-backed finance data and checkpoints plus `FINANCE_REDIS_URL`,
the application no longer depends on per-process state. PostgreSQL pools default
to 1–10 finance connections and 1–5 checkpoint connections per application
process. Validate total database connection capacity and load-test the target
environment before increasing worker or replica counts.
