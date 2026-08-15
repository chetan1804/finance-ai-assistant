# Deployment

The application ships as one multi-stage container. Node builds the React
frontend, then FastAPI serves the compiled frontend and authenticated API from
the Python runtime image. SQLite finance data and LangGraph checkpoints are
stored in a mounted persistent directory.

## Production requirements

- Python 3.12 or the provided Docker image
- A persistent volume mounted at `/app/data`
- One application process and one running instance while SQLite and the
  in-memory rate limiter are in use
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

The application applies pending versioned SQLite migrations before startup.
Users and their first accounts are created through registration.

Check a mounted database before deployment with:

```bash
python -m scripts.migrate_database --check
```

Back up both database files before releasing a new migration. Applied migration
files are checksum-protected and must never be edited.

## Storage configuration

`FINANCE_DATA_DIR` changes the directory containing both default SQLite files.
The two files can instead be configured independently:

- `FINANCE_DATABASE_PATH`: financial application database
- `FINANCE_CHECKPOINT_PATH`: LangGraph conversation checkpoint database

Back up both SQLite databases from the persistent volume. Test restoration
regularly and stop application writes while taking a raw file-level copy.

## Scaling boundary

Do not increase Uvicorn workers or platform replicas with the current storage
and rate-limiting design. Horizontal scaling requires moving financial data to
a managed database, checkpoints to shared storage, and rate limiting to Redis
or an API gateway.
