"""
Batch formatter CLI for preparing a monthly cycle's appendix assets.

- Deterministic: driven by a mapping JSON of office stem -> source PDF filename.
- Output scaffold under src/scribe/output/cycles/<cycle>/ with png/, pdf/, originals/ and manifest.json.
- Falls back to a placeholder PDF when a source is missing (if available).
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import shutil

from src.scribe.tools.formatter_service import FormatterService
from src.scribe.report_inventory import reports_for_cycle
from src.scribe.report_state import load_omitted_offices


BASE_SRC = Path(__file__).resolve().parents[2]  # .../src
DEFAULT_MAP_PATH = BASE_SRC / "scribe" / "assets" / "reports" / "report_map.example.json"
PLACEHOLDER_TEMPLATE_PATH = BASE_SRC / "scribe" / "assets" / "templates" / "placeholder.pdf"
OUTPUT_ROOT = BASE_SRC / "scribe" / "output" / "cycles"
LAST_RESULT: Optional[dict] = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch formatter for monthly appendix assets.")
    parser.add_argument("--cycle", required=True, help="Cycle identifier YYYY-MM (e.g., 2025-11).")
    parser.add_argument("--input-dir", required=True, help="Directory containing source PDFs.")
    parser.add_argument("--map", dest="map_path", default=str(DEFAULT_MAP_PATH),
                        help="Path to mapping JSON (office -> source PDF filename).")
    parser.add_argument("--dpi", type=int, default=FormatterService.DEFAULT_DPI, help="Render DPI (default 300).")
    parser.add_argument("--no-trim", action="store_true", help="Disable whitespace trimming.")
    parser.add_argument("--json", action="store_true", help="Print full result JSON.")
    return parser


def validate_cycle(cycle: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}", cycle or ""):
        raise ValueError("--cycle must be in YYYY-MM format")
    return cycle


def load_mapping(map_path: Path) -> Dict[str, str]:
    if not map_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {map_path}")
    data = json.loads(map_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("Mapping JSON must be a non-empty object of office->pdf filename")
    clean: Dict[str, str] = {}
    for office, pdf_name in data.items():
        if not office or not isinstance(office, str):
            raise ValueError("Invalid office key in mapping")
        if not pdf_name or not isinstance(pdf_name, str):
            raise ValueError(f"Invalid pdf filename for office '{office}'")
        clean[office.strip()] = pdf_name.strip()
    return clean


def _to_office_stem(body_name: str) -> str:
    """
    Convert a committee body name into the existing lowerCamel stem style
    used for report filenames (for example, "Building Maintenance Committee"
    -> "buildingMaintenance").
    """
    text = (body_name or "").strip()
    text = re.sub(r"(?i)\bcommittee\b", "", text)
    text = text.replace("&", " and ").replace("/", " ")
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    parts = [p for p in text.strip().split() if p]
    if not parts:
        return ""
    head = parts[0].lower()
    tail = "".join(p[:1].upper() + p[1:] for p in parts[1:])
    return f"{head}{tail}"


def load_committee_chair_mapping() -> Dict[str, str]:
    """
    Build office->pdf mapping entries for committees with an active Chair term.
    """
    from src.scribe.clerk_models import Body, Office, Term
    from src.scribe.database import get_db_session

    db = get_db_session()
    try:
        today = date.today()
        rows = (
            db.query(Body.name)
            .join(Office, Office.office_body_id == Body.body_id)
            .join(Term, Term.term_office_id == Office.office_id)
            .filter(Office.title == "Chair")
            .filter((Term.end.is_(None)) | (Term.end >= today))
            .distinct()
            .all()
        )
    finally:
        db.close()

    mapping: Dict[str, str] = {}
    for (body_name,) in rows:
        stem = _to_office_stem(body_name or "")
        if not stem:
            continue
        # Keep existing convention: <office>.pdf -> <office>.png
        mapping[stem] = f"{stem}.pdf"
    return mapping


def resolve_mapping(map_path: Path, cycle: str) -> Dict[str, str]:
    """
    Load static mapping and add committee chair slots from the database.
    Static entries win if a key exists in both sources.
    """
    mapping = load_mapping(map_path)
    dynamic = load_committee_chair_mapping()
    for office, pdf_name in dynamic.items():
        mapping.setdefault(office, pdf_name)
    return reports_for_cycle(mapping, cycle)


def ensure_cycle_scaffold(cycle_root: Path) -> None:
    (cycle_root / "png").mkdir(parents=True, exist_ok=True)
    (cycle_root / "pdf").mkdir(parents=True, exist_ok=True)
    (cycle_root / "originals").mkdir(parents=True, exist_ok=True)


def copy_placeholder_if_available(cycle_root: Path, placeholder_exists: bool) -> Path:
    dst = cycle_root / "placeholder.pdf"
    if placeholder_exists and not dst.exists():
        shutil.copyfile(PLACEHOLDER_TEMPLATE_PATH, dst)
    return dst


def process_office(
    office: str,
    source_pdf_name: str,
    input_dir: Path,
    png_dir: Path,
    placeholder_available: bool,
    cycle_placeholder: Path,
    dpi: int,
    trim_whitespace: bool,
    svc: FormatterService,
) -> Tuple[Dict[str, Any], bool, bool, bool]:
    source_path = (input_dir / source_pdf_name).expanduser().resolve()
    placeholder_used = False
    source_missing = not source_path.exists()

    if source_missing:
        if placeholder_available and cycle_placeholder.exists():
            pdf_to_use = cycle_placeholder
            placeholder_used = True
        else:
            entry = {
                "source_pdf": str(source_path),
                "placeholder_used": False,
                "pages": 0,
                "png_files": [],
                "status": "missing_placeholder",
                "error": f"Source missing and placeholder unavailable: {source_path}",
            }
            return entry, False, True, True  # success flag False, missing_placeholder True, source missing True
    else:
        pdf_to_use = source_path

    result = svc.pdf_to_pngs_v1(
        pdf_path=str(pdf_to_use),
        office=office,
        output_dir=str(png_dir),
        dpi=dpi,
        trim_whitespace=trim_whitespace,
    )

    success = bool(result.get("success"))
    pages = int(result.get("pages") or 0)
    images = result.get("images") or []
    png_files = []
    for img in images:
        try:
            image_path = Path(img).resolve()
            if not image_path.is_file():
                entry = {
                    "source_pdf": str(pdf_to_use),
                    "placeholder_used": bool(placeholder_used),
                    "pages": pages,
                    "png_files": [],
                    "status": "failed",
                    "error": f"Formatter reported missing PNG output: {image_path}",
                }
                return entry, False, False, source_missing
            rel = image_path.relative_to(png_dir.resolve())
            png_files.append(rel.as_posix())
        except ValueError:
            entry = {
                "source_pdf": str(pdf_to_use),
                "placeholder_used": bool(placeholder_used),
                "pages": pages,
                "png_files": [],
                "status": "failed",
                "error": f"Formatter output is outside png directory: {img}",
            }
            return entry, False, False, source_missing

    status = "ok" if success else "failed"
    entry = {
        "source_pdf": str(pdf_to_use),
        "placeholder_used": bool(placeholder_used),
        "pages": pages,
        "png_files": png_files,
        "status": status,
    }
    if not success:
        entry["error"] = result.get("message") or result.get("status") or "unknown error"
    elif placeholder_used and not source_path.exists():
        entry["error"] = f"Original source missing; used placeholder for {source_pdf_name}"

    return entry, success, False, source_missing


def main(argv: Optional[List[str]] = None) -> int:
    global LAST_RESULT
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1

    try:
        cycle = validate_cycle(args.cycle)
    except ValueError as exc:
        parser.error(str(exc))

    input_dir = Path(args.input_dir).expanduser().resolve()
    if not input_dir.is_dir():
        parser.error(f"--input-dir not found or not a directory: {input_dir}")

    map_path = Path(args.map_path).expanduser().resolve()

    try:
        mapping = resolve_mapping(map_path, cycle)
        omitted_offices = load_omitted_offices(cycle, mapping)
    except Exception as exc:
        parser.error(str(exc))

    cycle_root = (OUTPUT_ROOT / cycle).resolve()
    ensure_cycle_scaffold(cycle_root)
    png_dir = cycle_root / "png"

    placeholder_available = PLACEHOLDER_TEMPLATE_PATH.exists()
    if placeholder_available:
        copy_placeholder_if_available(cycle_root, placeholder_exists=True)
    cycle_placeholder = cycle_root / "placeholder.pdf"

    svc = FormatterService()

    offices: Dict[str, Dict[str, Any]] = {}
    ok_count = 0
    fail_count = 0
    placeholder_count = 0
    missing_sources = []
    missing_placeholder_flag = not placeholder_available

    for office, pdf_name in sorted(mapping.items()):
        if office in omitted_offices:
            offices[office] = {
                "source_pdf": None,
                "placeholder_used": False,
                "pages": 0,
                "png_files": [],
                "status": "omitted",
            }
            continue
        entry, success, missing_placeholder, source_missing = process_office(
            office=office,
            source_pdf_name=pdf_name,
            input_dir=input_dir,
            png_dir=png_dir,
            placeholder_available=placeholder_available,
            cycle_placeholder=cycle_placeholder,
            dpi=args.dpi,
            trim_whitespace=not args.no_trim,
            svc=svc,
        )

        offices[office] = entry

        if entry.get("placeholder_used"):
            placeholder_count += 1
            if source_missing:
                missing_sources.append(f"{office}:{pdf_name}")
        if entry.get("status") == "missing_placeholder":
            missing_sources.append(f"{office}:{pdf_name}")
            fail_count += 1
        elif not success:
            fail_count += 1
        else:
            ok_count += 1

        missing_placeholder_flag = missing_placeholder_flag or missing_placeholder

    manifest = {
        "cycle": cycle,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(input_dir),
        "output_dir": str(cycle_root),
        "dpi": args.dpi,
        "trim_whitespace": not args.no_trim,
        "map_path": str(map_path),
        "placeholder_available": placeholder_available,
        "offices": offices,
    }

    manifest_path = cycle_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        print("\n=== Batch Format Summary ===")
        print(f"Cycle: {cycle}")
        print(f"Input dir: {input_dir}")
        print(f"Output root: {cycle_root}")
        print(f"Placeholder template: {'found' if placeholder_available else 'MISSING'}")
        print(f"Counts -> ok: {ok_count}, failed: {fail_count}, placeholder-used: {placeholder_count}")
        if omitted_offices:
            print(f"Intentionally omitted (no written appendix): {', '.join(sorted(omitted_offices))}")
        if missing_sources:
            print("Missing source PDFs:")
            for item in missing_sources:
                print(f"  - {item}")
        print(f"Manifest written: {manifest_path}")

    exit_code = 0
    if fail_count > 0 or missing_placeholder_flag:
        exit_code = 1

    LAST_RESULT = {
        "cycle": cycle,
        "input_dir": str(input_dir),
        "output_root": str(cycle_root),
        "map_path": str(map_path),
        "manifest_path": str(manifest_path),
        "ok_count": ok_count,
        "fail_count": fail_count,
        "placeholder_count": placeholder_count,
        "missing_sources": missing_sources,
        "omitted_offices": sorted(omitted_offices),
        "missing_placeholder": missing_placeholder_flag,
        "exit_code": exit_code,
    }

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
