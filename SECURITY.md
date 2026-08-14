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

## Important limitations

- The CLI accepts a user ID directly. It is not authentication. The API
  milestone must derive the user ID from a verified session or access token and
  must never trust a user ID supplied in a request body.
- Existing SQLite databases do not automatically receive new constraints.
  Production deployment requires versioned database migrations.
- SQLite files are not encrypted at rest by this project. Production storage
  must provide disk/database encryption and restricted file permissions.
- Provider prompts and transaction data are sent to the configured LLM service.
  Production use requires an approved data-processing and retention policy.
- Rate limiting, secure HTTP headers, CSRF protection, and endpoint permissions
  belong at the API boundary and are not provided by the current CLI.

## Secret handling

Store `GROQ_API_KEY` only in `.env` or the deployment secret manager. Never
commit `.env`, API keys, database files, logs containing transactions, or saved
conversation checkpoints.

If a secret is committed, revoke it at the provider immediately, remove it from
Git history, and replace it with a newly generated value.
