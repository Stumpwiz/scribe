import argparse
import re
import sys
from datetime import date
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a meeting agenda PDF for a user-provided date with empty old/new business sections."
    )
    parser.add_argument(
        "--date",
        dest="meeting_date",
        help="Meeting date in YYYY-MM-DD format. If omitted, you will be prompted.",
    )
    return parser.parse_args()


def _resolve_meeting_date(raw_value: str | None) -> str:
    candidate = raw_value
    if not candidate:
        candidate = input("Meeting date (YYYY-MM-DD): ").strip()

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", candidate):
        raise ValueError(f"Invalid date format: {candidate!r}. Expected YYYY-MM-DD.")

    # Validates impossible dates such as 2026-02-30.
    date.fromisoformat(candidate)
    return candidate


def main() -> int:
    args = _parse_args()
    try:
        meeting_date = _resolve_meeting_date(args.meeting_date)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2

    project_root = Path(__file__).resolve().parents[1]
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from scribe.tools.meeting_agenda_generator_tool import MeetingAgendaGeneratorTool

    tool = MeetingAgendaGeneratorTool()
    meeting_info = {
        "meetingDate": meeting_date,
        "oldBusinessItems": [],
        "newBusinessItems": [],
    }

    print(f"Generating agenda for {meeting_date}...")
    result = tool._run(meeting_info=meeting_info)

    success = bool(result.get("success"))
    print(f"Success: {success}")
    if result.get("pdfPath"):
        print(f"PDF Path: {result['pdfPath']}")
    if result.get("logPath"):
        print(f"Log Path: {result['logPath']}")
    if result.get("log"):
        print("Compiler Log (first 500 chars):")
        print(str(result["log"])[:500])

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
