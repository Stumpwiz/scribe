# Clerk database setup for Scribe

Scribe queries Clerk's PostgreSQL data for reminder recipients and, when needed,
for sender-to-office identification during report ingestion. Database tools and
these lookups are implemented; they are not future setup tasks.

## Prerequisites

- Install Scribe's dependencies from `pyproject.toml` in the project interpreter.
- Make the compatible Clerk backend available. `src/scribe/clerk_models.py`
  adds a sibling `clerk/backend` directory to the import path and imports
  `app.models` and `app.database`. A clean Scribe clone alone does not provide
  those modules. Coordinate the backend version and its own dependencies with
  the Clerk maintainer.
- Set `DATABASE_URL` in private environment configuration or ignored `.env`.
  `.env.example` provides a placeholder URL, not deployment credentials.
- Arrange network access and database permissions with the database maintainer.
  Use the privileges needed by the intended queries; this guide does not assume
  full read/write access. TLS requirements belong to the configured connection
  and database policy; Scribe does not add TLS enforcement to an arbitrary URL.

No AWS resource changes, particular server version, or fixed deployment layout
are implied by this procedure. Schema migrations belong to Clerk. Keep Scribe's
imported models compatible with the deployed schema; a schema change is not
made safe merely by importing shared models.

## Current queries and recipient selection

`src/scribe/database.py` loads `DATABASE_URL`, creates the SQLAlchemy engine,
and supplies `get_db_session()` and `get_db()`. Callers of `get_db_session()`
must close their session.

`src/scribe/tools/database_query_tool.py` supplies the Clerk **Residents Council
Officers** mailing list and committee-chair lookup. Normal reminders use:

- Regular RC: officers.
- Open RC: officers plus committee chairs, deduplicated.
- Association: officers plus committee chairs, deduplicated, not all residents.

The v2 ingestion path can look up a sender's current office using Clerk models.
Neither operation requires private `RECIPIENTS_DIR` JSON files. See the
[runbook](monthly-cycle-runbook.md) for fallback review and the separate manual
Clerk cut-and-paste minutes-distribution procedure.

## Optional connection diagnostic

After setup, and only when a live database check is intended, run from the
repository root with the installed project interpreter:

```bash
uv run python tests/test_db_connection.py
```

This is a live connection/query script, not a mocked offline test. It prints
server information, model counts, and sample body names; keep its output private.
Review individual errors: its model-query loop can print errors without failing
the overall result, so a final success banner alone does not prove every model
query worked. There is no root-level `test_db_connection.py`.

## Troubleshooting

- Missing `DATABASE_URL`: verify the run configuration and local environment.
- Missing `app.models`: verify the sibling Clerk backend and dependencies are
  available to the same interpreter as Scribe.
- Connection errors: ask the maintainer to check connection details, TLS,
  reachability, and privileges; do not paste credentials into reports.
- Model/validation errors: check backend/schema compatibility and both projects'
  environment requirements. Scribe temporarily removes some of its settings
  during Clerk model imports; this does not replace correct backend setup.

See [README](../README.md) and [Security](SECURITY.md).
