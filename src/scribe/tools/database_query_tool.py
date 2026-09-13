"""
database_query_tool.py - CrewAI tool for querying the shared Clerk database

This tool provides methods to query governance data from the PostgreSQL database,
replacing static JSON files with dynamic database queries.

Business Rules:
- Council officers receive emails for ALL meeting types
- Committee chairs receive emails ONLY for "open" meeting types
- Recipients are determined by active Term records
"""

import logging
import os
from typing import List, Dict, Optional, Iterable, Tuple
from datetime import datetime, date
from crewai.tools import BaseTool
from pydantic import Field

from scribe.database import get_db_session
from scribe.clerk_models import Body, Person, Office, Term

logger = logging.getLogger(__name__)

DEFAULT_COMMITTEE_EXCLUDE_PATTERNS = (
    "hall rep",
    "hall reps",
    "st. stephen",
    "st stephen",
    "st. stephen's green",
    "st. stephens green",
    "st stephen's green",
    "st stephens green",
    "ssg",
)


def _active_term_cutoff() -> date:
    return date.today()


def _active_term_filters() -> List:
    return [Term.end >= _active_term_cutoff()]


def _get_committee_exclude_patterns() -> List[str]:
    raw = os.getenv("COMMITTEE_EXCLUDE_PATTERNS", "").strip()
    if raw:
        return [pattern.strip().lower() for pattern in raw.split(",") if pattern.strip()]
    return list(DEFAULT_COMMITTEE_EXCLUDE_PATTERNS)


def _is_committee_body(body_name: Optional[str], exclude_patterns: Optional[Iterable[str]] = None) -> bool:
    if not body_name:
        return False
    patterns = list(exclude_patterns) if exclude_patterns is not None else _get_committee_exclude_patterns()
    name = body_name.lower()
    return not any(pattern in name for pattern in patterns)


def _person_email(person: Optional[Person]) -> Optional[str]:
    if not person:
        return None
    return getattr(person, "email", None) or getattr(person, "email_address", None)


def _is_chair_title_exact(title: Optional[str]) -> bool:
    return (title or "").strip() == "Chair"


def _build_committee_chair_diagnostics(
    committees: Iterable[Body],
    chair_offices_by_body: Dict[int, List[Office]],
    active_terms_by_body: Dict[int, List[Term]],
) -> Tuple[List[Dict[str, object]], List[str]]:
    diagnostics: List[Dict[str, object]] = []
    warnings: List[str] = []

    for committee in committees:
        body_id = committee.body_id
        chair_offices = chair_offices_by_body.get(body_id, [])
        active_terms = active_terms_by_body.get(body_id, [])
        has_email = any(_person_email(term.person) for term in active_terms)

        if not chair_offices:
            warnings.append(f"{committee.name}: no Chair office")
        elif not active_terms:
            warnings.append(f"{committee.name}: no active Chair term")
        elif not has_email:
            warnings.append(f"{committee.name}: Chair term has no email")

        diagnostics.append(
            {
                "body_name": committee.name,
                "chair_office_exists": bool(chair_offices),
                "active_chair_terms": len(active_terms),
                "chair_term_has_email": bool(has_email),
            }
        )

    return diagnostics, warnings


class DatabaseQueryTool(BaseTool):
    """
    CrewAI tool for querying governance data from the database.

    Provides methods to look up council officers, committee chairs,
    committee members, and other governance information.
    """

    name: str = "Database Query Tool"
    description: str = (
        "Query the governance database for information about council officers, "
        "committee chairs, committee members, and other governance data. "
        "Use this to get current contact information and roster details."
    )

    last_committee_chair_diagnostics: List[Dict[str, object]] = []
    last_committee_chair_warnings: List[str] = []

    def _run(self, query_type: str, **kwargs) -> str:
        """
        Execute a database query based on the query_type.

        Args:
            query_type: Type of query ('officers', 'chairs', 'committee_members', etc.)
            **kwargs: Additional parameters specific to the query type

        Returns:
            String representation of query results
        """
        try:
            if query_type == "officers":
                results = self.get_council_officers()
            elif query_type == "chairs":
                results = self.get_committee_chairs()
            elif query_type == "committee_members":
                committee_name = kwargs.get("committee_name")
                if not committee_name:
                    return "Error: committee_name parameter required for committee_members query"
                results = self.get_committee_members(committee_name)
            else:
                return f"Error: Unknown query_type '{query_type}'"

            return str(results)
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            return f"Error executing query: {e}"

    def get_council_officers(self) -> List[str]:
        """
        Get email addresses of all active council officers from Clerk's
        "Residents Council Officers" mailing-list source.

        Council officers receive emails for ALL meeting types.

        Returns:
            List of email addresses
        """
        db = get_db_session()
        try:
            # Match Clerk report behavior exactly for the "Residents Council Officers"
            # list source: Body.name == "Residents Council".
            council = db.query(Body).filter(
                Body.name == "Residents Council"
            ).first()

            if not council:
                logger.warning("No council body found in database")
                return []

            # Get all active terms for council offices
            active_terms = db.query(Term).join(
                Office, Term.term_office_id == Office.office_id
            ).join(
                Person, Term.term_person_id == Person.person_id
            ).filter(
                Office.office_body_id == council.body_id,
                *_active_term_filters(),
            ).all()

            office_titles = sorted(set(
                term.office.title
                for term in active_terms
                if getattr(term, "office", None) and term.office.title
            ))
            logger.debug(
                "Council officer titles matched (%d): %s",
                len(office_titles),
                office_titles,
            )

            # Extract unique email addresses (filter out None)
            emails = list(set([
                term.person.email
                for term in active_terms
                if hasattr(term.person, 'email') and term.person.email
            ]))

            logger.info(
                "Found %d Residents Council officer email address(es) from Clerk source",
                len(emails),
            )
            return sorted(emails)

        except Exception as e:
            logger.error(f"Error querying council officers: {e}")
            raise
        finally:
            db.close()

    def get_residents_council_officers_mailing_list(self) -> List[str]:
        """
        Alias for the Clerk "Residents Council Officers" mailing list.

        Returns:
            List of email addresses.
        """
        return self.get_council_officers()

    def get_committee_chairs(self) -> List[str]:
        """
        Get email addresses of all active committee chairs.

        Committee chairs receive emails ONLY for "open" meeting types.

        Returns:
            List of email addresses
        """
        db = get_db_session()
        try:
            # Get all committee bodies (exclude the Residents Council)
            committees_all = db.query(Body).filter(
                ~Body.name.ilike('%council%')
            ).all()

            if not committees_all:
                logger.warning("No committees found in database")
                return []

            exclude_patterns = _get_committee_exclude_patterns()
            excluded = [c for c in committees_all if not _is_committee_body(c.name, exclude_patterns)]
            committees = [c for c in committees_all if _is_committee_body(c.name, exclude_patterns)]

            if excluded:
                logger.debug(
                    "Excluded non-committee bodies: %s",
                    [c.name for c in excluded],
                )

            if not committees:
                logger.warning("No committees found after exclusion filtering")
                return []

            committee_ids = [c.body_id for c in committees]
            logger.debug("Committees found: %d", len(committee_ids))

            # Get chair offices for these committees
            chair_offices = db.query(Office).filter(
                Office.office_body_id.in_(committee_ids),
                Office.title == "Chair",
            ).all()

            if not chair_offices:
                logger.warning("No chair offices found for committees")
            else:
                logger.debug("Chair offices found: %d", len(chair_offices))

            office_titles = sorted(set(
                office.title for office in chair_offices if office.title
            ))
            if office_titles:
                logger.debug(
                    "Committee chair office titles matched (%d): %s",
                    len(office_titles),
                    office_titles,
                )
            unexpected_titles = sorted(set(
                office.title for office in chair_offices if not _is_chair_title_exact(office.title)
            ))
            if unexpected_titles:
                logger.debug("Unexpected chair office titles encountered: %s", unexpected_titles)

            office_ids = [o.office_id for o in chair_offices]

            # Get terms for these chair offices
            if office_ids:
                active_terms = db.query(Term).join(
                    Office, Term.term_office_id == Office.office_id
                ).join(
                    Person, Term.term_person_id == Person.person_id
                ).filter(
                    Term.term_office_id.in_(office_ids),
                    *_active_term_filters(),
                ).all()
            else:
                active_terms = []
            logger.debug("Active chair terms found: %d", len(active_terms))

            chair_offices_by_body: Dict[int, List[Office]] = {}
            for office in chair_offices:
                chair_offices_by_body.setdefault(office.office_body_id, []).append(office)

            active_terms_by_body: Dict[int, List[Term]] = {}
            for term in active_terms:
                if not getattr(term, "office", None):
                    continue
                active_terms_by_body.setdefault(term.office.office_body_id, []).append(term)

            diagnostics, warnings = _build_committee_chair_diagnostics(
                committees,
                chair_offices_by_body,
                active_terms_by_body,
            )
            self.last_committee_chair_diagnostics = diagnostics
            self.last_committee_chair_warnings = warnings

            for warning in warnings:
                logger.warning("Committee chair issue: %s", warning)

            # Extract unique email addresses (filter out None)
            emails = list(set([
                _person_email(term.person)
                for term in active_terms
                if _person_email(term.person)
            ]))

            logger.info(
                "Committee chair summary: committees=%d, chair_offices=%d, active_chair_terms=%d, unique_emails=%d",
                len(committees),
                len(chair_offices),
                len(active_terms),
                len(emails),
            )
            logger.debug("Unique chair emails found: %d", len(emails))
            logger.info(f"Found {len(emails)} committee chair email addresses")
            return sorted(emails)

        except Exception as e:
            logger.error(f"Error querying committee chairs: {e}")
            raise
        finally:
            db.close()

    def get_committee_members(self, committee_name: str) -> List[Dict[str, str]]:
        """
        Get all active members of a specific committee.

        Args:
            committee_name: Name of the committee (e.g., "Finance")

        Returns:
            List of dicts with keys: name, email, office_title
        """
        db = get_db_session()
        try:
            # Find the committee body
            committee = db.query(Body).filter(
                Body.name.ilike(f"%{committee_name}%")
            ).first()

            if not committee:
                logger.warning(f"Committee '{committee_name}' not found")
                return []

            # Get all terms for this committee
            active_terms = db.query(Term).join(
                Office, Term.term_office_id == Office.office_id
            ).join(
                Person, Term.term_person_id == Person.person_id
            ).filter(
                Office.office_body_id == committee.body_id
            ).all()

            # Build member list
            members = []
            for term in active_terms:
                # Get name - try various possible field names
                name = getattr(term.person, 'full_name', None) or \
                       f"{getattr(term.person, 'first_name', '')} {getattr(term.person, 'last_name', '')}".strip()

                email = getattr(term.person, 'email', None) or getattr(term.person, 'email_address', None) or ''

                member = {
                    'name': name,
                    'email': email,
                    'office_title': term.office.title
                }
                members.append(member)

            logger.info(f"Found {len(members)} members for committee '{committee_name}'")
            return members

        except Exception as e:
            logger.error(f"Error querying committee members: {e}")
            raise
        finally:
            db.close()

    def get_all_committees(self) -> List[Dict[str, str]]:
        """
        Get a list of all committees (excludes the Residents Council).

        Returns:
            List of dicts with keys: body_id, name, mission
        """
        db = get_db_session()
        try:
            committees = db.query(Body).filter(
                ~Body.name.ilike('%council%')
            ).order_by(Body.body_precedence).all()

            result = [
                {
                    'body_id': c.body_id,
                    'name': c.name,
                    'mission': c.mission or ''
                }
                for c in committees
            ]

            logger.info(f"Found {len(result)} committees")
            return result

        except Exception as e:
            logger.error(f"Error querying committees: {e}")
            raise
        finally:
            db.close()

    def get_person_by_email(self, email: str) -> Optional[Dict[str, any]]:
        """
        Look up a person by their email address.

        Args:
            email: Email address to search for

        Returns:
            Dict with person details or None if not found
        """
        db = get_db_session()
        try:
            # Try to find person by email field (try common field names)
            person = db.query(Person).filter(
                Person.email.ilike(email)
            ).first()

            if not person:
                logger.info(f"No person found with email '{email}'")
                return None

            # Build result with flexible field access
            result = {
                'person_id': person.person_id,
                'full_name': getattr(person, 'full_name', None) or
                            f"{getattr(person, 'first_name', '')} {getattr(person, 'last_name', '')}".strip(),
                'email': getattr(person, 'email', None) or getattr(person, 'email_address', ''),
                'phone': getattr(person, 'phone', None) or getattr(person, 'telephone', '') or '',
                'unit_number': getattr(person, 'apt_number', None) or getattr(person, 'unit_number', '') or ''
            }

            return result

        except Exception as e:
            logger.error(f"Error querying person by email: {e}")
            raise
        finally:
            db.close()
