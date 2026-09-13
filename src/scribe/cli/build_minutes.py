"""Build meeting minutes PDF from LaTeX Jinja templates.

Usage:
    python -m src.scribe.cli.build_minutes --cycle YYYY-MM --type regular|open|association \
        [--out <path>] [--dry-run] [--engine xelatex|pdflatex] [--runs 2]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from ..meeting.meeting_dates import compute_meeting_dates
from ..report_inventory import ordered_reports_for_cycle

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
except ImportError as exc:  # pragma: no cover - dependency check
    raise SystemExit(
        "jinja2 is required for build_minutes. Install dependencies (e.g., pip install -r requirements.txt)."
    ) from exc

DEFAULT_CYCLES_ROOT = Path("src/scribe/output/cycles")
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"
LOGO_JPG = Path(__file__).resolve().parent.parent / "assets" / "images" / "residentCouncilLogoSmall.jpg"
LOGO_PDF = Path(__file__).resolve().parent.parent / "assets" / "images" / "residentCouncilLogoSmall.pdf"
TEMPLATE_MAP: Dict[str, str] = {
    "regular": "minutes_regular.tex.j2",
    "open": "minutes_open.tex.j2",
    "association": "minutes_association.tex.j2",
}
ENGINE_CHOICES = ("xelatex", "pdflatex")
OPEN_APPENDIX_ORDER = [
    "president",
    "vicePresident",
    "treasurer",
    "secretary",
    "administrativeAssistant",
    "buildingMaintenance",
    "dining",
    "employeeAppreciation",
    "environmentLandscape",
    "finance",
    "library",
    "scholarship",
    "specialEventsAndTrips",
    "director",
    "wingA",
    "wingB",
    "wingC",
    "wingD",
    "wingE",
    "wingF",
    "wingG",
]

OPEN_APPENDIX_TITLES = {
    "president": "President's Report",
    "vicePresident": "Vice President's Report",
    "treasurer": "Treasurer's Report",
    "secretary": "Secretary's Report",
    "administrativeAssistant": "Administrative Assistant's Report",
    "buildingMaintenance": "Building Maintenance Report",
    "dining": "Dining Report",
    "employeeAppreciation": "Employee Appreciation Report",
    "environmentLandscape": "Environment/Landscape Report",
    "finance": "Finance Report",
    "library": "Library Report",
    "scholarship": "Scholarship Report",
    "specialEventsAndTrips": "Special Events \\& Trips Report",
    "nominatingCommittee": "Nominating Committee Report",
    "director": "Executive Director's Report",
    "wingA": "Liffey A Wing Report",
    "wingB": "Liffey B Wing Report",
    "wingC": "Liffey C Wing Report",
    "wingD": "Killarney D Wing Report",
    "wingE": "Shannon E Wing Report",
    "wingF": "Shannon F Wing Report",
    "wingG": "Shannon G Wing Report",
}

OFFICER_REPORT_FILENAMES = {
    "president": "president.tex",
    "vicePresident": "vicePresident.tex",
    "treasurer": "treasurer.tex",
    "secretary": "secretary.tex",
    "administrativeAssistant": "administrativeAssistant.tex",
}

LAST_RESULT: Dict[str, object] = {}


def validate_cycle(cycle: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}", cycle or ""):
        raise ValueError("--cycle must be in YYYY-MM format")
    return cycle


def resolve_cycle_root(cycle: str) -> Path:
    root = (DEFAULT_CYCLES_ROOT / cycle).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Cycle root not found: {root}")
    return root


def resolve_template(minutes_type: str) -> Path:
    filename = TEMPLATE_MAP[minutes_type]
    primary = TEMPLATE_DIR / filename
    if primary.exists():
        return primary

    # Fallback: search within templates dir (no ripgrep per instructions).
    for path in TEMPLATE_DIR.rglob(filename):
        if path.is_file():
            return path

    raise FileNotFoundError(f"Template not found: {filename} under {TEMPLATE_DIR}")


def choose_engine(preferred: Optional[str]) -> str:
    if preferred:
        if preferred not in ENGINE_CHOICES:
            raise ValueError(f"--engine must be one of {ENGINE_CHOICES}")
        if shutil.which(preferred) is None:
            raise FileNotFoundError(f"Requested engine not available: {preferred}")
        return preferred

    if shutil.which("xelatex"):
        return "xelatex"
    if shutil.which("pdflatex"):
        return "pdflatex"
    raise FileNotFoundError("No LaTeX engine found (xelatex or pdflatex)")


def ensure_logo(cycle_root: Path) -> Path:
    if LOGO_JPG.is_file():
        source = LOGO_JPG
    elif LOGO_PDF.is_file():
        source = LOGO_PDF
    else:
        raise FileNotFoundError(
            f"Logo not found at {LOGO_JPG} or {LOGO_PDF}"
        )

    dest = cycle_root / source.name
    shutil.copy2(source, dest)
    return dest


def load_manifest(cycle_root: Path) -> Dict[str, Any]:
    manifest_path = cycle_root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Manifest is not valid JSON: {manifest_path}") from exc


def _fallback_title_from_office(office: str) -> str:
    if office in OPEN_APPENDIX_TITLES:
        return OPEN_APPENDIX_TITLES[office]
    # Convert lowerCamel/snake-like stems to a readable title.
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", office or "").replace("_", " ").strip()
    if not spaced:
        return "Report"
    return f"{spaced[:1].upper()}{spaced[1:]} Report"


def _safe_label(office: str, used: set[str]) -> str:
    raw = re.sub(r"[^a-zA-Z0-9_-]+", "-", office or "").strip("-") or "report"
    label = raw
    suffix = 2
    while label in used:
        label = f"{raw}-{suffix}"
        suffix += 1
    used.add(label)
    return label


def is_wing_office(office: str) -> bool:
    return bool(re.fullmatch(r"wing[A-G]", office or ""))


def build_open_appendix_reports(manifest: Dict[str, Any], cycle_root: Path) -> tuple[list[Dict[str, Any]], list[str]]:
    offices = manifest.get("offices")
    if not isinstance(offices, dict):
        return [], ["manifest.offices is missing or not an object; no appendix reports selected"]

    reports: list[Dict[str, Any]] = []
    skipped: list[str] = []
    used_labels: set[str] = set()
    png_root = cycle_root / "png"
    cycle = str(manifest.get("cycle") or "")
    order = ordered_reports_for_cycle(OPEN_APPENDIX_ORDER, cycle) if re.fullmatch(r"\d{4}-\d{2}", cycle) else OPEN_APPENDIX_ORDER
    for office in order:
        entry = offices.get(office)
        if entry is None:
            skipped.append(f"{office}: skipped (no assets present)")
            continue
        if not isinstance(entry, dict):
            skipped.append(f"{office}: skipped (manifest entry is not an object)")
            continue
        if entry.get("status") not in (None, "ok"):
            skipped.append(f"{office}: skipped (status={entry.get('status')})")
            continue
        placeholder_used = bool(entry.get("placeholder_used", False))
        if placeholder_used and is_wing_office(str(office)):
            skipped.append(f"{office}: skipped (placeholder wing report omitted from open minutes)")
            continue
        png_files = entry.get("png_files") or []
        if not isinstance(png_files, list):
            skipped.append(f"{office}: skipped (png_files is not a list)")
            continue
        normalized_png_files = [str(name).strip() for name in png_files if str(name).strip()]
        existing_png_files: list[str] = []
        missing_png_files: list[str] = []
        for png_name in normalized_png_files:
            png_path = png_root / png_name
            if png_path.is_file():
                existing_png_files.append(png_name)
            else:
                missing_png_files.append(png_name)
        if missing_png_files:
            skipped.append(f"{office}: skipped (no assets present)")
            continue
        if not existing_png_files:
            skipped.append(f"{office}: skipped (no assets present)")
            continue
        title = str(entry.get("title") or "").strip() or _fallback_title_from_office(str(office))
        office_str = str(office).strip()
        reports.append({
            "office": office_str,
            "label": _safe_label(office_str, used_labels),
            "title": title,
            "png_files": existing_png_files,
            "placeholder_used": bool(entry.get("placeholder_used", False)),
            "status": entry.get("status"),
            "source_pdf": entry.get("source_pdf"),
        })
    return reports, skipped


def report_pages_from_manifest(
        manifest: Dict[str, Any],
        office: str,
        fallback_pages: Optional[list[str]] = None,
) -> list[str]:
    offices = manifest.get("offices")
    if isinstance(offices, dict):
        entry = offices.get(office)
        if isinstance(entry, dict) and isinstance(entry.get("png_files"), list):
            return [str(name).strip() for name in entry["png_files"] if str(name).strip()]
    return [str(name).strip() for name in (fallback_pages or []) if str(name).strip()]


def officer_report_inputs(cycle_root: Path) -> Dict[str, str]:
    report_dir = cycle_root / "officer_reports"
    inputs: Dict[str, str] = {}
    for office, filename in OFFICER_REPORT_FILENAMES.items():
        path = report_dir / filename
        if path.is_file():
            inputs[office] = path.relative_to(cycle_root).as_posix()
    return inputs


def render_meeting_dates(template_dir: Path, output_dir: Path, context: Dict[str, str]) -> Path:
    env = Environment(
        loader=FileSystemLoader(str(template_dir.resolve())),
        autoescape=False,
        undefined=StrictUndefined,
        # Avoid collision with LaTeX macro args like {#1} which Jinja thinks is a comment start.
        comment_start_string="((#",
        comment_end_string="#))",
    )
    template = env.get_template("meeting_dates.tex.j2")
    rendered = template.render(**context)
    output_path = output_dir / "meeting_dates.tex"
    output_path.write_text(rendered, encoding="utf-8")
    return output_path


def render_template(
        template_path: Path,
        cycle_root: Path,
        minutes_type: str,
        logo_filename: str,
        meeting_dates: Dict[str, str],
        manifest: Dict[str, Any],
        appendix_reports: list[Dict[str, Any]],
) -> Path:
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent.resolve())),
        autoescape=False,
        undefined=StrictUndefined,
        # Avoid collision with LaTeX macro args like {#1} which Jinja thinks is a comment start.
        comment_start_string="((#",
        comment_end_string="#))",
    )
    template = env.get_template(template_path.name)

    context = {
        "cycle": cycle_root.name,
        "cycle_root": str(cycle_root),
        # Templates define \def\reportsDir{{ reportsDir }}; keep absolute keys for compatibility.
        "reportsDir": "png",
        "reports_dir": "png",
        "logopath": logo_filename,
        "logoPath": logo_filename,
        "pdfDir": str(cycle_root / "pdf"),
        "pdf_dir": str(cycle_root / "pdf"),
        "today": _dt.date.today().isoformat(),
        "minutes_type": minutes_type,
        "manifest": manifest,
        "appendix_reports": appendix_reports if minutes_type == "open" else [],
        "appendix_offices": {report["office"] for report in appendix_reports} if minutes_type == "open" else set(),
        "officer_report_inputs": officer_report_inputs(cycle_root),
        "report_pages": lambda office, fallback_pages=None: report_pages_from_manifest(
            manifest,
            str(office),
            fallback_pages,
        ),
        **meeting_dates,
    }

    rendered = template.render(**context)
    tex_path = cycle_root / f"minutes_{minutes_type}.tex"
    tex_path.write_text(rendered, encoding="utf-8")
    return tex_path


def compile_latex(engine: str, tex_path: Path, runs: int) -> subprocess.CompletedProcess:
    # Compile inside the cycle root to keep aux files local.
    cmd = [engine, "-interaction=nonstopmode", tex_path.name]
    result: Optional[subprocess.CompletedProcess] = None
    for _ in range(max(1, runs)):
        result = subprocess.run(cmd, cwd=tex_path.parent, check=False, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            break
    return result  # type: ignore[return-value]


def build_minutes(args: argparse.Namespace) -> int:
    minutes_type = args.type
    cycle = validate_cycle(args.cycle)
    cycle_root = resolve_cycle_root(cycle)
    template_path = resolve_template(minutes_type)

    try:
        logo_path = ensure_logo(cycle_root)
    except Exception as exc:  # noqa: BLE001
        print(f"Logo copy failed: {exc}")
        LAST_RESULT.update({
            "success": False,
            "stage": "asset",
            "error": str(exc),
            "cycle_root": str(cycle_root),
            "logo_sources": [str(LOGO_JPG), str(LOGO_PDF)],
        })
        return 1

    meeting_dates = compute_meeting_dates(cycle, minutes_type)
    try:
        manifest = load_manifest(cycle_root)
    except Exception as exc:  # noqa: BLE001
        print(f"Manifest load failed: {exc}")
        LAST_RESULT.update({
            "success": False,
            "stage": "manifest",
            "error": str(exc),
            "cycle_root": str(cycle_root),
            "manifest_path": str(cycle_root / "manifest.json"),
        })
        return 1

    appendix_reports: list[Dict[str, Any]] = []
    skipped_appendix_entries: list[str] = []
    if minutes_type == "open":
        appendix_reports, skipped_appendix_entries = build_open_appendix_reports(manifest, cycle_root)
        print(f"Appendix reports included: {len(appendix_reports)}")
        for report in appendix_reports:
            print(
                f"  + {report['office']} -> {report['title']} "
                f"({len(report.get('png_files') or [])} page(s))"
            )
        if skipped_appendix_entries:
            print(f"Appendix reports skipped: {len(skipped_appendix_entries)}")
            for item in skipped_appendix_entries:
                print(f"  - {item}")

    try:
        render_meeting_dates(TEMPLATE_DIR, cycle_root, meeting_dates)
        tex_path = render_template(
            template_path,
            cycle_root,
            minutes_type,
            logo_path.name,
            meeting_dates,
            manifest,
            appendix_reports,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Render failed: {exc}")
        LAST_RESULT.update({
            "success": False,
            "stage": "render",
            "error": str(exc),
            "cycle_root": str(cycle_root),
            "template": str(template_path),
        })
        return 1

    pdf_target = Path(args.out) if args.out else cycle_root / f"minutes_{minutes_type}_{cycle}.pdf"
    engine_used: Optional[str] = None
    compile_result: Optional[subprocess.CompletedProcess] = None

    if not args.dry_run:
        try:
            engine_used = choose_engine(args.engine)
            compile_result = compile_latex(engine_used, tex_path, args.runs)
        except Exception as exc:  # noqa: BLE001
            print(f"Compile failed: {exc}")
            LAST_RESULT.update({
                "success": False,
                "stage": "compile",
                "error": str(exc),
                "cycle_root": str(cycle_root),
                "template": str(template_path),
                "tex": str(tex_path),
                "engine": engine_used,
            })
            return 1

        if compile_result and compile_result.returncode != 0:
            print("LaTeX compilation failed")
            print(compile_result.stdout)
            print(compile_result.stderr)
            LAST_RESULT.update({
                "success": False,
                "stage": "compile",
                "error": "latex_return_nonzero",
                "returncode": compile_result.returncode,
                "stdout": compile_result.stdout,
                "stderr": compile_result.stderr,
                "cycle_root": str(cycle_root),
                "template": str(template_path),
                "tex": str(tex_path),
                "engine": engine_used,
            })
            return compile_result.returncode or 1

        generated_pdf = tex_path.with_suffix(".pdf")
        try:
            generated_pdf.replace(pdf_target)
        except FileNotFoundError:
            print(f"Expected PDF not found: {generated_pdf}")
            LAST_RESULT.update({
                "success": False,
                "stage": "rename",
                "error": "pdf_missing",
                "cycle_root": str(cycle_root),
                "template": str(template_path),
                "tex": str(tex_path),
                "engine": engine_used,
                "expected_pdf": str(generated_pdf),
            })
            return 1
    else:
        engine_used = args.engine or ("xelatex" if shutil.which("xelatex") else "pdflatex")

    LAST_RESULT.update({
        "success": True,
        "stage": "dry" if args.dry_run else "done",
        "cycle": cycle,
        "cycle_root": str(cycle_root),
        "template": str(template_path),
        "tex": str(tex_path),
        "pdf": str(pdf_target),
        "engine": engine_used,
        "runs": args.runs,
        "dry_run": bool(args.dry_run),
        "appendix_reports_included": len(appendix_reports),
        "appendix_reports_skipped": skipped_appendix_entries,
    })

    print("--- build_minutes summary ---")
    print(f"cycle_root: {cycle_root}")
    print(f"template:   {template_path}")
    print(f"tex out:    {tex_path}")
    print(f"pdf out:    {pdf_target}")
    print(f"engine:     {engine_used}")
    print(f"status:     {'dry-run' if args.dry_run else 'success'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render and compile minutes LaTeX template for a cycle.")
    parser.add_argument("--cycle", required=True, help="Cycle identifier YYYY-MM (e.g., 2026-02).")
    parser.add_argument("--type", required=True, choices=list(TEMPLATE_MAP.keys()),
                        help="Minutes type to render (regular|open|association).")
    parser.add_argument("--out", dest="out", default=None,
                        help="Optional output PDF path (defaults to cycle_root/minutes_<type>_<cycle>.pdf).")
    parser.add_argument("--dry-run", action="store_true", help="Render .tex only; skip LaTeX compilation.")
    parser.add_argument("--engine", choices=ENGINE_CHOICES, help="LaTeX engine to use (default: auto).")
    parser.add_argument("--runs", type=int, default=2, help="Number of times to run the engine (default: 2).")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return build_minutes(args)
    except Exception as exc:  # noqa: BLE001
        print(f"Unexpected failure: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
