"""Build agenda template context from Clerk database-backed source data."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

OFFICER_SLOTS = [
    {"label": "President", "office_names": ["President"], "body_names": ["Residents Council"]},
    {"label": "Vice President", "office_names": ["Vice President"], "body_names": ["Residents Council"]},
    {"label": "Treasurer", "office_names": ["Treasurer"], "body_names": ["Residents Council"]},
    {"label": "Secretary", "office_names": ["Secretary"], "body_names": ["Residents Council"]},
    {
        "label": "Administrative Assistant",
        "office_names": ["Administrative Assistant"],
        "body_names": ["Residents Council"],
    },
]

REGULAR_LIAISON_SLOTS = [
    {"label": "Building Maintenance", "body_names": ["Building Maintenance Committee", "Building Maintenance"]},
    {"label": "Dining", "body_names": ["Dining Committee", "Dining"]},
    {"label": "Employee Appreciation", "body_names": ["Employee Appreciation Committee", "Employee Appreciation"]},
    {"label": "Environment/Landscape", "body_names": ["Environment/Landscape Committee", "Environment/Landscape"]},
    {"label": "Finance", "body_names": ["Finance Committee", "Finance"]},
    {"label": "Library", "body_names": ["Library Committee", "Library"]},
    {"label": "Scholarship", "body_names": ["Scholarship Committee", "Scholarship"]},
    {"label": "Special Events \\& Trips", "body_names": ["Special Events and Trips Committee", "Special Events & Trips"]},
    {"label": "St.~Stephen's Green", "body_names": ["St. Stephen's Green", "St Stephens Green", "St Stephen's Green"]},
]

OPEN_REPORT_SLOTS = [
    {"label": "Building Maintenance", "body_names": ["Building Maintenance Committee", "Building Maintenance"]},
    {"label": "Dining", "body_names": ["Dining Committee", "Dining"]},
    {"label": "Employee Appreciation", "body_names": ["Employee Appreciation Committee", "Employee Appreciation"]},
    {"label": "Environment/Landscape", "body_names": ["Environment/Landscape Committee", "Environment/Landscape"]},
    {"label": "Finance", "body_names": ["Finance Committee", "Finance"]},
    {"label": "Library", "body_names": ["Library Committee", "Library"]},
    {"label": "Scholarship", "body_names": ["Scholarship Committee", "Scholarship"]},
    {"label": "Special Events \\& Trips", "body_names": ["Special Events and Trips Committee", "Special Events & Trips"]},
]


class AgendaContextBuilder:
    """Create a normalized context object used by agenda templates."""

    @staticmethod
    def _normalize_token(value: str) -> str:
        normalized = (value or "").lower()
        normalized = normalized.replace("&", "and").replace("/", " ")
        normalized = normalized.replace(".", "").replace("~", " ")
        normalized = normalized.replace("'", "").replace("’", "")
        normalized = normalized.replace("committee", "")
        normalized = " ".join(normalized.split())
        return normalized

    @classmethod
    def _load_current_incumbents_by_title(cls, office_title: str) -> List[Dict[str, str]]:
        # Agenda rosters use existence of Term link records as currency;
        # term dates are intentionally ignored.
        from scribe.database import get_db_session
        from scribe.clerk_models import Body, Office, Person, ReportRecord, Term

        db = get_db_session()
        rows: List[Dict[str, str]] = []
        try:
            try:
                records = (
                    db.query(ReportRecord)
                    .filter(ReportRecord.title == office_title)
                    .order_by(ReportRecord.body_precedence.asc(), ReportRecord.office_precedence.asc())
                    .all()
                )
                for rec in records:
                    body_name = (rec.name or "").strip()
                    if not body_name:
                        continue
                    first = (rec.first or "").strip()
                    last = (rec.last or "").strip()
                    incumbent = f"{first} {last}".strip()
                    if not incumbent:
                        continue
                    rows.append({"body": body_name, "title": office_title, "incumbent": incumbent})
            except Exception as exc:
                logger.warning(
                    "ReportRecord lookup failed for office '%s'; using direct joins fallback: %s",
                    office_title,
                    exc,
                )
                fallback_rows = (
                    db.query(Body.name, Office.title, Person.first, Person.last)
                    .select_from(Term)
                    .join(Office, Term.term_office_id == Office.office_id)
                    .join(Body, Office.office_body_id == Body.body_id)
                    .join(Person, Term.term_person_id == Person.person_id)
                    .filter(Office.title == office_title)
                    .order_by(Body.body_precedence.asc(), Office.office_precedence.asc())
                    .all()
                )
                for body_name, title, first, last in fallback_rows:
                    clean_body = (body_name or "").strip()
                    incumbent = f"{(first or '').strip()} {(last or '').strip()}".strip()
                    if not clean_body or not incumbent:
                        continue
                    rows.append({"body": clean_body, "title": (title or office_title).strip(), "incumbent": incumbent})
            return rows
        finally:
            db.close()

    @classmethod
    def _build_body_rows(cls, office_title: str, slots: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        try:
            incumbents = cls._load_current_incumbents_by_title(office_title=office_title)
            unavailable_fallback = "[vacant]"
        except Exception as exc:
            logger.warning("Could not load office '%s' incumbents from Clerk database: %s", office_title, exc)
            incumbents = []
            unavailable_fallback = "[name unavailable]"

        body_lookup: Dict[str, str] = {}
        for row in incumbents:
            normalized = cls._normalize_token(row["body"])
            body_lookup.setdefault(normalized, row["incumbent"])

        result: List[Dict[str, str]] = []
        missing_labels: List[str] = []
        for slot in slots:
            label = slot["label"]
            incumbent = None
            for body_name in slot["body_names"]:
                incumbent = body_lookup.get(cls._normalize_token(body_name))
                if incumbent:
                    break
            if not incumbent:
                incumbent = unavailable_fallback
                missing_labels.append(label)
            result.append({"label": label, "incumbent": incumbent})

        if missing_labels:
            logger.warning(
                "Missing %s incumbents for %d slot(s): %s",
                office_title,
                len(missing_labels),
                ", ".join(missing_labels),
            )
        return result

    @classmethod
    def _build_officers(cls) -> List[Dict[str, str]]:
        try:
            incumbents = cls._load_current_incumbents_by_title(office_title="President")
            incumbents += cls._load_current_incumbents_by_title(office_title="Vice President")
            incumbents += cls._load_current_incumbents_by_title(office_title="Treasurer")
            incumbents += cls._load_current_incumbents_by_title(office_title="Secretary")
            incumbents += cls._load_current_incumbents_by_title(office_title="Administrative Assistant")
            unavailable_fallback = "[vacant]"
        except Exception as exc:
            logger.warning("Could not load officers from Clerk database: %s", exc)
            incumbents = []
            unavailable_fallback = "[name unavailable]"

        office_lookup: Dict[str, str] = {}
        for row in incumbents:
            office_key = cls._normalize_token(row["title"])
            body_key = cls._normalize_token(row["body"])
            office_lookup.setdefault(f"{office_key}:{body_key}", row["incumbent"])

        result: List[Dict[str, str]] = []
        for slot in OFFICER_SLOTS:
            incumbent = None
            for office_name in slot["office_names"]:
                for body_name in slot["body_names"]:
                    office_key = cls._normalize_token(office_name)
                    body_key = cls._normalize_token(body_name)
                    incumbent = office_lookup.get(f"{office_key}:{body_key}")
                    if incumbent:
                        break
                if incumbent:
                    break
            result.append({"label": slot["label"], "incumbent": incumbent or unavailable_fallback})
        return result

    @classmethod
    def build(cls, meeting_info: Dict[str, Any]) -> Dict[str, Any]:
        """Return an enriched copy of meeting info with template-friendly role rows."""
        context = dict(meeting_info)
        context["officers"] = cls._build_officers()
        context["regular_reports"] = cls._build_body_rows("Liaison", REGULAR_LIAISON_SLOTS)
        context["open_reports"] = cls._build_body_rows("Chair", OPEN_REPORT_SLOTS)
        # Association agenda currently uses the same committee slots/titles as open.
        context["association_reports"] = context["open_reports"]
        return context
