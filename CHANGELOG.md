# Changelog

## 2026-07-19

### Minutes Production

- Made report appendix pagination manifest-driven. Minutes templates now use
  the formatter manifest's ordered `png_files` lists and generate one
  `\reportpage` entry per file.
- Replaced fixed-position report page arguments with `\reportbegin`,
  `\reportpage`, and `\reportend`, removing the former practical seven-page
  report limit. The old `\report` macro remains as a compatibility wrapper.
- Added cycle-local officer narrative fragments for President, Vice President,
  Treasurer, Secretary, and Administrative Assistant reports under
  `src/scribe/output/cycles/YYYY-MM/officer_reports/`.
- Kept officer subsection headings and appendix-reference sentences controlled
  by the minutes templates.
- Updated formatter naming to use emitted, nonblank pages: one emitted page
  writes `<office>.png`; multiple emitted pages write `<office>-1.png`,
  `<office>-2.png`, and so on.
- Added manifest validation so every listed PNG must exist on disk.
- Verified the 2026-07 regular minutes built successfully with all nine
  Executive Director report pages, Wing E rendered correctly, the late Wing F
  report included, and all five officer narratives included.

## 2026-07-13

### Gmail Ingestion

- Established the canonical monthly cycle invocation as:
  `uv run python -m src.scribe.cli.run_cycle`.
- Added Environment/Landscape aliases: `E/L`, `E:L`, `Env/Land`,
  `Environment/Landscape`, and `Environment & Landscape`.
- Added per-attachment office inference during Gmail staging:
  - inspect each attachment filename first;
  - use the attachment-derived office when recognized;
  - otherwise fall back to message-level inference;
  - record `office` and `office_inference_reason` in preview/log output.
- Added Employee Appreciation aliases: `EA C`, `EAC`,
  `Employee Appreciation`, `Employee Appreciation Committee`, and
  `Employee Appreciation Liaison`.
- Documented alias precedence so specific committee aliases take precedence over
  generic officer terms when both appear, as in
  `Treasurer's Liaison Report EA C 7-9-26.docx`.
- Added regression tests for Environment/Landscape abbreviations, Dining and
  Wing D reports attached to one email, Treasurer and Employee Appreciation
  reports, and the actual `EA C` filename.
- Latest focused verification:
  `uv run pytest -q tests/test_ingest_office_inference.py` returned
  `9 passed, 1 warning`.

Operator instructions are in
[docs/monthly-cycle-runbook.md](docs/monthly-cycle-runbook.md).
