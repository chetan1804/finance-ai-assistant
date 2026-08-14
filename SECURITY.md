# Security

## Implemented controls

- All financial SQL uses bound parameters.
- Read and write operations are scoped to a validated positive user ID.
- Transactions reject accounts and categories owned by another user.
- Parent categories cannot reference another user's private category.
- Monetary values must be finite, positive, and below the supported limit.
- Dates must use ISO `YYYY-MM-DD` format and ranges must be ordered.
- Chat questions and thread IDs have length and character restrictions.
- Conversation history is treated as untrusted data and limited to 20 user turns.
- LLM output is reduced to an allowlisted intent and validated dates before a
  database query is selected.
- Financial responses are grounded in a server-side database result.
- API keys and local databases are excluded from Git.
- New databases include defensive `CHECK` constraints.
- API user identity is derived from an opaque bearer token, never a request body.
- Authenticated endpoints have per-user rate limiting.
- API responses include no-store, MIME-sniffing, framing, and referrer controls.
- Oversized request bodies are rejected before endpoint processing.

## Important limitations

- The CLI still accepts a user ID directly and is only suitable for trusted local
  use. Network clients must use the authenticated API.
- The current bearer-token map is appropriate for local development and small
  internal deployments. Production should use a dedicated identity provider,
  expiring credentials, rotation, and revocation.
- Existing SQLite databases do not automatically receive new constraints.
  Production deployment requires versioned database migrations.
- SQLite files are not encrypted at rest by this project. Production storage
  must provide disk/database encryption and restricted file permissions.
- Provider prompts and transaction data are sent to the configured LLM service.
  Production use requires an approved data-processing and retention policy.
- The in-memory rate limiter is per process. A multi-worker deployment requires
  a shared limiter such as Redis or an API gateway.
- TLS termination, allowed-host enforcement, and trusted-proxy configuration
  must be supplied by the production platform.

## Secret handling

Store `GROQ_API_KEY` only in `.env` or the deployment secret manager. Never
commit `.env`, API keys, database files, logs containing transactions, or saved
conversation checkpoints.

If a secret is committed, revoke it at the provider immediately, remove it from
Git history, and replace it with a newly generated value.
