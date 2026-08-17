# AI Reliability

The finance assistant uses the LLM only to classify a question and extract an
optional category and date range. The selected query is allowlisted, all
database access remains scoped to the authenticated user, and the final answer
is rendered from the verified database amount without another LLM call.

## Failure controls

- Requests are screened for common direct, privilege-escalation, secret-seeking,
  cross-user, and encoded prompt-injection patterns before provider access.
- The provider client has a 20-second timeout, two retries, and a 300-token
  output ceiling by default.
- Provider errors are logged by error class only. The user receives a fixed
  temporary-unavailability message and no database mutation occurs.
- Parsed intent, category, and dates pass through the existing allowlist and
  validation layer before any query is selected.
- Monetary answers support the stored English, Hindi, or Marathi preference and
  contain only the server-formatted verified result.

Configure the bounded provider behavior through:

```text
FINANCE_LLM_MODEL=llama-3.3-70b-versatile
FINANCE_LLM_TIMEOUT_SECONDS=20
FINANCE_LLM_MAX_RETRIES=2
FINANCE_LLM_MAX_TOKENS=300
```

## Evaluation

Run the deterministic gate, which needs no provider key:

```bash
python -m scripts.evaluate_finance_agent --min-score 1.0
```

The dataset covers normal finance intents, follow-up context, direct prompt
injection, privilege escalation, system-prompt extraction, encoded injection,
and credential exfiltration. The report scores query correctness; live mode
also scores context extraction, grounding, and unsafe-output leakage:

```bash
python -m scripts.evaluate_finance_agent \
  --live \
  --min-score 0.9 \
  --output artifacts/ai-evaluation.json
```

Live evaluation consumes provider quota and may vary as models change. Run it
before changing the model or prompt, while CI keeps the deterministic offline
gate stable. Add a regression case whenever a new failure mode is discovered.

## Performance gate

The standard-library load runner sends concurrent HTTP requests and reports
success count, error rate, requests per second, p50, p95, p99, and maximum
latency. CI exercises `/ready` on the built production image:

```bash
python -m scripts.load_test_api \
  --base-url http://127.0.0.1:8000 \
  --endpoint /ready \
  --requests 200 \
  --concurrency 20 \
  --max-p95-ms 500 \
  --min-rps 20 \
  --max-error-rate 0 \
  --output artifacts/performance.json
```

For an authenticated endpoint, pass `--token` through a protected shell
variable and keep generated reports out of source control if they could contain
deployment metadata. Avoid exceeding the configured API rate limit when
choosing the request count.

## Remaining limitations

Pattern matching cannot detect every prompt-injection variation. Reliability
therefore depends on layered controls: least-privilege tools, user-scoped data,
structured and validated model output, deterministic final answers, monitoring,
and continuously expanded adversarial tests. The offline gate does not measure
provider availability or semantic drift; scheduled live evaluation is still an
operational responsibility.
