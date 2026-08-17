# Finance Assistant

An AI-powered personal finance assistant that understands the user's
financial data, spending behavior, goals, and preferences.

## Project Vision

Build a finance assistant progressively using:

- Python
- Data Analysis
- Machine Learning
- Generative AI
- RAG
- LLMs
- Tool Calling
- Agentic AI
- LangChain
- LangGraph
- Evaluation
- Production deployment

## Development Roadmap

1. Project Setup
2. Data Model
3. Basic Finance Tracker
4. Data Processing
5. Exploratory Data Analysis
6. Machine Learning
7. LLM Integration
8. Prompt Engineering
9. Structured Outputs
10. RAG
11. Tool Calling
12. Agentic AI
13. LangGraph
14. Memory
15. Personalization
16. Evaluation
17. Security
18. API
19. UI
20. Deployment

## Current Stage

The original 20-step roadmap is complete. The next-level React frontend is
implemented; the legacy static UI remains available as a local fallback during
acceptance testing. The finance and authentication data layer supports SQLite
and PostgreSQL with versioned migrations for both backends. Conversation
checkpoints also move to PostgreSQL automatically when the finance database URL
is configured, while local development continues to use SQLite. PostgreSQL
connections are pooled, Redis provides cross-replica rate limiting, and the
readiness endpoint verifies production dependencies.

## Step 15 Features

- User-scoped finance queries and account validation
- Date-aware income, expense, category, and savings queries
- Follow-up question resolution using LangGraph conversation memory
- SQLite checkpoints isolated by user and conversation thread
- Stored language, currency, income, risk, and notification preferences
- Personalized responses that use verified database results only

## Run the Personalized Assistant

```bash
source .venv/bin/activate
python -m scripts.step15_finance_chat --user-id 1
```

Run the automated tests with:

```bash
python -m pytest -q
```

## Evaluate the Finance Agent

The offline evaluation uses a deterministic database and does not call an LLM:

```bash
python -m scripts.evaluate_finance_agent
```

The live evaluation measures intent/date extraction, query correctness,
grounding against verified financial amounts, and unsafe-output leakage:

```bash
python -m scripts.evaluate_finance_agent --live
```

Use `--output <path>.json` to save case-level results and `--min-score 0.9`
to set the quality gate. The default minimum score is 80%.

Provider calls have explicit timeout, retry, and output-token limits. Prompt
injection screening runs before the provider call, provider failures return a
safe retry response, and final monetary answers are rendered deterministically
from the database result. See [AI_RELIABILITY.md](AI_RELIABILITY.md) for the
threat model, configuration, and evaluation workflow.

## Performance Testing

With the API running, execute the repeatable readiness-path baseline:

```bash
python -m scripts.load_test_api \
  --requests 200 \
  --concurrency 20 \
  --max-p95-ms 500 \
  --min-rps 20
```

The command exits unsuccessfully when the latency, throughput, or error-rate
budget is missed. CI runs the same gate against the production container. Use
`--endpoint`, `--token`, and `--output` to test an authenticated route and save
the JSON result. Benchmark the deployed environment before setting tighter
service objectives; local and shared CI measurements are only regression
baselines.

## Security

The application validates financial values, dates, identifiers, profile fields,
and chat input before use. Database operations are parameterized and scoped to
the selected user, and the LLM treats conversation content as untrusted data.

See [SECURITY.md](SECURITY.md) for implemented controls, production limitations,
and secret-handling guidance.

## Run the API

Keep your provider key in `.env`. Users now create an account and sign in with
email and password; manually configured bearer tokens remain available only as
a migration fallback.

Start the local server:

```bash
python -m uvicorn src.api.app:create_app --factory --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation. Send
the configured token as `Authorization: Bearer <token>`.

Open `http://127.0.0.1:8000/` for the finance dashboard. Register with a name,
email, password, currency, and first account, or sign into an existing profile.

Available endpoints:

- `GET /health`
- `GET /ready`
- `GET /version`
- `GET /metrics`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `PATCH /api/v1/auth/password`
- `GET /api/v1/auth/sessions`
- `DELETE /api/v1/auth/sessions/{session_id}`
- `POST /api/v1/auth/logout-all`
- `POST /api/v1/privacy/export`
- `POST /api/v1/export/transactions`
- `POST /api/v1/import/transactions`
- `DELETE /api/v1/privacy/account`
- `GET /api/v1/summary`
- `GET /api/v1/transactions`
- `POST /api/v1/transactions`
- `PUT /api/v1/transactions/{transaction_id}`
- `DELETE /api/v1/transactions/{transaction_id}`
- `GET|POST /api/v1/budgets`
- `PUT|DELETE /api/v1/budgets/{budget_id}`
- `GET|POST /api/v1/goals`
- `PUT|DELETE /api/v1/goals/{goal_id}`
- `GET|POST /api/v1/recurring-transactions`
- `PUT|DELETE /api/v1/recurring-transactions/{recurring_id}`
- `POST /api/v1/recurring-transactions/process`
- `GET /api/v1/notifications`
- `PATCH /api/v1/notifications/{notification_id}/read`
- `POST /api/v1/notifications/read-all`
- `DELETE /api/v1/notifications/{notification_id}`
- `GET /api/v1/preferences`
- `PUT /api/v1/preferences`
- `POST /api/v1/chat`
- `GET /api/v1/accounts`
- `GET /api/v1/categories`

## Dashboard Features

- Responsive financial overview and date filters
- Income, spending, savings, and savings-rate metrics
- Cash-flow comparison and category breakdown
- Secure transaction creation, editing, and deletion with balance reconciliation
- Category budgets with date-scoped actual spending and progress
- Savings goals with target, saved amount, priority, status, and progress
- Daily, weekly, monthly, and yearly recurring income or expenses
- Idempotent due-transaction generation with pause, resume, and end dates
- Atomic, duplicate-safe transaction CSV import with a downloadable template
- Password-confirmed complete JSON and spreadsheet-safe CSV exports
- Persistent budget, goal, recurring, and import notifications
- Account balance cards
- User preference editing
- Password rotation and active-session management
- Personal-data export and permanent account deletion
- Context-aware finance assistant chat

See [IMPORT_EXPORT.md](IMPORT_EXPORT.md) for the CSV format, validation limits,
API example, export protections, and notification behavior.

## Observability

Every API response includes an `X-Request-ID`. Application logs are structured
JSON by default and record route templates, response status, and duration
without logging request bodies, tokens, or financial values. `/metrics` exposes
Prometheus-compatible request, latency, and dependency-readiness metrics.

## Run the React Frontend

Run FastAPI in one terminal:

```bash
python -m uvicorn src.api.app:create_app --factory --reload
```

Run the React development server in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173/`. Vite proxies `/api` and `/health` requests to
FastAPI on port `8000`.

To test the production build locally:

```bash
cd frontend
npm run build
cd ..
FINANCE_UI_DIST=frontend/dist python -m uvicorn src.api.app:create_app --factory
```

## Deployment

The production container uses a non-root user, health checks, and a reduced
runtime dependency set. SQLite remains the zero-configuration default;
PostgreSQL can be selected with `FINANCE_DATABASE_URL`. See
[DEPLOYMENT.md](DEPLOYMENT.md) for first-run bootstrap, managed-platform
configuration, backup, and scaling guidance.

Production mode validates allowed hosts, redirects trusted HTTP requests to
HTTPS, emits HSTS on secure responses, and permits cross-origin browser access
only for explicitly configured frontend origins.

Database migrations run automatically at application startup. See
[MIGRATIONS.md](MIGRATIONS.md) for status checks and safe schema-change rules.

## Backup and recovery

Create an integrity-checked backup of the configured finance and conversation
storage:

```bash
python -m scripts.backup_data
python -m scripts.verify_backup data/backups/<backup-directory>
```

Each backup contains a credential-free manifest with SHA-256 checksums. SQLite
uses its online backup API; PostgreSQL uses custom-format `pg_dump` archives.
Restore rejects existing destinations unless `--force` is explicitly supplied.
See [DEPLOYMENT.md](DEPLOYMENT.md#backup-and-disaster-recovery) for restore drills,
scheduling, and PostgreSQL client-version requirements.

## Release container

Pushing a semantic version tag such as `v1.0.0` runs the complete backend and
frontend verification suite, then publishes a versioned image to GitHub
Container Registry with an SBOM and build-provenance attestation. See
[RELEASE.md](RELEASE.md) for the release and rollback procedure.
