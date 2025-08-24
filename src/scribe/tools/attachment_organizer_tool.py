"""
AttachmentOrganizerTool: Save classified email report artifacts to disk.

This tool accepts a batch of classified reports (from EmailClassifierTool),
creates a structured directory Reports/YYYY-MM under src/scribe/output/reports,
saves placeholder files for any attachments or body excerpts, and builds a ZIP
archive of the raw sources.

It is robust to mocked inputs; it does not download real attachments, but instead
creates placeholder files named after the provided attachment_filenames.

It also includes a compatibility path for legacy calls that pass a single
`message` dict instead of a list under `classified_reports`.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging
import re
import zipfile

from crewai.tools import BaseTool

logger = logging.getLogger(__name__)


@dataclass
class _ReportItem:
    message_id: str
    sender: str
    subject: str
    classification: str
    has_attachments: bool
    attachment_filenames: List[str]
    body_excerpt: str


class AttachmentOrganizerTool(BaseTool):
    """
    Process classified email reports and organize artifacts on disk.

    - Extends: BaseTool
    - Tool name: "attachment_organizer"
    - Input:
      {
        "classified_reports": [ { message_id, from, subject, classification,
                                   has_attachments, attachment_filenames, body_excerpt }, ... ],
        "month": "YYYY-MM"
      }
    - Output:
      {
        "status": "organized",
        "report_directory": "src/scribe/output/reports/YYYY-MM/",
        "archive_file": "src/scribe/output/reports/YYYY-MM/YYYY-MM_raw_sources.zip"
      }
    """

    name: str = "attachment_organizer"
    description: str = (
        "Save report attachments or body excerpts to src/scribe/output/reports/YYYY-MM/ "
        "and create a YYYY-MM_raw_sources.zip archive."
    )

    # Accept flexible kwargs; no args_schema
    def _run(
        self,
        classified_reports: Optional[List[Dict[str, Any]]] = None,
        month: Optional[str] = None,
        base_dir: Optional[str] = None,
        # Legacy compatibility: a single message dict may be passed as `message`
        message: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        try:
            # Normalize inputs
            items: List[Dict[str, Any]] = []
            if classified_reports:
                items = classified_reports
            elif message:
                # Legacy single-message pathway; treat as one report, classification optional
                items = [message]
                if month is None:
                    # Try to infer month from message or default to current YYYY-MM
                    from datetime import datetime
                    month = datetime.now().strftime("%Y-%m")
            else:
                logger.warning("AttachmentOrganizerTool: No input reports provided; nothing to do")
                return {
                    "status": "organized",
                    "report_directory": "",
                    "archive_file": "",
                    "saved_files": [],
                    "message": "No reports to organize",
                }

            # Validate month
            if not month or not re.match(r"^\d{4}-\d{2}$", month):
                logger.warning("AttachmentOrganizerTool: Invalid or missing 'month'; defaulting to current month")
                from datetime import datetime
                month = datetime.now().strftime("%Y-%m")

            # Determine root output directory
            # Spec default: src/scribe/output/reports/YYYY-MM/
            root = Path(__file__).resolve().parent.parent  # .../src/scribe
            default_base = root / "output" / "reports"

            # Allow override via base_dir (mainly for legacy path "Reports") but keep under output/reports
            # If base_dir is an absolute path, respect it; if relative, place under output/reports
            out_base = default_base
            if base_dir:
                bd = Path(base_dir)
                if bd.is_absolute():
                    out_base = bd
                else:
                    out_base = default_base  # keep fixed base per spec

            report_dir = out_base / month
            report_dir.mkdir(parents=True, exist_ok=True)

            saved_files: List[Path] = []

            # Process each report
            for idx, item in enumerate(items, start=1):
                rep = self._normalize_item(item)
                if not rep:
                    logger.warning("AttachmentOrganizerTool: Skipped malformed item at index %d", idx)
                    continue

                if rep.has_attachments and rep.attachment_filenames:
                    # Create placeholder files for each attachment
                    for af_idx, filename in enumerate(rep.attachment_filenames, start=1):
                        safe_name = self._make_safe_name(filename) or f"attachment_{af_idx}.bin"
                        new_name = self._rename_by_classification(safe_name, rep.classification)

                        target_path = report_dir / new_name
                        target_path = self._ensure_unique(target_path)
                        try:
                            content = (
                                f"Placeholder for attachment\n"
                                f"Original filename: {filename}\n"
                                f"Message ID: {rep.message_id}\n"
                                f"Classification: {rep.classification}\n"
                            )
                            # Write binary-safe placeholder for non-txt extensions
                            if target_path.suffix.lower() in {".txt", ""}:
                                target_path.write_text(content, encoding="utf-8")
                            else:
                                target_path.write_bytes(content.encode("utf-8"))
                            saved_files.append(target_path)
                            logger.info("AttachmentOrganizerTool: Saved attachment placeholder for %s -> %s", rep.message_id, target_path)
                        except Exception as e:
                            logger.error("AttachmentOrganizerTool: Failed saving attachment placeholder %s: %s", new_name, e)
                else:
                    # No attachments: save body excerpt to a .txt file
                    base = self._derive_title(rep) or rep.classification or "body"
                    safe_title = self._make_safe_name(base)
                    if not safe_title:
                        safe_title = "body"
                    target_path = report_dir / f"{safe_title}.txt"
                    target_path = self._ensure_unique(target_path)
                    try:
                        content = (
                            f"Body excerpt saved from message {rep.message_id}\n"
                            f"Sender: {rep.sender}\n"
                            f"Subject: {rep.subject}\n"
                            f"Classification: {rep.classification}\n\n"
                            f"{rep.body_excerpt or ''}"
                        )
                        target_path.write_text(content, encoding="utf-8")
                        saved_files.append(target_path)
                        logger.info("AttachmentOrganizerTool: Saved body text for %s -> %s", rep.message_id, target_path)
                    except Exception as e:
                        logger.error("AttachmentOrganizerTool: Failed saving body text for %s: %s", rep.message_id, e)

            # Create ZIP archive of all saved files
            archive_path = report_dir / f"{month}_raw_sources.zip"
            try:
                with zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for p in saved_files:
                        # Store with only filename in archive (avoid full path)
                        zf.write(p, arcname=p.name)
                logger.info("AttachmentOrganizerTool: Created archive %s with %d file(s)", archive_path, len(saved_files))
            except Exception as e:
                logger.error("AttachmentOrganizerTool: Failed to create archive %s: %s", archive_path, e)

            return {
                "status": "organized",
                "report_directory": str(report_dir),
                "archive_file": str(archive_path),
                "saved_files": [str(p) for p in saved_files],
            }

        except Exception as e:
            logger.exception("AttachmentOrganizerTool: unexpected error")
            return {
                "status": "error",
                "error": str(e),
            }

    # Helpers
    def _normalize_item(self, item: Dict[str, Any]) -> Optional[_ReportItem]:
        try:
            return _ReportItem(
                message_id=str(item.get("message_id") or item.get("id") or "unknown"),
                sender=str(item.get("from") or ""),
                subject=str(item.get("subject") or ""),
                classification=str(item.get("classification") or item.get("category") or "general_correspondence"),
                has_attachments=bool(item.get("has_attachments", False)),
                attachment_filenames=list(item.get("attachment_filenames") or []),
                body_excerpt=str(item.get("body_excerpt") or ""),
            )
        except Exception:
            return None

    def _make_safe_name(self, name: str) -> str:
        # Remove illegal filename characters and trim
        base = re.sub(r"[\\/:*?\"<>|]", "_", name or "").strip()
        # prevent empty or dot-only names
        if not base or base in {".", ".."}:
            return ""
        return base

    def _rename_by_classification(self, filename: str, classification: str) -> str:
        if not filename:
            return filename
        # Replace base name with classification if reasonable
        p = Path(filename)
        ext = p.suffix or ""
        title = classification.strip().replace(" ", "_") if classification else p.stem
        # Capitalize some common classes for readability
        title_map = {
            "officer_report": "Officer",
            "committee_report": "Committee",
            "general_correspondence": "General",
            "non_report": "Other",
        }
        mapped = title_map.get(title.lower(), title)
        return f"{mapped}{ext}"

    def _ensure_unique(self, path: Path) -> Path:
        if not path.exists():
            return path
        stem = path.stem
        ext = path.suffix
        parent = path.parent
        i = 2
        while True:
            candidate = parent / f"{stem} ({i}){ext}"
            if not candidate.exists():
                return candidate
            i += 1

    def _derive_title(self, rep: _ReportItem) -> str:
        # Try to derive a better title from subject (e.g., Treasurer, Vice President)
        subj = rep.subject.lower()
        role_keywords = [
            ("president", "President"),
            ("vice", "VicePresident"),
            ("treasurer", "Treasurer"),
            ("secretary", "Secretary"),
            ("minutes", "Minutes"),
            ("agenda", "Agenda"),
            ("report", "Report"),
        ]
        for kw, title in role_keywords:
            if kw in subj:
                return title
        # Fallback to classification
        return {
            "officer_report": "Officer",
            "committee_report": "Committee",
            "general_correspondence": "General",
            "non_report": "Other",
        }.get(rep.classification.lower(), rep.classification or "")
