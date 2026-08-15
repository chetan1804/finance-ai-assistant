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
- Checkpoint deserialization only permits LangGraph's safe allowlisted types.
- LLM output is reduced to an allowlisted intent and validated dates before a
  database query is selected.
- Financial responses are grounded in a server-side database result.
- API keys and local databases are excluded from Git.
- New databases include defensive `CHECK` constraints.
- API user identity is derived from an opaque bearer token, never a request body.
- Authenticated endpoints have per-user rate limiting.
- API responses include no-store, MIME-sniffing, framing, and referrer controls.
- Oversized request bodies are rejected before endpoint processing.
- The dashboard stores bearer tokens in browser session storage, not persistent
  local storage, and removes them on sign-out.
- Dashboard assets use a same-origin content-security policy without inline or
  third-party scripts.
- Passwords are hashed with Argon2id and are never stored in plaintext.
- Access and refresh tokens are random opaque values stored only as SHA-256
  hashes in the database.
- Access sessions expire, refresh tokens rotate on use, and logout revokes the
  active database session.
- Registration and login are rate-limited by client address.

## Important limitations

- The CLI still accepts a user ID directly and is only suitable for trusted local
  use. Network clients must use the authenticated API.
- Email verification, password reset, MFA, compromised-password screening, and
  account recovery are not implemented yet.
- Versioned SQLite and PostgreSQL migrations are applied automatically, but
  production backups and restore testing remain operational responsibilities.
- SQLite files are not encrypted at rest by this project. Production SQLite or
  PostgreSQL storage must provide encryption and restricted access.
- Provider prompts and transaction data are sent to the configured LLM service.
  Production use requires an approved data-processing and retention policy.
- The in-memory rate limiter is per process. Even with PostgreSQL checkpoints, a
  multi-worker deployment requires a shared limiter such as Redis or an API
  gateway.
- TLS termination, allowed-host enforcement, and trusted-proxy configuration
  must be supplied by the production platform.
- Browser session storage remains accessible to same-origin JavaScript. Keep the
  strict content-security policy, review frontend dependencies, and avoid adding
  third-party scripts that could access access or refresh tokens.

## Secret handling

Store `GROQ_API_KEY`, `FINANCE_DATABASE_URL`, and `FINANCE_CHECKPOINT_URL` only
in `.env` or the deployment secret manager. Never commit `.env`, API keys,
database credentials, database files, logs containing transactions, or saved
conversation checkpoints.

If a secret is committed, revoke it at the provider immediately, remove it from
Git history, and replace it with a newly generated value.
