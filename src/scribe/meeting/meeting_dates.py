"""Utilities for computing meeting dates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Dict


@dataclass(frozen=True)
class MeetingDates:
    last_meeting_date: date
    meeting_date: date
    next_meeting_date: date


def _first_thursday(year: int, month: int) -> date:
    first_day = date(year, month, 1)
    # Python weekday(): Monday=0 ... Sunday=6. Thursday=3.
    offset = (3 - first_day.weekday()) % 7
    return first_day.replace(day=1 + offset)


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    new_month = month + delta
    new_year = year + (new_month - 1) // 12
    new_month = (new_month - 1) % 12 + 1
    return new_year, new_month


def _format_date(value: date) -> str:
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def compute_meeting_dates(cycle: str, meeting_type: str) -> Dict[str, str]:
    """
    Compute formatted meeting dates for the given cycle.

    Args:
        cycle: YYYY-MM cycle identifier.
        meeting_type: Meeting type (regular|open|association). Currently unused.

    Returns:
        Dict with last_meeting_date, meeting_date, next_meeting_date formatted as "Month D, YYYY".
    """
    if not cycle or len(cycle) != 7 or cycle[4] != "-":
        raise ValueError("cycle must be in YYYY-MM format")

    year = int(cycle[:4])
    month = int(cycle[5:7])

    prev_year, prev_month = _add_months(year, month, -1)
    next_year, next_month = _add_months(year, month, 1)

    meeting_dates = MeetingDates(
        last_meeting_date=_first_thursday(prev_year, prev_month),
        meeting_date=_first_thursday(year, month),
        next_meeting_date=_first_thursday(next_year, next_month),
    )

    return {
        "last_meeting_date": _format_date(meeting_dates.last_meeting_date),
        "meeting_date": _format_date(meeting_dates.meeting_date),
        "next_meeting_date": _format_date(meeting_dates.next_meeting_date),
    }


def cycle_from_meeting_date(meeting_date: str) -> str:
    """
    Derive a YYYY-MM cycle from a meeting date string.

    Accepts:
    - YYYY-MM
    - YYYY-MM-DD
    """
    if not meeting_date:
        raise ValueError("meeting_date is required to derive cycle")
    if re.match(r"^\d{4}-\d{2}$", meeting_date):
        return meeting_date
    if re.match(r"^\d{4}-\d{2}-\d{2}$", meeting_date):
        return meeting_date[:7]
    raise ValueError(f"Invalid meeting_date format: {meeting_date}. Expected YYYY-MM or YYYY-MM-DD")
