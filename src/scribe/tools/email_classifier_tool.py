"""
EmailClassifierTool: Classify email report candidates into categories.

This tool consumes dictionaries produced by EmailInboxMonitorTool (or similar
structure) and classifies each message using sender lists and subject heuristics.

- Extends: BaseTool
- Tool name: "email_classifier"
- Class name: EmailClassifierTool

Inputs to _run:
- Either a single message via `message=<dict>`
- Or a list of messages via `reports=<list[dict]>`
- Optional `recipients_dir` path pointing to assets/recipients

Outputs:
- If given `reports` (list):
  {
    "status": "classified",
    "classified_reports": [ { original fields..., classification: <str> }, ... ]
  }
- If given `message` (single):
  {
    "status": "classified",
    "classification": <str>,
    "relevant": <bool>,
    "reason": <str>,
    "item": { original fields..., classification: <str> }
  }
This dual shape keeps backward compatibility with monitor_and_ingest_email_reports,
which expects `relevant` and `reason` for per-message calls.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import json
import logging
import os
import re
from pathlib import Path

from crewai.tools import BaseTool

logger = logging.getLogger(__name__)


KEYWORDS = ["report", "agenda", "minutes", "attachment"]


class EmailClassifierTool(BaseTool):
    name: str = "email_classifier"
    description: str = (
        "Classify Gmail report candidates into officer_report, committee_report, "
        "general_correspondence, or non_report using sender lists and subject heuristics."
    )

    # No args_schema; accept flexible kwargs

    def _run(
        self,
        reports: Optional[List[Dict[str, Any]]] = None,
        message: Optional[Dict[str, Any]] = None,
        recipients_dir: Optional[str] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        # Load known sender lists
        council_members, committee_chairs = self._load_recipients(recipients_dir)

        # Normalize inputs to a list of items to classify
        items: List[Dict[str, Any]]
        single_mode = False
        if message is not None and reports is None:
            items = [message]
            single_mode = True
        else:
            items = reports or []

        logger.info(f"EmailClassifierTool: processing {len(items)} item(s)")

        classified: List[Dict[str, Any]] = []
        for idx, item in enumerate(items, start=1):
            try:
                classification, reason = self._classify_one(
                    item,
                    council_members,
                    committee_chairs,
                )
                enriched = dict(item)
                enriched["classification"] = classification
                classified.append(enriched)
                logger.info(
                    "EmailClassifierTool: item %s classified as '%s' (%s)",
                    idx,
                    classification,
                    reason,
                )
            except Exception as e:
                logger.exception("EmailClassifierTool: failed to classify item %s", idx)
                enriched = dict(item)
                enriched["classification"] = "non_report"
                classified.append(enriched)

        # Single-item backward-compatible response
        if single_mode:
            item0 = classified[0] if classified else {}
            classification = item0.get("classification", "non_report")
            relevant = classification in ("officer_report", "committee_report")
            # reason recompute to include keywords/sender basis for clarity
            sender = (message or {}).get("from", "") or ""
            subject = (message or {}).get("subject", "") or ""
            reason = self._explain(sender, subject, council_members, committee_chairs)
            return {
                "status": "classified",
                "classification": classification,
                "relevant": bool(relevant),
                "reason": reason,
                "item": item0,
            }

        # Batch response per spec
        return {
            "status": "classified",
            "classified_reports": classified,
        }

    def _load_recipients(self, recipients_dir: Optional[str]) -> Tuple[set, set]:
        try:
            if recipients_dir:
                base = Path(recipients_dir)
            else:
                # Default to project assets path relative to this file
                base = Path(__file__).resolve().parent.parent / "assets" / "recipients"
            council_path = base / "council_members.json"
            chairs_path = base / "committee_chairs.json"
            council_members = _load_email_set(council_path)
            committee_chairs = _load_email_set(chairs_path)
            logger.info(
                "EmailClassifierTool: loaded recipients (council_members=%d, committee_chairs=%d)",
                len(council_members), len(committee_chairs)
            )
            return council_members, committee_chairs
        except Exception as e:
            logger.warning(f"EmailClassifierTool: failed to load recipients: {e}")
            return set(), set()

    def _classify_one(
        self,
        item: Dict[str, Any],
        council_members: set,
        committee_chairs: set,
    ) -> Tuple[str, str]:
        sender = (item.get("from") or "").lower()
        subject = (item.get("subject") or "").lower()
        has_attachments = bool(item.get("has_attachments", False))
        body_excerpt = (item.get("body_excerpt") or "")

        # Sender matching
        sender_in_council = _email_in_set(sender, council_members)
        sender_in_chairs = _email_in_set(sender, committee_chairs)

        # Subject heuristics
        subject_hits = [kw for kw in KEYWORDS if kw in subject]
        subject_has_keywords = len(subject_hits) > 0

        # Decide classification
        if sender_in_council and not sender_in_chairs:
            return "officer_report", "Sender matched council_members.json"
        if sender_in_chairs and not sender_in_council:
            return "committee_report", "Sender matched committee_chairs.json"
        if sender_in_council and sender_in_chairs:
            # Ambiguous; use subject hint
            if subject_has_keywords:
                # Prefer committee if subject references committee context, else officer
                if _looks_committee(subject):
                    return "committee_report", "Sender matched both; subject suggests committee"
                return "officer_report", "Sender matched both; subject suggests report"
            # Default to officer when ambiguous
            return "officer_report", "Sender matched both lists; default officer_report"

        # No sender match: use subject heuristics
        if subject_has_keywords:
            if _looks_committee(subject):
                return "committee_report", f"Subject contained keywords ({', '.join(subject_hits)})"
            return "officer_report", f"Subject contained keywords ({', '.join(subject_hits)})"

        # Fallbacks
        substantive_body = len(re.sub(r"\s+", "", body_excerpt)) >= 200
        if has_attachments or substantive_body:
            return "general_correspondence", "No sender/subject match; substantive content"

        return "non_report", "No indicators of report relevance"

    def _explain(self, sender: str, subject: str, cm: set, cc: set) -> str:
        s = sender.lower()
        subj = subject.lower()
        parts = []
        if _email_in_set(s, cm):
            parts.append("Sender matched council_member.json")
        if _email_in_set(s, cc):
            parts.append("Sender matched committee_chairs.json")
        for kw in KEYWORDS:
            if kw in subj:
                parts.append(f"Subject contained '{kw}'")
        return ", ".join(parts) if parts else "Heuristic default applied"


def _load_email_set(path: Path) -> set:
    try:
        if not path.exists():
            return set()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        emails = set()
        if isinstance(data, list):
            for v in data:
                if isinstance(v, str):
                    emails.add(v.strip().lower())
        elif isinstance(data, dict):
            # In case a dict structure is used in future
            for v in data.values():
                if isinstance(v, list):
                    for e in v:
                        if isinstance(e, str):
                            emails.add(e.strip().lower())
        return emails
    except Exception:
        return set()


def _email_in_set(sender_header: str, email_set: set) -> bool:
    # Extract email from formats like 'Name <email@domain>'
    m = re.search(r"<([^>]+@[^>]+)>", sender_header)
    email = m.group(1).lower() if m else sender_header.strip().lower()
    return email in email_set


def _looks_committee(subject_lower: str) -> bool:
    # Simple hint words to tilt toward committee_report
    return any(w in subject_lower for w in ["committee", "chair", "subcommittee"])