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

The live evaluation measures intent/date extraction, query correctness, and
whether responses contain the verified financial amount:

```bash
python -m scripts.evaluate_finance_agent --live
```

Use `--output <path>.json` to save case-level results and `--min-score 0.9`
to set the quality gate. The default minimum score is 80%.

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
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/summary`
- `GET /api/v1/transactions`
- `POST /api/v1/transactions`
- `PUT /api/v1/transactions/{transaction_id}`
- `DELETE /api/v1/transactions/{transaction_id}`
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
- Account balance cards
- User preference editing
- Context-aware finance assistant chat

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

Database migrations run automatically at application startup. See
[MIGRATIONS.md](MIGRATIONS.md) for status checks and safe schema-change rules.
