# Database migrations

SQLite schema changes are stored in `src/database/migrations` as immutable,
sequential SQL files:

```text
001_core_schema.sql
002_auth_sessions.sql
```

The application applies pending migrations before creating the FastAPI app.
Each applied version and SHA-256 checksum is recorded in `schema_migrations`.
Startup fails if an applied migration was edited.

Check migration status without changing the database:

```bash
python -m scripts.migrate_database --check
```

Apply pending migrations explicitly:

```bash
python -m scripts.migrate_database
```

Use `--database-path <path>` for another SQLite file. Back up production data
before applying a new migration. Never edit an applied migration; create the
next sequential file instead.

These migrations make SQLite upgrades repeatable. PostgreSQL remains a separate
future migration because the current query layer uses SQLite placeholders,
pragmas, and connection behavior.
