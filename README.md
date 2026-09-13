# Scribe: Secretary Assistant

[![CI](https://github.com/Stumpwiz/scribe/actions/workflows/ci.yml/badge.svg)](https://github.com/Stumpwiz/scribe/actions/workflows/ci.yml)

Scribe supports Residents Council and Association agenda preparation, meeting
reminders, report ingestion, and LaTeX/PDF minutes production. The supported
monthly workflow uses module commands and a reminder GUI; older CrewAI tools
remain in the repository for compatibility.

## Project layout

- `src/scribe/cli/`: cycle orchestration, ingestion, collection, formatting,
  minutes building, and committee archive commands.
- `src/scribe/tools/`, `src/scribe/tasks/`, and `src/scribe/ui/`: email, Clerk
  queries, reminders, agenda generation, and the Flask interface.
- `src/scribe/assets/`: templates, report metadata, source graphics, and
  example-only recipient JSON.
- `src/scribe/input/`: local meeting inputs; cycle `report_state.json` policy
  files have a narrow Git tracking exception.
- `src/scribe/output/`: local cycle originals, converted reports, and outputs.
- `src/scribe/google_auth/`: locally provisioned helper and authentication
  material, intentionally absent from Git.
- `scripts/`, `tests/`, and `docs/`: launchers, regression tests, and procedures.
- `pyproject.toml`: package metadata and Python dependencies.

## Getting started

1. Use Python compatible with `pyproject.toml` (currently 3.10–3.13). Create a
   virtual environment and install the project from the repository root:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

   On Windows, activate `.venv\Scripts\activate` instead. The commands below
   use `uv run python`; an activated project interpreter can also run them.
2. Prepare local configuration using `.env.example` as a reference. Keep
   operational values in ignored `.env` or private environment configuration.
3. Arrange Clerk backend/model availability and database access as described in
   [Database setup](docs/DATABASE_SETUP.md). Normal reminder recipients come
   dynamically from Clerk. JSON recipient files are not required for this path.
4. Obtain the Scribe-specific `src/scribe/google_auth` helper from the trusted
   maintainer and provision authorized Gmail credentials locally. The repository
   does not provide a complete fresh-clone provisioning mechanism for this
   helper. Installing the external `google-auth` package does not supply it.
   Keep the helper, credentials, and tokens out of Git.
5. Install LibreOffice (`soffice` or `libreoffice`) for document conversion and
   XeLaTeX for minutes/agenda PDF builds. Follow the
   [monthly-cycle runbook](docs/monthly-cycle-runbook.md) for preview, applied
   ingestion, local building, review, distribution, and closeout.

Preview report staging (reads Gmail; does not download report attachments):

```bash
uv run python -m src.scribe.cli.run_cycle --cycle YYYY-MM --skip-collect --skip-format
```

Launch the reminder GUI in explicit preview mode:

```bash
DRY_RUN=true uv run python scripts/run_reminder_gui.py
```

Use these module commands rather than `scribe-ingest`: its current packaging
entry point targets `scribe.cli:main`, while the `scribe.cli` package does not
export `main`. That compatibility entry point needs a separate code correction.

## Recipients and external effects

Normal reminder recipients are the Clerk **Residents Council Officers** mailing
list for Regular RC meetings, with committee chairs added and deduplicated for
Open RC and Association meetings. Association reminders do not go automatically
to all residents. `RECIPIENTS_DIR` serves legacy JSON interfaces only.

Minutes distribution is a separate Secretary procedure: obtain the current
cut-and-paste list from Clerk (Regular: officers; Open/Association: officers plus
committee chairs), review the draft, and distribute when authorized. The monthly
cycle does not automatically email draft minutes.

Applied ingestion downloads attachments and labels Gmail messages. Reminder
sending uses Gmail with the locally authorized OAuth scopes; Scribe is not a
read-only Gmail application. The GUI opens a local HTTP listener by default.
See the [security guide](docs/SECURITY.md) for authentication, configuration,
logging, and repository hygiene.

## Publishing committee minutes

The committee archive command converts DOCX to PDF and proposes an archive link.
The archive is the authoritative record; the website index links to that PDF.
Preview first; applying it is a separate authorized website operation:

```bash
uv run python -m src.scribe.cli.archive_committee_minutes \
  --committee SE --month YYYY-MM --source "/path/to/minutes.docx" \
  --site-root "/path/to/mrra"
```

Add `--apply` only after review to write the archive and website changes. Existing
destination PDFs are refused unless `--force` is also supplied.
