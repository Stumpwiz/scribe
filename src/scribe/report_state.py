"""Persistent cycle inputs for intentional written-appendix omissions."""

from __future__ import annotations

import json
import re
from collections.abc import Collection
from pathlib import Path


STATE_ROOT = Path(__file__).resolve().parent / "input" / "cycles"


def load_omitted_offices(cycle: str, known_offices: Collection[str]) -> set[str]:
    """Read optional source state; unspecified offices keep normal behavior.

    This input lives outside generated cycle output so rebuilding that output
    cannot erase the decision. Unknown offices/policies fail before any writes.
    """
    if not re.fullmatch(r"\d{4}-\d{2}", cycle):
        raise ValueError("Report-state cycle must be YYYY-MM")
    path = STATE_ROOT / cycle / "report_state.json"
    if not path.exists():
        return set()
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read report state {path}: {exc}") from exc
    if not isinstance(state, dict) or set(state) != {"offices"} or not isinstance(state["offices"], dict):
        raise ValueError(f"Report state {path} must contain only an 'offices' object")
    for office, policy in state["offices"].items():
        if office not in known_offices:
            raise ValueError(f"Unknown office {office!r} in report state {path}")
        if policy != {"appendix": "none"}:
            raise ValueError(f"Report state {path}: {office} must specify only appendix='none'")
    return set(state["offices"])
