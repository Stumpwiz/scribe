# Security guide

This project handles email and attachments; follow these practices to protect sensitive data.

Configuration
- Use a local .env (gitignored) to set:
  - RECIPIENTS_DIR: Absolute path to a private directory with real recipient lists (council_members.json, committee_chairs.json), e.g., instance/recipients.
  - DEFAULT_FALLBACK_EMAIL: Safe fallback (e.g., notify@example.com).
  - EMAIL_FROM: Sender mailbox used by EmailService.
- Keep Google API credentials and tokens out of Git. Store them locally in a private directory.

Repository hygiene
- Private recipients directory is ignored by .gitignore. Do not commit real email lists.
- Sample recipients under src/scribe/assets/recipients use example.com and are enforced by tests.
- Email addresses are masked in logs to avoid leaking PII in logs and CI artifacts.

Local pre-commit scanning
- Optional but recommended: enable pre-commit scanning before committing.
- One-time setup:
  - Make hook executable: chmod +x scripts/githooks/pre-commit
  - Point Git to use the repo hooks: git config core.hooksPath scripts/githooks
- The hook will:
  - Run gitleaks if installed (brew install gitleaks or download from GitHub releases)
  - Run a Python-based fallback scanner (scripts/scan_secrets.py)

CI scanning
- GitHub Actions workflow .github/workflows/security.yml runs gitleaks on push/PR.
- If gitleaks fails or is unavailable, the fallback Python scanner runs and will fail the job on findings.

Incident response
- If you suspect a secret leak:
  - Rotate affected credentials immediately.
  - Purge tokens and regenerate OAuth credentials where necessary.
  - Force-push removal is not sufficient; assume compromise and rotate.
