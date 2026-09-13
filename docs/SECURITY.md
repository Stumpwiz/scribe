# Security guide

Scribe handles email, attachments, and Clerk contact data. Keep operational data
local and review external actions separately from local document preparation.

## Runtime configuration

Use ignored `.env` or private environment configuration. Tracked examples use
example-domain addresses only.

- `EMAIL_FROM`: outgoing sender identity and reminder-sender recognition during
  ingestion. It has no real-address default. It does not select the OAuth account.
- `REPORT_SUBMISSION_EMAIL`: address printed in reminder report-submission and
  agenda-correction instructions; falls back to `EMAIL_FROM`, then
  `reports@example.com` for unconfigured previews.
- `DEFAULT_FALLBACK_EMAIL`: used when Clerk recipient lookup produces no
  recipients, in the task's lookup-error fallback, or when the notification tool
  is called without recipients. The unset default is `test@example.com`. Review
  lookup warnings; a partial result can still be used when one Clerk query fails.
- `DEV_OVERRIDE_EMAIL`: redirects non-dry-run sends through `EmailService` to a
  development address when configured. It does not discover recipients.
- `RECIPIENTS_DIR`: legacy JSON loader and sender-classification compatibility.
  It is not required for normal Clerk reminders or monthly-cycle v2 ingestion.
  Only users of those older interfaces need private JSON; do not create it as a
  normal setup requirement. Without an override they use tracked example data.

Normal reminders use Clerk: Regular RC officers; Open and Association officers
plus committee chairs, deduplicated. Association does not mean all residents.
Task callers may supply explicit recipients. Low-level send tools use the list
supplied by their caller. Operational Clerk data, recipient exports, and any
legacy real-recipient JSON must stay out of Git.

## Gmail authentication and external actions

The Scribe-specific `src/scribe/google_auth` helper is locally provisioned and
intentionally excluded from Git, along with credentials and tokens. Obtain it
through the trusted maintainer. The repository currently lacks a complete
fresh-clone provisioning mechanism; installing the third-party `google-auth`
package does not supply the Scribe helper.

Gmail `userId="me"` refers to the account authorized by the OAuth token.
`EMAIL_FROM` is a configured sender header/recognition value, not authentication.
The authorized account and permitted sender identity must be configured
consistently. Applied ingestion downloads attachments and adds labels; other
email paths can send or mark mail read. Do not assume universal read-only scopes.

The reminder GUI listens on loopback by default. Remote access needs an
appropriate protected connection; do not expose its Flask development server or
debugger publicly. Verify dry-run state before using the send interface.

## Repository and log hygiene

- Keep private addresses, credentials, tokens, attachments, generated meeting
  outputs, recipient/reminder archives, and private operational notes out of Git.
- Tracked recipient examples use `example.com`; tests enforce example-only data.
- Cycle `report_state.json` is tracked source policy. Ordinary cycle input and
  generated manifests remain local; manifests are derived, not policy storage.
- Keep private recovery archives and history references local; never push them.
- Some logs/audits mask addresses, but redaction is not universal. DEBUG recipient
  audits and some legacy/error logs can disclose operational details. Inspect
  logs before sharing them or uploading CI artifacts.

## Secret-scanner coverage and limits

The optional `scripts/githooks/pre-commit` hook runs gitleaks if installed and
then `scripts/scan_secrets.py`. Enabling it uses
`git config core.hooksPath scripts/githooks` after making the hook executable.
The hook's gitleaks invocation uses `--no-git`; it is not a history audit.

`.github/workflows/security.yml` runs gitleaks with full checkout history and
uses the Python fallback on gitleaks failure. A passing fallback is not proof
that an earlier gitleaks finding was harmless.

The fallback scans selected text extensions in the working filesystem, not a
specified Git commit range or just staged files. It does not implement Git's
ignore rules; its path-component exclusions do not reliably exclude nested paths
listed with slashes. It can inspect local material, miss binary/archive content,
miss unquoted secrets or credentials embedded in connection URLs, and produce
false positives. Its printed context is not guaranteed safe to share. Do not
regard a passing scan as proof that a tree or its history is publication-safe.
Review the intended diff and historical blobs when publishing unpublished work.

## Incident response

If a credential may have leaked, rotate it and coordinate remediation. Deleting
a file or rewriting Git history does not revoke a credential or remove copies
already obtained by others.
