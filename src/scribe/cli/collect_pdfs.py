"""
Collect staged PDFs into the deterministic cycle pdf/ directory.

Purpose:
- stage_attachments_v2 saves attachments under:
    src/scribe/output/cycles/<cycle>/originals/<office>/
  with normalized but not necessarily canonical names.

- format_all expects a deterministic input-dir containing the canonical pdf filenames
  referenced by the report_map JSON:
    {"dining": "dining.pdf", "director": "director.pdf", ...}

This CLI bridges the two:
- For each office in the map, choose a "best" PDF candidate from originals/<office>/
- Copy it to pdf/<mapped_filename>
- Do not overwrite by default.

Usage:
  python -m src.scribe.cli.collect_pdfs --cycle 2026-02 --map src/scribe/assets/reports/report_map.json
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from src.scribe.report_inventory import reports_for_cycle
from src.scribe.report_state import load_omitted_offices

BASE_SRC = Path(__file__).resolve().parents[2]  # .../src
DEFAULT_OUTPUT_ROOT = BASE_SRC / "scribe" / "output" / "cycles"
DEFAULT_MAP_PATH = BASE_SRC / "scribe" / "assets" / "reports" / "report_map.example.json"
LAST_RESULT: Optional[dict] = None
_OVERWRITE_FOR_CONVERSION = False


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
    Convert a committee body name into the lowerCamel stem style used for
    report filenames (for example, "Building Maintenance Committee" -> "buildingMaintenance").
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
        # Keep collect convention: <office>.pdf destination under cycle/pdf.
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


@dataclass(frozen=True)
class Pick:
    path: Path
    score: Tuple[int, int, int]  # (preferred_name, newer_mtime, larger_size)


def pick_best_pdf(originals_office_dir: Path, preferred_name: str) -> Optional[Path]:
    """
    Choose the best PDF candidate from originals/<office>/.

    Heuristics (simple + deterministic enough):
    - Prefer a file whose name matches preferred_name (case-insensitive).
    - Then prefer newest modified time.
    - Then prefer largest file size.
    """
    if not originals_office_dir.is_dir():
        return None

    pdfs = [p for p in originals_office_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
    if not pdfs:
        return None

    preferred_lower = preferred_name.lower()

    picks: list[Pick] = []
    for p in pdfs:
        try:
            stat = p.stat()
            preferred = 1 if p.name.lower() == preferred_lower else 0
            newer = int(stat.st_mtime)
            size = int(stat.st_size)
            picks.append(Pick(path=p, score=(preferred, newer, size)))
        except OSError:
            # ignore unreadable files
            continue

    if not picks:
        return None

    # max by score tuple
    best = max(picks, key=lambda x: x.score)
    return best.path


def pick_best_docx(originals_office_dir: Path, office: str) -> Optional[Path]:
    """
    Choose the best DOCX candidate from originals/<office>/.

    Heuristics:
    - Prefer file named <office>.docx (case-insensitive)
    - Then newest modified time
    - Then largest size
    """
    if not originals_office_dir.is_dir():
        return None

    docx_files = [p for p in originals_office_dir.iterdir() if p.is_file() and p.suffix.lower() == ".docx"]
    if not docx_files:
        return None

    preferred_lower = f"{office}.docx".lower()

    picks: list[Pick] = []
    for p in docx_files:
        try:
            stat = p.stat()
            preferred = 1 if p.name.lower() == preferred_lower else 0
            newer = int(stat.st_mtime)
            size = int(stat.st_size)
            picks.append(Pick(path=p, score=(preferred, newer, size)))
        except OSError:
            continue

    if not picks:
        return None

    best = max(picks, key=lambda x: x.score)
    return best.path


def convert_docx_to_pdf(docx_path: Path, out_dir: Path, output_pdf_name: str) -> Path:
    """Convert a DOCX to PDF using LibreOffice headless and return the final PDF path."""
    dest = out_dir / output_pdf_name
    if dest.exists() and not _OVERWRITE_FOR_CONVERSION:
        return dest

    out_dir.mkdir(parents=True, exist_ok=True)

    # Use an isolated LibreOffice profile to avoid host-profile lock/corruption issues.
    with tempfile.TemporaryDirectory(prefix="scribe-lo-profile-") as lo_profile_dir:
        profile_uri = Path(lo_profile_dir).resolve().as_uri()
        cmd = [
            "soffice",
            "--headless",
            f"-env:UserInstallation={profile_uri}",
            "--nologo",
            "--nolockcheck",
            "--nodefault",
            "--norestore",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(docx_path),
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        stdout = result.stdout.decode("utf-8", errors="ignore").strip()
        stderr = result.stderr.decode("utf-8", errors="ignore").strip()
        raise RuntimeError(
            f"LibreOffice conversion failed (exit {result.returncode}); "
            f"stdout={stdout or '<empty>'}; stderr={stderr or '<empty>'}"
        )

    generated_pdf = out_dir / f"{docx_path.stem}.pdf"
    if not generated_pdf.exists():
        raise RuntimeError("LibreOffice did not produce the expected PDF output")

    # If LibreOffice already produced the canonical name, we're done.
    if generated_pdf.resolve() == dest.resolve():
        return dest

    # Otherwise rename/move to canonical name
    if dest.exists():
        dest.unlink()
    generated_pdf.replace(dest)
    return dest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect staged PDFs into cycle pdf/ for format_all.")
    parser.add_argument("--cycle", required=True, help="Cycle identifier YYYY-MM (e.g., 2026-02).")
    parser.add_argument(
        "--map",
        dest="map_path",
        default=str(DEFAULT_MAP_PATH),
        help="Path to mapping JSON (office -> canonical pdf filename).",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Root cycles directory (default: src/scribe/output/cycles).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing pdf/<mapped_filename> if present.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Do not return error exit code if an office has no staged PDF.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be copied, but do not write.",
    )
    parser.add_argument(
        "--fill-missing-with-placeholder",
        action="store_true",
        help="If a mapped office PDF is missing in originals/, copy cycle placeholder.pdf into pdf/<canonical>.pdf",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    global LAST_RESULT
    global _OVERWRITE_FOR_CONVERSION
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1

    try:
        cycle = validate_cycle(args.cycle)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    map_path = Path(args.map_path).expanduser().resolve()
    try:
        mapping = resolve_mapping(map_path, cycle)
        omitted_offices = load_omitted_offices(cycle, mapping)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    output_root = Path(args.output_root).expanduser().resolve()
    cycle_root = (output_root / cycle).resolve()
    originals_root = cycle_root / "originals"
    pdf_root = cycle_root / "pdf"
    placeholder_path = cycle_root / "placeholder.pdf"

    pdf_root.mkdir(parents=True, exist_ok=True)

    _OVERWRITE_FOR_CONVERSION = bool(args.overwrite)

    ok = 0
    skipped_existing = 0
    missing = 0
    converted_docx = 0
    copied: list[str] = []
    missing_offices: list[str] = []
    converted_offices: list[str] = []
    placeholder_filled = 0
    placeholder_filled_offices: list[str] = []
    placeholder_available = placeholder_path.exists()

    for office, canonical_pdf in sorted(mapping.items()):
        if office in omitted_offices:
            continue
        office_dir = originals_root / office
        dest = pdf_root / canonical_pdf

        if dest.exists() and not args.overwrite:
            skipped_existing += 1
            continue

        src = pick_best_pdf(office_dir, preferred_name=canonical_pdf)
        if not src:
            docx_src = pick_best_docx(office_dir, office)
            if docx_src:
                if args.dry_run:
                    copied.append(f"DRY CONVERT {docx_src} -> {dest}")
                    ok += 1
                    converted_docx += 1
                    converted_offices.append(f"{office}:{docx_src.name}->{canonical_pdf}")
                    continue
                try:
                    converted_path = convert_docx_to_pdf(docx_src, pdf_root, canonical_pdf)
                except Exception as exc:
                    missing += 1
                    missing_offices.append(f"{office}:{canonical_pdf} (conversion failed: {exc})")
                    continue
                copied.append(f"{docx_src} -> {converted_path} (converted)")
                ok += 1
                converted_docx += 1
                converted_offices.append(f"{office}:{docx_src.name}->{canonical_pdf}")
                continue

            if args.fill_missing_with_placeholder:
                if placeholder_available:
                    src = placeholder_path
                    placeholder_filled += 1
                    placeholder_filled_offices.append(f"{office}:{canonical_pdf}")
                else:
                    missing += 1
                    missing_offices.append(f"{office}:{canonical_pdf} (placeholder missing)")
                    continue
            else:
                missing += 1
                missing_offices.append(f"{office}:{canonical_pdf}")
                continue

        if args.dry_run:
            copied.append(f"DRY {src} -> {dest}")
            ok += 1
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(f"{src} -> {dest}")
        ok += 1

    print("\n=== Collect PDFs Summary ===")
    print(f"Cycle: {cycle}")
    print(f"Map: {map_path}")
    print(f"Cycle root: {cycle_root}")
    print(f"Originals: {originals_root}")
    print(f"PDF dir: {pdf_root}")
    if omitted_offices:
        print(f"Intentionally omitted (no written appendix): {', '.join(sorted(omitted_offices))}")
    print(
        f"Counts -> copied/ok: {ok}, skipped-existing: {skipped_existing}, "
        f"missing: {missing}, placeholder-filled: {placeholder_filled}, converted_docx: {converted_docx}"
    )
    if copied:
        print("\nCopies:")
        for line in copied:
            print(f"  - {line}")
    if converted_offices:
        print("\nConverted DOCX:")
        for item in converted_offices:
            print(f"  - {item}")
    if placeholder_filled_offices:
        print("\nPlaceholder filled for:")
        for item in placeholder_filled_offices:
            print(f"  - {item}")
    if missing_offices:
        print("\nMissing staged PDFs for:")
        for item in missing_offices:
            print(f"  - {item}")

    if missing_offices and not args.allow_missing:
        exit_code = 1
    else:
        exit_code = 0

    LAST_RESULT = {
        "cycle": cycle,
        "map_path": str(map_path),
        "cycle_root": str(cycle_root),
        "originals_root": str(originals_root),
        "pdf_root": str(pdf_root),
        "copied": copied,
        "missing_offices": missing_offices,
        "omitted_offices": sorted(omitted_offices),
        "placeholder_filled_offices": placeholder_filled_offices,
        "converted_offices": converted_offices,
        "counts": {
            "copied": ok,
            "skipped_existing": skipped_existing,
            "missing": missing,
            "placeholder_filled": placeholder_filled,
            "converted_docx": converted_docx,
        },
        "exit_code": exit_code,
        "allow_missing": args.allow_missing,
        "dry_run": args.dry_run,
        "overwrite": args.overwrite,
        "fill_missing_with_placeholder": args.fill_missing_with_placeholder,
        "placeholder_available": placeholder_available,
        "placeholder_path": str(placeholder_path),
    }

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
