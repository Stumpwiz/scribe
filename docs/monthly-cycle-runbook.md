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

The normal ingestion path is `run_cycle → cli.ingest → stage_attachments_v2`.
It uses report filename/subject inference and can use Clerk sender-to-office
lookup; it does not require recipient JSON files.

A nonzero staging or collection result stops the command before later steps by
default. Ordinary missing reports can cause a nonzero collection result even
when placeholders are available. Review the summary before continuing. Adding
`--keep-going` permits downstream processing but does not turn failures into
successes: the overall command still returns a failure status. After reviewing
missing reports, you can instead run the explicit local `format_all` and
`build_minutes` commands below; they do not repeat Gmail ingestion.

## Agenda Preparation and Reminder Email Generation

Launch the Reminder GUI with:

```bash
DRY_RUN=true uv run python scripts/run_reminder_gui.py
```

This explicit environment setting selects preview delivery. The launcher only
sets `DRY_RUN=true` when the variable is absent and `--allow-send` is not used;
an inherited `DRY_RUN=false` is not overridden. For an authorized real send,
configure `DRY_RUN=false`, use `--allow-send`, and verify the effective state and
previewed recipients/agenda before sending. These environment prefixes use shell
syntax; IDE run configurations can set the same variable directly.

Normal reminders query Clerk dynamically:

| Meeting type | Recipients |
| --- | --- |
| Regular RC | Residents Council Officers mailing list |
| Open RC | Residents Council Officers + committee chairs, deduplicated |
| Association | Residents Council Officers + committee chairs, deduplicated |

Association reminders do not automatically go to all residents. The task-based
workflow may supply nonempty `email_recipients`; otherwise it uses the same Clerk
lookup. Low-level notification/send tools use their caller's `recipients`/`to`
list and do not independently discover it. Review lookup warnings and fallback
recipients: an empty Clerk result uses `DEFAULT_FALLBACK_EMAIL` (unset default
`test@example.com`), and a partial query failure can leave a partial list.

`RECIPIENTS_DIR` is only for retained legacy JSON interfaces and sender
classification, not normal reminders or monthly-cycle ingestion. Missing private
JSON is not a defect in these supported workflows; do not create it for normal
setup. `EMAIL_FROM` is sender identity/reminder recognition, while
`REPORT_SUBMISSION_EMAIL` selects the printed submission/correction address and
falls back to `EMAIL_FROM`. See [Security](SECURITY.md) for other fallbacks and
development redirection.

### Remote development (JetBrains Gateway)

The default host, `127.0.0.1`, is appropriate only when the browser runs on
the same machine as the GUI. When the GUI runs on the development host through JetBrains
Gateway from another computer, launch it with:

```bash
DRY_RUN=true uv run python scripts/run_reminder_gui.py --host 0.0.0.0
```

Then open `http://<development-host>:5000` in the client browser (for example,
`http://192.0.2.10:5000`). Clicking the `127.0.0.1` hyperlink printed in the
terminal opens the client's localhost, not the development host, so it will not reach
the GUI.

Use this all-interface binding only on a protected development network. Prefer
a protected tunnel to loopback when available; do not expose Flask debug mode.

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

Each fragment contains narrative paragraphs only. Do not include officer
labels/headings or appendix-reference sentences; those remain controlled by the
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

When a message includes a recognized document attachment, v2 staging excludes
image parts explicitly marked `Content-Disposition: inline`. Image-only
submissions and images explicitly attached as attachments remain eligible.

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

Choose `--type regular`, `--type open`, or `--type association` for the actual
meeting. The example above is Regular, not a default for every meeting.

### Intentionally Omit a Written Appendix

Meeting delivery belongs in the manually authored minutes prose. To record that
an office intentionally has no written appendix for a cycle, create the optional
source input `src/scribe/input/cycles/YYYY-MM/report_state.json`:

```json
{
  "offices": {
    "library": {"appendix": "none"}
  }
}
```

This is an example policy, not a standing rule for the Library. Only
`{"appendix": "none"}` is supported; remove an office from this input to restore
its usual processing. An absent file or unspecified office keeps existing
behavior. Invalid policies and unknown office names fail before output writes.

Both `collect_pdfs` and `format_all` automatically read this cycle input, including
when invoked by `run_cycle`. Collection skips the office before selecting or
converting files and before placeholder filling. Formatting records an explicit
`status: "omitted"` entry with `source_pdf: null`, `pages: 0`, `png_files: []`, and
`placeholder_used: false`. Intentional omissions are reported separately from
missing reports and failures. Existing source/PDF/PNG files are retained but do
not override the policy or enter the Open-minutes appendix.

Cycle `report_state.json` files are version-controlled source policy because
reproducing a cycle requires its appendix decisions. The narrow `.gitignore`
exception covers only `src/scribe/input/cycles/YYYY-MM/report_state.json`; other
input material remains ignored. Include policy changes in the cycle's reviewed
Git changes so a checkout restores the decisions along with the code. Generated
`manifest.json` files remain derived output, not the source of this policy.
Do not hand-edit them to record omissions. Rerun collection, formatting, and
minutes building after changing the policy. An intentional `appendix: "none"`
omission is distinct from an ordinary missing written report. Unspecified
missing reports retain their existing placeholder and collector exit-code
behavior, including the Open-meeting wing-placeholder exclusions.

Review manually authored appendix-reference clauses along with meeting prose.
The Dining and Environment/Landscape clauses in the current Open template use
the actual selected appendix offices; the other existing clauses remain manual.

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

Ordinary missing non-wing reports receive the existing placeholder treatment.
Open minutes include their valid placeholder PNGs in the normal appendix order,
but continue to exclude wing-report placeholders; received wing reports remain
eligible. Entries with failed status or missing PNG files are still skipped.
Only offices in the cycle's open appendix inventory are selected; a manifest
entry alone does not add an office to that inventory.

### Build Minutes for the Meeting Type

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
  label/heading and agree with the template's appendix-reference wording.
- Console summary reviewed.
- Gmail messages labeled `Scribe/Incoming`.

## Pre-Distribution Minutes Checklist

- All expected reports appear.
- Known non-submissions and committees that did not meet are handled
  appropriately.
- Late reports appear in the appendix.
- Expected officer labels/headings appear in the selected template (Open uses
  description-list labels rather than five officer subsection headings).
- Officer narratives appear beneath the correct headings.
- Appendix-reference clauses agree with actual selected appendices. Intentional
  omissions have neither an appendix nor a missing-report placeholder, while
  report delivery remains recorded accurately in the meeting prose.
- Every multi-page report is complete.
- No literal placeholders such as `[director-8]` appear.
- No unexpected blank appendix pages appear.
- Formatter manifest PNG filenames exist on disk under
  `src/scribe/output/cycles/YYYY-MM/png/`.
- Final PDF opens, and page order is correct.

## Draft-Minutes Distribution

After draft review, the Secretary obtains the current cut-and-paste mailing list
from Clerk: Regular RC minutes go to RC officers; Open RC and Association minutes
go to RC officers plus committee chairs. Association does not mean all residents.
Review/deduplicate the combined list and distribute only when authorized.
Do not put addresses in source documents or Git. This manual procedure is
separate from automated reminder delivery; the monthly cycle does not email the
draft automatically. Website publication is a separate reviewed operation.

## Cycle Artifact Closeout

Confirm review, distribution, and intended website publication before deleting
superseded artifacts. Preserve the reviewed full-quality PDF and the compacted
distributed/published copy, with a clear local record of which is which.

Retain received originals, canonical report PDFs used as stable formatting
inputs, tracked cycle `report_state.json`, and manually authored cycle inputs
needed for provenance. This includes officer fragments under the output tree;
they are not regenerated merely because their directory is ignored.

After verification/publication, superseded drafts, stale report images,
XeLaTeX `.aux`/`.log`/`.toc` files, and temporary correction backups with no
unique source material can be removed. Review other generated intermediates
before removal. Keep source logos/templates and useful final assets; generated
`.tex` and the final manifest can provide build provenance even though the
manifest is derived. This closeout guidance is not authorization to bulk-delete
older cycles or historical records.

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
