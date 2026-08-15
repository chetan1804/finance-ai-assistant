# Database migrations

Schema changes are stored as immutable, sequential SQL files. SQLite migrations
live in `src/database/migrations`; PostgreSQL equivalents live in
`src/database/postgres_migrations`:

```text
001_core_schema.sql
002_auth_sessions.sql
```

The application selects PostgreSQL when `FINANCE_DATABASE_URL` is set and uses
SQLite otherwise. It applies pending migrations before creating the FastAPI
app. Each applied version and SHA-256 checksum is recorded in
`schema_migrations`; startup fails if an applied migration was edited.

Check migration status without changing the database:

```bash
python -m scripts.migrate_database --check
```

Apply pending migrations explicitly:

```bash
python -m scripts.migrate_database
```

Set `FINANCE_DATABASE_URL` to check or migrate PostgreSQL:

```bash
FINANCE_DATABASE_URL=postgresql://finance:password@localhost:5432/finance \
  python -m scripts.migrate_database --check
```

Use `--database-path <path>` to explicitly select another SQLite file, even if
`FINANCE_DATABASE_URL` is present. Back up production data before applying a
new migration. Never edit an applied migration; create matching next-version
files for each supported backend instead.

PostgreSQL migrations use a transaction-level advisory lock so concurrent app
starts cannot apply the same migration at once. CI exercises the finance and
authentication services against a real PostgreSQL service.
