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

Step 20 — Deployment foundation complete.

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

Keep your existing `.env` and generate a bearer token mapped to an existing
database user ID:

```bash
python -m scripts.configure_api_token --user-id 1
```

The command preserves existing provider keys and prints the new bearer token
once. Store it securely.

Start the local server:

```bash
python -m uvicorn src.api.app:create_app --factory --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation. Send
the configured token as `Authorization: Bearer <token>`.

Open `http://127.0.0.1:8000/` for the finance dashboard. Paste the generated
bearer token into the secure session screen. The browser keeps it only in
session storage, so signing out or closing the tab clears the session.

Available endpoints:

- `GET /health`
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

## Deployment

The production container uses a non-root user, health checks, a reduced runtime
dependency set, and persistent SQLite storage. See [DEPLOYMENT.md](DEPLOYMENT.md)
for first-run bootstrap, Docker Compose, managed-platform configuration, backup,
and scaling guidance.
