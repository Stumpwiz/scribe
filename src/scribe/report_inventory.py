"""Cycle-aware report inventory and open-minutes ordering."""

from __future__ import annotations

from collections.abc import Mapping


CONDITIONAL_REPORTS: dict[str, dict[str, object]] = {
    "nominatingCommittee": {
        "filename": "nominatingCommittee.pdf",
        "months": frozenset({9}),
        "after": "specialEventsAndTrips",
    },
}


def reports_for_cycle(mapping: Mapping[str, str], cycle: str) -> dict[str, str]:
    """Return the expected report mapping for ``cycle`` (YYYY-MM)."""
    month = int(cycle.split("-", 1)[1])
    reports = {
        office: filename
        for office, filename in mapping.items()
        if office not in CONDITIONAL_REPORTS
    }
    for office, rule in CONDITIONAL_REPORTS.items():
        if month in rule["months"]:
            reports[office] = str(rule["filename"])
    return reports


def ordered_reports_for_cycle(base_order: list[str], cycle: str) -> list[str]:
    """Insert cycle-specific reports without changing the base report order."""
    expected = reports_for_cycle({}, cycle)
    order = list(base_order)
    for office in expected:
        after = str(CONDITIONAL_REPORTS[office]["after"])
        order.insert(order.index(after) + 1, office)
    return order
