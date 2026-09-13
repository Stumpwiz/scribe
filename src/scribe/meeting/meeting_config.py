"""Canonical meeting metadata (time, locations, and type rules)."""

from __future__ import annotations

from datetime import date
from typing import Dict


MEETING_TIME = "2:00 p.m."

MEETING_LOCATIONS: Dict[str, str] = {
    "regular": "McAuley Conference Room",
    "open": "Performing Arts Center (PAC)",
    "association": "Performing Arts Center (PAC)",
}


def meeting_type_for_month(month: int) -> str:
    if month == 12:
        return "association"
    if month in (3, 6, 9):
        return "open"
    return "regular"


def meeting_type_for_date(meeting_date: date) -> str:
    return meeting_type_for_month(meeting_date.month)


def next_meeting_type_for_date(meeting_date: date) -> str:
    year = meeting_date.year
    month = meeting_date.month + 1
    if month == 13:
        year += 1
        month = 1
    return meeting_type_for_month(month)


def meeting_location_for_type(meeting_type: str) -> str:
    normalized = (meeting_type or "").strip().lower()
    if normalized in MEETING_LOCATIONS:
        return MEETING_LOCATIONS[normalized]
    raise ValueError(f"Unknown meeting type for location: {meeting_type}")
