import argparse
import sys
from typing import List, Optional

from googleapiclient.discovery import build

from src.scribe.google_auth.google_auth_helper import get_google_credentials
from src.scribe.tools.email_service import EmailService, DEFAULT_INGEST_QUERY

DEFAULT_QUERY = DEFAULT_INGEST_QUERY
LAST_RESULT: Optional[dict] = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manual IngestorAgent v1 (Gmail triage: classify + label + JSONL log)"
    )
    parser.add_argument("--max", type=int, default=10, help="Max messages to process")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply labels and write log (default is dry-run)",
    )
    parser.add_argument("--label", default="Scribe/Incoming", help="Label to apply")
    parser.add_argument("--log-path", default=None, help="Override JSONL log path")
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help=f"Gmail search query (default: {DEFAULT_QUERY!r})",
    )
    parser.add_argument(
        "--whoami",
        action="store_true",
        help="Print authorized Gmail account and exit (no ingest)",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Display only report-like messages (report-submission, forwarded-report, meeting-minutes).",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-stage/download attachments even if the message is already labeled (useful for development).",
    )

    parser.add_argument(
        "--stage-attachments",
        action="store_true",
        help="Stage attachments to cycle/originals using v2 flow (adds label/log unless dry-run).",
    )

    parser.add_argument(
        "--skip-unknown",
        action="store_true",
        help="Skip staging attachments when office cannot be inferred (office='unknown').",
    )

    parser.add_argument(
        "--cycle",
        default=None,
        help="Cycle identifier (YYYY-MM) required when using --stage-attachments.",
    )
    parser.add_argument(
        "--out-root",
        default="src/scribe/output/cycles",
        help="Root output directory for cycles (default: src/scribe/output/cycles)",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    global LAST_RESULT
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1

    if args.whoami:
        try:
            creds = get_google_credentials()
            svc = build("gmail", "v1", credentials=creds)
            profile = svc.users().getProfile(userId="me").execute()
            print(profile.get("emailAddress", "unknown"))
            return 0
        except Exception as exc:
            print(f"Failed to resolve Gmail identity: {exc}", file=sys.stderr)
            return 1

    if args.stage_attachments:
        if not args.cycle:
            print("--cycle is required when using --stage-attachments", file=sys.stderr)
            sys.exit(2)

        result = EmailService()._run(
            action="stage_attachments_v2",
            max_results=args.max,
            label_name=args.label,
            log_path=args.log_path,
            dry_run=not args.apply,
            query=args.query,
            cycle=args.cycle,
            out_root=args.out_root,
            force=args.force,
            skip_unknown=args.skip_unknown,
        )
        if not result.get("success"):
            print("\n=== Ingest Result ===")
            print(f"Success: False")
            print(f"Status: {result.get('status')}")
            print(f"Action: {result.get('action')}")
            print(f"Error: {result.get('error') or result.get('message')}")
            LAST_RESULT = result
            return 1

    else:
        result = EmailService.ingest_unread_inbox_v1(
            max_results=args.max,
            label_name=args.label,
            log_path=args.log_path,
            dry_run=not args.apply,
            query=args.query,
        )

    processed = result.get("processed", []) or []
    LAST_RESULT = result

    if args.report_only:
        # v1 has classification; v2 doesn't (yet). For v2, treat any message with attachments as "report-like".
        report_classes = {"report-submission", "forwarded-report", "meeting-minutes"}
        if result.get("action") == "stage_attachments_v2":
            processed = [p for p in processed if (p.get("attachments") or [])]
        else:
            processed = [p for p in processed if p.get("classification") in report_classes]

    print("\n=== Ingest Result ===")
    print(f"Action: {result.get('action')}")
    print(f"Dry run: {not args.apply}")
    print(f"Candidates: {result.get('candidates_count')}")
    if args.report_only:
        print(f"Report-like messages displayed: {len(processed)}")
        print(f"Processed (unlabeled): {result.get('processed_count')}")
    else:
        print(f"Processed: {result.get('processed_count')}")
    print(f"Skipped (already labeled): {result.get('skipped_already_labeled')}")
    print(f"Label: {result.get('label_name')} ({result.get('label_id')})")
    print(f"Log path: {result.get('log_path')}")
    print(f"Query: {result.get('query')}")

    if args.report_only and processed:
        print("\nReport Messages:")
        for item in processed:
            print("-" * 50)
            print(f"From: {item.get('from')}")
            print(f"Subject: {item.get('subject')}")
            print(f"Office: {item.get('office')}")
            print(f"Classification: {item.get('classification')}")
            print(f"Classification confidence: {item.get('classification_confidence')}")
            att_count = item.get("attachments_count")
            attachments = item.get("attachments") or []
            if att_count is None:
                att_count = len(attachments)
            print(f"Attachments: {att_count}")
            if attachments:
                filenames = []
                for att in attachments:
                    if not isinstance(att, dict):
                        continue
                    filename = (
                        att.get("normalized_filename")
                        or att.get("filename")
                        or att.get("original_filename")
                    )
                    if filename:
                        filenames.append(str(filename))
                if filenames:
                    print("Attachment filenames:")
                    for name in filenames:
                        print(f"  - {name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
