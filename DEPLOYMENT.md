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
docker compose ps
```

Open `http://127.0.0.1:8000/` and enter the generated bearer token.

## Managed container platforms

Use the repository `Dockerfile` and configure:

- Health-check path: `/health`
- Container port: the platform-provided `PORT`, falling back to `8000`
- Persistent volume mount: `/app/data`
- Secret: `GROQ_API_KEY`
- Instance count: `1`

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

When neither checkpoint override is present, checkpoints follow
`FINANCE_DATABASE_URL` and therefore share the finance PostgreSQL database. Set
only `FINANCE_CHECKPOINT_PATH` to retain SQLite checkpoints alongside a
PostgreSQL finance database. Never configure both checkpoint overrides.

For a managed PostgreSQL database, store a URL such as the following in the
platform secret manager rather than committing it:

```text
postgresql://finance:password@database-host:5432/finance
```

Back up the selected finance database and the checkpoint SQLite database. Test
restoration regularly and stop application writes while taking a raw SQLite
file-level copy.

## Scaling boundary

PostgreSQL now provides shared finance data and conversation checkpoints, but do
not increase Uvicorn workers or platform replicas yet. Horizontal scaling still
requires moving rate limiting to Redis or an API gateway and validating the
target database connection capacity under production load.
