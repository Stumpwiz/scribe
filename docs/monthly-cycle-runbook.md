# Monthly Cycle Runbook

This runbook is for operating Scribe once a month. It documents implemented
behavior separately from manual Gmail closeout steps. Related change history is
in [../CHANGELOG.md](../CHANGELOG.md).

## Gmail State Before Beginning

Completed prior-cycle report messages should have:

- `Scribe/Archive/YYYY-MM`
- no `Scribe/Incoming`
- no `INBOX`

New current-cycle reports should normally have:

- `INBOX`
- no Scribe label before staging

`Scribe/Incoming` is a staging marker, not an archive. `run_cycle.py --apply`
adds `Scribe/Incoming`, but it does not remove `INBOX` and does not apply an
archive label. Gmail archive closeout remains manual.

## Preview Command

Dry-run mode is the default. Omit `--apply` when previewing.

```bash
uv run python -m src.scribe.cli.run_cycle \
  --cycle YYYY-MM
```

For a cleaner staging-only preview, skip collect and format:

```bash
uv run python -m src.scribe.cli.run_cycle \
  --cycle YYYY-MM \
  --skip-collect \
  --skip-format
```

Use the staging-only preview when checking Gmail classification and attachment
office routing without downstream PDF or PNG noise. Missing PDFs during an
initial dry run are expected because dry-run staging saves no attachments.

## Applied Run

```bash
uv run python -m src.scribe.cli.run_cycle \
  --cycle YYYY-MM \
  --apply
```

This command:

- downloads attachments into `src/scribe/output/cycles/YYYY-MM/originals/`;
- applies `Scribe/Incoming`;
- collects PDFs into `src/scribe/output/cycles/YYYY-MM/pdf/`;
- formats downstream artifacts.

## Agenda Preparation and Reminder Email Generation

Launch the Reminder GUI with:

```bash
uv run python scripts/run_reminder_gui.py
```

### Remote development (JetBrains Gateway)

The default host, `127.0.0.1`, is appropriate only when the browser runs on
the same machine as the GUI. When the GUI runs on the development host through JetBrains
Gateway from another computer, launch it with:

```bash
uv run python scripts/run_reminder_gui.py --host 0.0.0.0
```

Then open `http://<development-host>:5000` in the client browser (for example,
`http://192.0.2.10:5000`). Clicking the `127.0.0.1` hyperlink printed in the
terminal opens the client's localhost, not the development host, so it will not reach
the GUI.

## Post-Meeting Minutes Production

After the meeting recording has been transcribed and summarized, review:

```text
src/scribe/output/cycles/YYYY-MM/transcript.txt.summary.md
```

Use the summary and meeting record to prepare minutes body edits and any officer
narrative fragments.

### Prepare Officer Narrative Fragments

Prepare optional LaTeX fragments in:

```text
src/scribe/output/cycles/YYYY-MM/officer_reports/
```

Use these filenames when the corresponding officer narrative is available:

- `president.tex`
- `vicePresident.tex`
- `treasurer.tex`
- `secretary.tex`
- `administrativeAssistant.tex`

Each fragment contains narrative paragraphs only. Do not include subsection
headings or appendix-reference sentences; those remain controlled by the
minutes template. Review every fragment for factual accuracy and make it
LaTeX-safe before building. Missing fragment files are allowed and do not
prevent a build.

### Process Late Reports

When a new, unlabeled report arrives after an earlier staging run, run the
normal applied cycle command again:

```bash
uv run python -m src.scribe.cli.run_cycle \
  --cycle YYYY-MM \
  --apply
```

Already-staged Gmail messages are skipped during the normal applied run. Newly
arrived unlabeled reports are staged.

Then rebuild downstream artifacts:

```bash
uv run python -m src.scribe.cli.collect_pdfs \
  --cycle YYYY-MM \
  --overwrite
```

```bash
uv run python -m src.scribe.cli.format_all \
  --cycle YYYY-MM \
  --input-dir src/scribe/output/cycles/YYYY-MM/pdf
```

```bash
uv run python -m src.scribe.cli.build_minutes \
  --cycle YYYY-MM \
  --type regular
```

`collect_pdfs --overwrite` refreshes collected PDFs. `format_all` refreshes PNG
appendix assets and `manifest.json`. `build_minutes` rebuilds the final PDF
from the current manifest and officer fragments.

The Nominating Committee report is expected only for the September cycle. In
the open-minutes appendix it follows the standing committee reports (after
Special Events & Trips) and precedes the Executive Director and wing reports;
the ordering of all other reports is unchanged.

### Formatter Naming

Formatter output names are based on emitted, nonblank report pages after blank
or effectively blank pages have been suppressed. Physical PDF page count may
differ from emitted report-page count.

```text
one emitted page:
  wingE.png

multiple emitted pages:
  director-1.png
  director-2.png
  ...
```

### Manifest-Driven Pagination

Do not manually edit report page counts in the minutes template. The formatter
manifest supplies the ordered PNG filenames for each report, and the minutes
templates generate one `\reportpage` entry per listed file.

The generated appendix syntax is:

```tex
\reportbegin{Report Title}{reportLabel}
\reportpage{report-page.png}
\reportend
```

This removes the former practical limit that came from fixed positional page
arguments in the old `\report` macro. The old macro remains only as a
compatibility wrapper.

### Build Regular Minutes

After reports, manifest, template body edits, and officer fragments are ready:

```bash
uv run python -m src.scribe.cli.build_minutes \
  --cycle YYYY-MM \
  --type regular
```

## Verification Checklist

- All candidate messages classified.
- No unexpected `unknown` office.
- Attachments saved under the correct office directories.
- Multi-report emails split correctly by attachment.
- Expected PDFs created.
- Officer narrative fragments, when present, appear beneath the correct officer
  subsection heading and before the appendix-reference sentence.
- Console summary reviewed.
- Gmail messages labeled `Scribe/Incoming`.

## Pre-Distribution Minutes Checklist

- All expected reports appear.
- Known non-submissions and committees that did not meet are handled
  appropriately.
- Late reports appear in the appendix.
- All five officer subsection headings appear.
- Officer narratives appear beneath the correct headings.
- Appendix-reference sentences remain in place.
- Every multi-page report is complete.
- No literal placeholders such as `[director-8]` appear.
- No unexpected blank appendix pages appear.
- Formatter manifest PNG filenames exist on disk under
  `src/scribe/output/cycles/YYYY-MM/png/`.
- Final PDF opens, and page order is correct.

## Recovery After a Classification Fix

Use this procedure when messages were already staged and labeled before a
classification fix.

1. Delete only affected stale office directories under
   `src/scribe/output/cycles/YYYY-MM/originals/`.
1. Delete affected stale PDFs under `src/scribe/output/cycles/YYYY-MM/pdf/`.
1. Force a staging-only rerun:

```bash
uv run python -m src.scribe.cli.run_cycle \
  --cycle YYYY-MM \
  --apply \
  --force \
  --skip-collect \
  --skip-format \
  --max 25
```

1. Recollect with overwrite:

```bash
uv run python -m src.scribe.cli.collect_pdfs \
  --cycle YYYY-MM \
  --overwrite
```

1. Reformat:

```bash
uv run python -m src.scribe.cli.format_all \
  --cycle YYYY-MM \
  --input-dir src/scribe/output/cycles/YYYY-MM/pdf
```

`--force` restages already-labeled messages. It overwrites staged originals
only; it does not overwrite collected PDFs. Removing `Scribe/Incoming` is
unnecessary, and Gmail label application is idempotent. Stale misfiled
originals must be removed explicitly.

## End-of-Cycle Gmail Closeout

After the cycle is complete, close out Gmail manually:

- apply `Scribe/Archive/YYYY-MM`;
- remove `Scribe/Incoming`;
- archive from Inbox by removing `INBOX`;
- optionally mark read;
- do not delete the messages.

## Troubleshooting

Direct execution of `src/scribe/cli/run_cycle.py` may fail with:

```text
ModuleNotFoundError: No module named 'src'
```

Use module invocation instead:

```bash
uv run python -m src.scribe.cli.run_cycle \
  --cycle YYYY-MM
```

A dry run after messages are already labeled may report
`already_labeled_not_newer`. Use `--force` only when intentionally restaging
after a code or classification correction.
