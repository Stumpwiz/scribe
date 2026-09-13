# Scribe Project – AI Context & Continuity

> **Purpose**: This file provides durable project context for AI agents (Codex, Claude Agent, etc.) and for the human maintainer.
> **Instruction to AI agents**: *Read this file first before proposing changes or edits.*

---

## Project Overview

**Scribe** is an agentic assistant supporting the Residents Council / Residents Association at Mercy Ridge. It automates meeting workflows such as agenda distribution, reminders, email ingestion, and (future) report tracking.

The project is intentionally conservative: correctness, traceability, and non‑destructive behavior matter more than speed or autonomy.

---

## Current Milestones (Authoritative)

### ReminderAgent (v1)

* **Status**: In production
* **Function**: Sends agenda / meeting reminder emails
* **Email backend**: Gmail API
* **Authorized mailbox**: `user5@example.com`
* **Behavior**:

  * Sends email (optionally dry‑run)
  * Attaches agenda PDFs when present
  * No ingestion or mailbox modification

### IngestorAgent (v1.x)

* **Status**: Implemented and validated

* **Purpose**: Manual, non-destructive ingestion focused on report submissions

* **Core actions**:

  * Read messages matching a Gmail search query
  * Fetch Gmail payload structure (no downloads) to enumerate attachment metadata from payload parts only
    * Metadata captured per attachment: filename, mime, size, attachment_id
  * Classify into one of:

    * `report-submission`
    * `meeting-minutes`
    * `forwarded-report`
    * `administrative-message`
    * `unknown`
  * `classification_confidence` (high/medium/low) is driven primarily by attachment presence
  * Apply label **`Scribe/Incoming`** (add-only)
  * Append a JSONL log record with: classification, classification_confidence, attachments (filename, mime, size, attachment_id), attachments_count, attachments_total_size, has_attachments
  * Safety CLI flag: `--whoami` prints the authorized Gmail account and exits (no ingest)

* **Hard constraints (do not violate)**:

  * ❌ Never send replies
  * ❌ Never mark messages read
  * ❌ Never archive or delete
  * ❌ Never download attachments
  * ✅ Label add‑only is allowed

* **Idempotency**:

  * Messages already labeled `Scribe/Incoming` are skipped
  * Prevents duplicate log entries
  * Known gap (2026-06): processed message IDs are not persisted across cycle boundaries, so old unread Inbox mail can still contaminate later cycles

---

## Key Code Locations

* **Email service tool**:
  `src/scribe/tools/email_service.py`

* **CLI for ingestion**:
  `src/scribe/cli/ingest.py`

* **CLI for minutes build**:
  `python -m src.scribe.cli.build_minutes --cycle YYYY-MM --type regular|open|association [--out path] [--dry-run]`

* **Tool registry**:
  `loader.py` (maps `email_service` → `EmailService()`)

* **Ingest log (JSONL)**:
  `src/scribe/output/ingestion/ingest_log.jsonl`

---

## Gmail / OAuth Configuration (Critical)

* **Active Google Cloud project**: `scribe-gmail-486216`

* **OAuth client type**: Desktop app

* **OAuth status**: Testing

* **Authorized test user**: `user5@example.com`

* **Important invariant**:

  * Gmail API uses `userId="me"`
  * Identity is determined *solely* by the OAuth token

* **Sanity check command** (run before any destructive operation):

  ```bash
  python - <<'PY'
  from googleapiclient.discovery import build
  from src.scribe.google_auth.google_auth_helper import get_google_credentials
  creds = get_google_credentials()
  svc = build("gmail", "v1", credentials=creds)
  print("Authorized Gmail:", svc.users().getProfile(userId="me").execute()["emailAddress"])
  PY
  ```

---

## Ingestion Query Behavior

* **Default query**:

  ```
  is:unread in:inbox -category:promotions -category:social -category:updates
  ```

* **Query override supported**:

  * CLI flag: `--query "<gmail search>"`
  * Passed end‑to‑end: CLI → EmailService._run → ingest_unread_inbox_v1

* **Use cases for override**:

  * Testing when Inbox is empty (e.g. `in:trash`, `in:anywhere`)
  * Controlled experiments without touching Inbox

* **Operational warning from 2026-06 open cycle**:

  * The default query is too broad for cycle safety when old cycle mail remains unread in Inbox
  * Cross-cycle contamination occurred when unread 2026-04/2026-05 messages were staged into 2026-06
  * Immediate mitigation: mark archived-cycle mail read and remove it from Inbox before ingestion
  * Long-term fix required: persist processed Gmail message IDs and skip forever, or redesign label/query lifecycle

---

## Current Mailbox State (as of 2026-06 closeout)

* Do not assume Inbox hygiene by default.
* `Scribe/Incoming` is currently ambiguous in practice and should not be treated as a reliable cycle boundary.
* Before running ingestion for a new cycle, archived-cycle unread mail must be marked read and removed from Inbox.

---

## Development Environment

* **Local machine**: Windows desktop ("Blacksun")
* **Remote dev host**: NVIDIA Spark ("the development host")
* **IDE**: PyCharm via JetBrains Gateway (remote development)

### AI tooling constraints

* **Junie by JetBrains**: ❌ Not available under remote development
* **Primary IDE agent**: Codex
* **Recommended settings**:

  * Agent: Codex
  * Access: Agent (not full access)
  * Model: `gpt-5.2-codex-max`
  * Reasoning: `medium` (default)

---

## Guardrails for AI Agents

When modifying this repository:

* Prefer **small, reviewable patches**
* Never refactor ReminderAgent while working on IngestorAgent unless explicitly asked
* Never introduce automatic mailbox mutation beyond label‑add
* Avoid running shell commands unless explicitly requested
* Preserve backwards compatibility with existing CLI usage

---

## Last Session Summary

* Completed 2026-06 open Residents Council cycle to clean draft-minutes state
* Successful final build:
  `uv run python -m src.scribe.cli.build_minutes --cycle 2026-06 --type open`
* Final minutes artifacts:
  `src/scribe/output/cycles/2026-06/minutes_open_2026-06.pdf`
  and `src/scribe/output/cycles/2026-06/minutes_open.tex`
* Final formatting succeeded:
  `uv run python -m src.scribe.cli.format_all --cycle 2026-06 --input-dir src/scribe/output/cycles/2026-06/pdf`
  with `ok: 21`, `failed: 0`, `placeholder-used: 0`
* Manifest written:
  `src/scribe/output/cycles/2026-06/manifest.json`
* Reconciliation work completed after cross-cycle contamination (rebuild + manual report verification + canonical `originals/` validation)
* Reminder workflow validated for open meeting:
  Clerk-based recipients only, 19 recipients total (11 officers + 8 committee chairs), `agenda_2026-06-04_open.pdf` attached, send successful

---

## Next Intended Step

* External ops:
  mail draft 2026-06 minutes PDF, update RC website/archive, then move processed June mail from `Scribe/Incoming` to `Scribe/Archive/2026-06`
* Development priorities:
  implement durable Gmail message-ID dedupe, add cycle-scoped ingestion safety, improve forwarded/sender_fallback classification, and clarify director main-report vs appendix handling

---

> **End of context**
