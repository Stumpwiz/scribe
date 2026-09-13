"""Reliable committee-minutes archive and website publication workflow."""

from __future__ import annotations

import calendar
import os
import re
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from src.scribe.website.committee_modal import AnchorPatch, find_anchor_patch

COMMITTEE_MODALS = {
    "BM": "bmModal", "DI": "diModal", "EA": "eaModal", "EL": "elModal",
    "FI": "fiModal", "LI": "liModal", "SC": "scModal", "SE": "seModal",
}


class ArchiveMinutesError(ValueError):
    """An actionable validation or publication error."""


@dataclass(frozen=True)
class PublicationPlan:
    committee: str
    month: str
    source: Path
    site_root: Path
    destination: Path
    relative_href: str
    modal_id: str
    month_label: str
    index_path: Path
    html: str
    patch: AnchorPatch
    destination_exists: bool
    force: bool


def validate_committee(code: str) -> str:
    code = (code or "").upper()
    if code not in COMMITTEE_MODALS:
        valid = ", ".join(COMMITTEE_MODALS)
        raise ArchiveMinutesError(f"Unknown committee code '{code}'. Expected one of: {valid}.")
    return code


def validate_month(month: str) -> str:
    match = re.fullmatch(r"(\d{4})-(\d{2})", month or "")
    if match is None or not 1 <= int(match.group(2)) <= 12:
        raise ArchiveMinutesError(f"Invalid month '{month}'. Use exactly YYYY-MM with a month from 01 to 12.")
    return month


def destination_path(site_root: Path, committee: str, month: str) -> Path:
    return site_root / "documents" / "Archive" / committee / month[:4] / f"{month}_{committee}.pdf"


def build_plan(committee: str, month: str, source: Path, site_root: Path, *, force: bool = False) -> PublicationPlan:
    committee = validate_committee(committee)
    month = validate_month(month)
    source = Path(source).expanduser().resolve()
    site_root = Path(site_root).expanduser().resolve()
    if not source.is_file():
        raise ArchiveMinutesError(f"Source DOCX does not exist or is not a file: {source}")
    if source.suffix.lower() != ".docx":
        raise ArchiveMinutesError(f"Source must have a .docx extension: {source}")
    if not site_root.is_dir():
        raise ArchiveMinutesError(f"Website repository root does not exist or is not a directory: {site_root}")
    index_path = site_root / "index.html"
    if not index_path.is_file():
        raise ArchiveMinutesError(f"Website repository root does not contain index.html: {index_path}")
    destination = destination_path(site_root, committee, month)
    if source == destination.resolve():
        raise ArchiveMinutesError("Source and archive destination resolve to the same file.")
    exists = destination.exists()
    if exists and not force:
        raise ArchiveMinutesError(f"Destination PDF already exists: {destination}. Re-run with --force to replace it.")
    relative_href = destination.relative_to(site_root).as_posix()
    label = calendar.month_abbr[int(month[5:7])]
    # Decode bytes directly so Python does not normalize Windows CRLF newlines.
    try:
        html = index_path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ArchiveMinutesError(f"index.html is not valid UTF-8: {index_path}") from exc
    patch = find_anchor_patch(html, COMMITTEE_MODALS[committee], label, relative_href)
    return PublicationPlan(committee, month, source, site_root, destination, relative_href,
                           COMMITTEE_MODALS[committee], label, index_path, html, patch, exists, force)


def convert_docx_to_pdf(source: Path, work_dir: Path) -> Path:
    """Convert in an isolated LibreOffice profile and strictly validate its output."""
    executable = shutil.which("soffice") or shutil.which("libreoffice")
    if executable is None:
        raise ArchiveMinutesError("LibreOffice was not found. Install it and ensure soffice is on PATH.")
    with tempfile.TemporaryDirectory(prefix="scribe-lo-profile-") as profile:
        command = [executable, "--headless", f"-env:UserInstallation={Path(profile).resolve().as_uri()}",
                   "--nologo", "--nolockcheck", "--nodefault", "--norestore",
                   "--convert-to", "pdf", "--outdir", str(work_dir), str(source)]
        result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic output"
        raise ArchiveMinutesError(f"LibreOffice conversion failed (exit {result.returncode}): {detail}")
    expected = work_dir / f"{source.stem}.pdf"
    pdfs = list(work_dir.glob("*.pdf"))
    if pdfs != [expected] and set(pdfs) != {expected}:
        names = ", ".join(p.name for p in pdfs) or "none"
        raise ArchiveMinutesError(f"LibreOffice did not create exactly the expected PDF '{expected.name}' (found: {names}).")
    if not expected.is_file() or expected.stat().st_size == 0:
        raise ArchiveMinutesError(f"LibreOffice produced a missing or empty PDF: {expected}")
    return expected


def _stage_file(directory: Path, data: bytes, suffix: str, *, mode: int = 0o644) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".scribe-", suffix=suffix, dir=directory)
    path = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, mode)
        return path
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def apply_plan(plan: PublicationPlan, converted_pdf: Path) -> tuple[Path, Path]:
    """Stage both files, atomically replace each, and roll back the PDF if HTML fails."""
    try:
        current_html = plan.index_path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ArchiveMinutesError(f"index.html is no longer valid UTF-8: {plan.index_path}") from exc
    if current_html != plan.html:
        raise ArchiveMinutesError(
            f"index.html changed after validation; no files were installed. Re-run the command: {plan.index_path}"
        )
    if plan.destination.exists() and not plan.force:
        raise ArchiveMinutesError(
            f"Destination PDF appeared after validation: {plan.destination}. Re-run with --force to replace it."
        )
    new_html = plan.patch.apply(plan.html).encode("utf-8")
    pdf_mode = stat.S_IMODE(plan.destination.stat().st_mode) if plan.destination.exists() else 0o644
    html_mode = stat.S_IMODE(plan.index_path.stat().st_mode)
    staged_pdf = _stage_file(plan.destination.parent, converted_pdf.read_bytes(), ".pdf", mode=pdf_mode)
    staged_html = _stage_file(plan.index_path.parent, new_html, ".html", mode=html_mode)
    backup_pdf: Path | None = None
    installed = False
    try:
        if plan.destination.exists():
            backup_pdf = _stage_file(
                plan.destination.parent, plan.destination.read_bytes(), ".bak", mode=pdf_mode
            )
        os.replace(staged_pdf, plan.destination)
        installed = True
        os.replace(staged_html, plan.index_path)
    except BaseException:
        if installed:
            if backup_pdf is not None:
                os.replace(backup_pdf, plan.destination)
                backup_pdf = None
            else:
                plan.destination.unlink(missing_ok=True)
        raise
    finally:
        staged_pdf.unlink(missing_ok=True)
        staged_html.unlink(missing_ok=True)
        if backup_pdf is not None:
            backup_pdf.unlink(missing_ok=True)
    return plan.destination, plan.index_path


def publish(plan: PublicationPlan, *, apply: bool) -> tuple[Path, Path] | None:
    with tempfile.TemporaryDirectory(prefix="scribe-committee-minutes-") as work:
        pdf = convert_docx_to_pdf(plan.source, Path(work))
        return apply_plan(plan, pdf) if apply else None
