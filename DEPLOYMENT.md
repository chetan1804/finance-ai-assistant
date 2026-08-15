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
- `GROQ_API_KEY` and `FINANCE_API_TOKENS` configured as secrets

Never bake `.env`, database files, API tokens, or provider keys into an image.

## Deploy with Docker Compose

Create `.env` from `.env.example`, set the provider key, and configure a bearer
token for the first fresh-database user:

```bash
python -m scripts.configure_api_token --user-id 1
docker compose build
docker compose run --rm finance-assistant python -m scripts.bootstrap_user \
  --name "Your name" --email "you@example.com"
docker compose up -d
```

The bootstrap command is idempotent. It creates the initial user, account, and
common transaction categories on a new volume. Confirm that it reports user ID
`1`; if it reports another ID, regenerate `FINANCE_API_TOKENS` for that ID
before starting the service.

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
- Secrets: `GROQ_API_KEY` and `FINANCE_API_TOKENS`
- Instance count: `1`

Run the bootstrap command once against the mounted volume before normal startup.
The application automatically ensures the current schema exists at startup,
but it does not perform versioned migrations or create a user unless the
bootstrap command is run.

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
