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

Step 15 — Personalization complete. Step 16 — Evaluation is next.

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
