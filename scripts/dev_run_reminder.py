import argparse
import asyncio
import os
from datetime import datetime
from pathlib import Path

# Ensure DRY_RUN defaults to true unless explicitly disabled.
if os.getenv("DRY_RUN") is None:
    os.environ["DRY_RUN"] = "true"

from scribe.meeting.meeting_config import meeting_type_for_date
from scribe.tasks.reminder_tasks import send_meeting_notification_workflow


class _MockTask:
    def __init__(self, context):
        self.context = context


class _MockAgent:
    name = "DevRunner"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run reminder workflow helper")
    parser.add_argument(
        "--meeting-date",
        default="2026-05-07",
        help="Meeting date in YYYY-MM-DD format (default: 2026-05-07)",
    )
    parser.add_argument(
        "--meeting-type",
        choices=("regular", "open", "association"),
        default=None,
        help="Optional override; if omitted, type is derived from meeting date",
    )
    parser.add_argument(
        "--location",
        default=None,
        help="Optional location override",
    )
    parser.add_argument(
        "--allow-send",
        action="store_true",
        help="Allow non-dry run execution (default remains dry-run)",
    )
    return parser.parse_args()


def _build_context(args: argparse.Namespace) -> dict:
    meeting_date = datetime.strptime(args.meeting_date, "%Y-%m-%d").date()
    meeting_type = args.meeting_type or meeting_type_for_date(meeting_date)

    context = {
        "meetingDate": meeting_date.isoformat(),
        "meetingType": meeting_type,
        "meetingTime": "2:00 PM",
        "dry_run": not args.allow_send,
    }
    if args.location:
        context["location"] = args.location
    return context


def main():
    args = _parse_args()
    context = _build_context(args)
    task = _MockTask(context)
    agent = _MockAgent()

    print(f"Starting ReminderAgent dev run (DRY_RUN={context['dry_run']})...")
    print(f"Meeting date: {context['meetingDate']}")
    print(f"Meeting type: {context['meetingType']}")
    print("Recipients source: Clerk mailing list 'Residents Council Officers' (default)")

    result = asyncio.run(send_meeting_notification_workflow(None, agent, task))

    run_id = result.get("run_id") or os.getenv("RUN_ID") or "(unknown)"
    print(f"Run ID: {run_id}")

    preview_path = result.get("preview_path")
    if preview_path:
        print(f"Email preview: {preview_path}")
    else:
        print("Email preview path not available")

    attachment_path = result.get("attachment_path")
    if attachment_path:
        print(f"Agenda PDF: {attachment_path}")
    else:
        agendas_dir = Path(__file__).resolve().parents[1] / "src" / "scribe" / "output" / "agendas"
        canonical_name = f"agenda_{context['meetingDate']}_{context['meetingType']}.pdf"
        canonical_path = agendas_dir / canonical_name
        if canonical_path.exists():
            print(f"Agenda PDF: {canonical_path}")
        else:
            print("Agenda PDF not found.")

    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Recipient count: {result.get('recipient_count', 'unknown')}")
    print("Dev run complete.")


if __name__ == "__main__":
    main()
