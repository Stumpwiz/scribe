# Scribe project context

Scribe supports Residents Council and Association agendas, reminders, report
collection, and minutes production. This file describes the current workflow;
cycle-specific progress belongs in local records, not a shared session transcript.

## Supported paths

- Reminder GUI: `uv run python scripts/run_reminder_gui.py` from the repository
  root. Set `DRY_RUN=true` explicitly for preview; check effective state before
  any intended send. Agenda PDF generation is implemented.
- Monthly ingestion: `src.scribe.cli.run_cycle` → `src.scribe.cli.ingest` →
  `EmailService` action `stage_attachments_v2`. Preview reads Gmail; applied
  staging downloads eligible attachments, labels messages, and writes local
  ingestion state. Other email interfaces can mark mail read; do not apply
  historical “never download/never mark read” claims to the whole application.
- Local reports: `src.scribe.cli.collect_pdfs` → `src.scribe.cli.format_all` →
  `src.scribe.cli.build_minutes`. Choose `regular`, `open`, or `association` for
  minutes. Local downstream commands do not distribute the resulting PDF.

See the [monthly-cycle runbook](../monthly-cycle-runbook.md) for exact commands,
mailbox closeout, report pagination, review, distribution, and retention.

## Recipients and configuration

Normal reminders query Clerk's Residents Council Officers mailing list. Regular
RC uses officers; Open RC and Association use officers plus committee chairs,
deduplicated. Association does not automatically target all residents. The task
workflow accepts explicit `email_recipients`; otherwise it uses Clerk. Low-level
send tools use caller-supplied lists and do not discover a distribution list.

Minutes distribution is the Secretary's separate Clerk cut-and-paste procedure
with the same meeting-type groups, after review and authorization.

`EMAIL_FROM` controls sender identity and reminder recognition;
`REPORT_SUBMISSION_EMAIL` controls the printed submission/correction address,
falling back to `EMAIL_FROM`. `DEFAULT_FALLBACK_EMAIL` and `DEV_OVERRIDE_EMAIL`
have distinct fallback/redirection roles described in [Security](../SECURITY.md).
`RECIPIENTS_DIR` is legacy JSON compatibility, not normal recipient setup or the
v2 ingestion source. Current sender-to-office inference can use Clerk.

## Source and generated state

Cycle `src/scribe/input/cycles/YYYY-MM/report_state.json` is tracked policy.
`{"appendix": "none"}` intentionally excludes an office from collection,
conversion, placeholders, and appendix selection even when old assets remain.
Delivery at the meeting is separately recorded in manually authored prose.
Ordinary missing written reports keep placeholder behavior; Open minutes omit
wing placeholders but may include received wing reports. Manifests are derived.
Follow the runbook rather than manually editing them to record policy.

Preserve originals and manually authored cycle inputs, including officer
fragments stored under output. Generated output is not automatically disposable
merely because it is ignored. Publication and cleanup are separate decisions.

## Setup and maintenance boundaries

Clerk backend imports and database access are prerequisites for normal recipient
lookup; see [Database setup](../DATABASE_SETUP.md). The custom
`src/scribe/google_auth` helper is locally provisioned and excluded from Git.
There is no complete fresh-clone provisioning path for it in this repository;
third-party `google-auth` installation is insufficient. Credentials, tokens,
operational contacts, and private configuration must remain local.

Prefer small changes, mocked external operations for tests, and explicit review
before email, publication, or destructive cleanup. The legacy `scribe-ingest`
packaging entry point and older JSON-based callers need separate compatibility
work; use the runbook's module commands. Do not repair these or redesign
authentication incidentally during a documentation or meeting-cycle change.
