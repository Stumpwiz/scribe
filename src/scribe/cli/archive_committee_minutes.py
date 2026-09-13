"""CLI for archiving and publishing committee minutes (dry-run by default)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.scribe.archive.committee_minutes import ArchiveMinutesError, build_plan, publish
from src.scribe.website.committee_modal import CommitteeModalError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Archive a committee-minutes DOCX as PDF and update the MRRA website.")
    parser.add_argument("--committee", required=True, help="Two-letter committee code (for example, SE).")
    parser.add_argument("--month", required=True, help="Meeting month in YYYY-MM format.")
    parser.add_argument("--source", required=True, type=Path, help="Source .docx minutes file.")
    parser.add_argument("--site-root", required=True, type=Path, help="Local MRRA website repository root.")
    parser.add_argument("--apply", action="store_true", help="Perform changes (the default is a dry run).")
    parser.add_argument("--force", action="store_true", help="Permit replacement of an existing archive PDF.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        plan = build_plan(args.committee, args.month, args.source, args.site_root, force=args.force)
        print("APPLY" if args.apply else "DRY RUN (no persistent changes)")
        print(f"Committee: {plan.committee}")
        print(f"Meeting month: {plan.month}")
        print(f"Source DOCX: {plan.source}")
        print(f"Destination PDF: {plan.destination}")
        print(f"Modal ID: {plan.modal_id}")
        print(f"Month button: {plan.month_label}")
        print(f"Old href: {plan.patch.old_href}")
        print(f"New href: {plan.patch.new_href}")
        print(f"Destination exists: {'yes' if plan.destination_exists else 'no'}")
        print(f"Anchor before: {plan.patch.before}")
        print(f"Anchor after:  {plan.patch.after}")
        changed = publish(plan, apply=args.apply)
        if changed:
            print("Published successfully:")
            for path in changed:
                print(f"  {path}")
        else:
            print("Conversion validated; temporary files cleaned up.")
        return 0
    except (ArchiveMinutesError, CommitteeModalError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
