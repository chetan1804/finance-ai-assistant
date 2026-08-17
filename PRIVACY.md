# Privacy controls

ArthNivo stores the minimum application data needed for a personal finance
workspace: profile details, preferences, accounts, categories, transactions,
budgets, goals, authentication records, and conversation checkpoints. Provider
prompts may contain finance context needed to answer a user's question; the
deployment operator must approve the configured LLM provider's processing and
retention terms.

## User controls

Authenticated users can manage privacy from **Security & privacy** in the React
dashboard. Both high-impact operations require the current password again:

- **Download my data** produces a portable JSON document containing profile and
  financial records. Password hashes, access-token hashes, refresh-token hashes,
  and session records are excluded.
- **Delete my account** requires the exact confirmation `DELETE`. It removes the
  user profile, credentials, sessions, accounts, categories, transactions,
  budgets, goals, preferences, and all conversation threads prefixed with that
  user ID.

The equivalent API operations are `POST /api/v1/privacy/export` and
`DELETE /api/v1/privacy/account`. A legacy bearer-token profile without password
credentials must first be migrated to normal account authentication; it cannot
bypass password reauthentication.

## Backup retention

Live data is deleted immediately. Existing encrypted disaster-recovery backups
remain immutable until they reach the deployment's documented retention limit.
Operators must define that limit, restrict backup access, log approved restores,
and avoid reintroducing a deleted account during recovery. See `DEPLOYMENT.md`
for backup and restore procedures.

This document describes product behavior and is not a jurisdiction-specific
privacy notice. A public deployment still needs an operator-approved privacy
notice, retention schedule, subprocessors list, and request-handling process.
