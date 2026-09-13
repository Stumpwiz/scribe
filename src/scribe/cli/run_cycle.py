"""
Orchestrator for the monthly cycle pipeline.

Phases (in order):
 1) Stage attachments from Gmail into cycle/originals/<office>/ (dry-run by default)
 2) Collect/canonicalize PDFs into cycle/pdf/
 3) Format PDFs into PNG appendix assets and manifest.json

Each phase delegates to existing CLIs via their main(argv) entrypoints.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.scribe.cli import ingest, collect_pdfs, format_all
from src.scribe.tools.formatter_service import FormatterService

DEFAULT_STAGE_QUERY = "in:inbox has:attachment newer_than:14d"
DEFAULT_MAX = 25
DEFAULT_LABEL = "Scribe/Incoming"
DEFAULT_OUT_ROOT = "src/scribe/output/cycles"


def compute_cycle_root(out_root: str, cycle: str) -> Path:
    """Resolve the cycle root using a consistent expansion + resolution."""
    return Path(out_root).expanduser().resolve() / cycle


def validate_cycle(cycle: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}", cycle or ""):
        raise ValueError("--cycle must be in YYYY-MM format")
    return cycle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the monthly cycle pipeline (stage -> collect -> format).")
    parser.add_argument("--cycle", required=True, help="Cycle identifier YYYY-MM (e.g., 2026-02).")
    parser.add_argument("--query", default=DEFAULT_STAGE_QUERY, help="Gmail query for staging step.")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX, help="Max messages to process in staging.")
    parser.add_argument("--apply", action="store_true", help="Apply label/log and download attachments (staging).")
    parser.add_argument("--force", action="store_true",
                        help="Restage even if messages already have the label (with --apply).")
    parser.add_argument(
        "--skip-unknown",
        action="store_true",
        help="Skip staging attachments when office inference returns 'unknown'.",
    )
    parser.add_argument("--label", default=DEFAULT_LABEL, help="Label to apply during staging.")
    parser.add_argument("--log-path", default=None, help="Override ingestion log path.")
    parser.add_argument("--out-root", default=DEFAULT_OUT_ROOT, help="Root cycles directory.")
    parser.add_argument("--map", default=None, help="Path to office->pdf mapping JSON (falls back to CLI defaults).")
    parser.add_argument("--dpi", type=int, default=FormatterService.DEFAULT_DPI, help="Render DPI for formatting.")
    parser.add_argument("--no-trim", action="store_true", help="Disable whitespace trimming in formatting.")
    parser.add_argument("--skip-stage", action="store_true", help="Skip staging step.")
    parser.add_argument("--skip-collect", action="store_true", help="Skip collect step.")
    parser.add_argument("--skip-format", action="store_true", help="Skip formatting step.")
    parser.add_argument("--keep-going", action="store_true", help="Continue even if a step fails.")
    parser.add_argument("--json", dest="json_out", action="store_true", help="Print summary JSON at end.")
    return parser


def run_stage(args: argparse.Namespace) -> Dict[str, Any]:
    if args.skip_stage:
        return {"skipped": True, "success": True, "exit_code": 0}

    print("\n=== Stage: Gmail attachments -> originals/ ===")
    stage_argv = [
        "--stage-attachments",
        "--cycle",
        args.cycle,
        "--query",
        args.query,
        "--max",
        str(args.max),
        "--label",
        args.label,
        "--out-root",
        args.out_root,
    ]
    if args.log_path:
        stage_argv += ["--log-path", args.log_path]
    if args.apply:
        stage_argv.append("--apply")
    if args.force:
        stage_argv.append("--force")
    if args.skip_unknown:
        stage_argv.append("--skip-unknown")

    exit_code = ingest.main(stage_argv)
    result = ingest.LAST_RESULT
    return {
        "skipped": False,
        "success": exit_code == 0,
        "exit_code": exit_code,
        "result": result,
    }


def run_collect(args: argparse.Namespace, cycle_root: Path) -> Dict[str, Any]:
    if args.skip_collect:
        return {"skipped": True, "success": True, "exit_code": 0}

    print("\n=== Collect: PDFs -> pdf/ ===")

    collect_argv = [
        "--cycle",
        args.cycle,
        "--output-root",
        args.out_root,
    ]
    if args.map:
        collect_argv += ["--map", args.map]
    if not args.apply:
        collect_argv.append("--dry-run")

    exit_code = collect_pdfs.main(collect_argv)
    result = collect_pdfs.LAST_RESULT
    return {
        "skipped": False,
        "success": exit_code == 0,
        "exit_code": exit_code,
        "result": result,
    }


def run_format(args: argparse.Namespace, cycle_root: Path) -> Dict[str, Any]:
    if not args.apply:
        return {
            "skipped": True,
            "success": True,
            "exit_code": 0,
            "result": None,
            "skipped_reason": "apply_not_set",
        }

    if args.skip_format:
        return {"skipped": True, "success": True, "exit_code": 0}

    print("\n=== Format: PDFs -> png/ + manifest ===")

    input_dir = cycle_root / "pdf"
    format_argv = [
        "--cycle",
        args.cycle,
        "--input-dir",
        str(input_dir),
        "--dpi",
        str(args.dpi),
    ]
    if args.map:
        format_argv += ["--map", args.map]
    if args.no_trim:
        format_argv.append("--no-trim")

    exit_code = format_all.main(format_argv)
    result = format_all.LAST_RESULT
    return {
        "skipped": False,
        "success": exit_code == 0,
        "exit_code": exit_code,
        "result": result,
    }


def summarize(stage_res: Dict[str, Any], collect_res: Dict[str, Any], format_res: Dict[str, Any]) -> Dict[str, Any]:
    summary = {
        "stage": stage_res,
        "collect": collect_res,
        "format": format_res,
    }
    return summary


def _summarize_originals(stage_result: Dict[str, Any]) -> Dict[str, int]:
    by_office: Dict[str, int] = defaultdict(int)
    for record in (stage_result or {}).get("processed") or []:
        for attachment in record.get("attachments") or []:
            office = attachment.get("office") or "unknown"
            by_office[office] += 1
    return dict(sorted(by_office.items()))


def build_minutes_checklist(cycle_root: Path, stage_res: Dict[str, Any], collect_res: Dict[str, Any],
                            format_res: Dict[str, Any]) -> Dict[str, Any]:
    stage_result = (stage_res or {}).get("result") or {}
    collect_result = (collect_res or {}).get("result") or {}
    format_result = (format_res or {}).get("result") or {}

    originals_by_office = _summarize_originals(stage_result) if stage_result else {}
    collect_counts = (collect_result.get("counts") or {}) if collect_result else {}
    format_counts = {
        "ok": format_result.get("ok_count") if format_result else None,
        "failed": format_result.get("fail_count") if format_result else None,
        "placeholder_used": format_result.get("placeholder_count") if format_result else None,
    }

    missing_offices = set()
    for key in ("missing_offices",):
        for item in collect_result.get(key, []) if collect_result else []:
            missing_offices.add(item)
    for item in format_result.get("missing_sources", []) if format_result else []:
        missing_offices.add(item)

    manifests = {
        "collect": collect_result.get("manifest_path") if collect_result else None,
        "format": format_result.get("manifest_path") if format_result else None,
    }

    return {
        "cycle_root": str(cycle_root),
        "originals_by_office": originals_by_office,
        "pdf_counts": {
            "copied_ok": collect_counts.get("copied"),
            "missing": collect_counts.get("missing"),
            "skipped_existing": collect_counts.get("skipped_existing"),
        },
        "png_counts": format_counts,
        "manifests": manifests,
        "missing_offices": sorted(missing_offices),
    }


def print_minutes_ready_checklist(checklist: Dict[str, Any]) -> None:
    print("\n=== Minutes-ready Checklist ===")
    print(f"- cycle_root: {checklist.get('cycle_root')}")
    originals = checklist.get("originals_by_office") or {}
    print(f"- originals_count_by_office: {originals if originals else 'n/a'}")
    pdf_counts = checklist.get("pdf_counts") or {}
    print(
        f"- pdf_copied_ok: {pdf_counts.get('copied_ok')} missing: {pdf_counts.get('missing')} skipped_existing: {pdf_counts.get('skipped_existing')}")
    png_counts = checklist.get("png_counts") or {}
    print(
        f"- png_generated_ok: {png_counts.get('ok')} failed: {png_counts.get('failed')} placeholder_used: {png_counts.get('placeholder_used')}")
    manifests = checklist.get("manifests") or {}
    print(f"- manifest_collect: {manifests.get('collect') or 'n/a'}")
    print(f"- manifest_format: {manifests.get('format') or 'n/a'}")
    missing_offices = checklist.get("missing_offices") or []
    print(f"- missing_offices: {missing_offices if missing_offices else 'none'}")


def print_human_summary(summary: Dict[str, Any], cycle_root: Path) -> None:
    print("\n=== Cycle Summary ===")
    print(f"Cycle root: {cycle_root}")
    for name in ["stage", "collect", "format"]:
        step = summary.get(name, {})
        status = "skipped" if step.get("skipped") else ("ok" if step.get("success") else "failed")
        print(f"- {name}: {status} (exit {step.get('exit_code')})")
    stage_result = summary.get("stage", {}).get("result") or {}
    collect_result = summary.get("collect", {}).get("result") or {}
    format_result = summary.get("format", {}).get("result") or {}

    if stage_result:
        print(
            f"  attachments processed: {stage_result.get('processed_count')} saved: {stage_result.get('saved_attachments_count')}")
    if collect_result:
        counts = (collect_result.get("counts") or {})
        print(
            f"  pdf collected ok: {counts.get('copied')} missing: {counts.get('missing')} skipped_existing: {counts.get('skipped_existing')}")
    if format_result:
        print(
            f"  formatted ok: {format_result.get('ok_count')} fail: {format_result.get('fail_count')} manifest: {format_result.get('manifest_path')}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1

    try:
        cycle = validate_cycle(args.cycle)
    except ValueError as exc:
        parser.error(str(exc))

    cycle_root = compute_cycle_root(args.out_root, cycle)
    print(f"Cycle root: {cycle_root}")
    print(f"Defaults: staging dry-run (unless --apply). Keep-going: {args.keep_going}")

    stage_res = run_stage(args)
    if stage_res["exit_code"] != 0 and not args.keep_going:
        collect_stub = {"skipped": True, "success": True, "exit_code": 0}
        format_stub = {"skipped": True, "success": True, "exit_code": 0}
        summary = summarize(stage_res, collect_stub, format_stub)
        checklist = build_minutes_checklist(cycle_root, stage_res, collect_stub, format_stub)
        print_human_summary(summary, cycle_root)
        if args.json_out:
            summary_with_checklist = dict(summary)
            summary_with_checklist["checklist"] = checklist
            print(json.dumps(summary_with_checklist, indent=2))
        print_minutes_ready_checklist(checklist)
        return stage_res["exit_code"]

    collect_res = run_collect(args, cycle_root)
    if collect_res["exit_code"] != 0 and not args.keep_going:
        format_stub = {"skipped": True, "success": True, "exit_code": 0}
        summary = summarize(stage_res, collect_res, format_stub)
        checklist = build_minutes_checklist(cycle_root, stage_res, collect_res, format_stub)
        print_human_summary(summary, cycle_root)
        if args.json_out:
            summary_with_checklist = dict(summary)
            summary_with_checklist["checklist"] = checklist
            print(json.dumps(summary_with_checklist, indent=2))
        print_minutes_ready_checklist(checklist)
        return collect_res["exit_code"]

    format_res = run_format(args, cycle_root)
    summary = summarize(stage_res, collect_res, format_res)

    checklist = build_minutes_checklist(cycle_root, stage_res, collect_res, format_res)

    print_human_summary(summary, cycle_root)
    print_minutes_ready_checklist(checklist)
    if args.json_out:
        summary_with_checklist = dict(summary)
        summary_with_checklist["checklist"] = checklist
        print(json.dumps(summary_with_checklist, indent=2))

    final_code = 0
    for step in summary.values():
        if not step.get("success"):
            final_code = step.get("exit_code") or 1
            break
    return final_code


if __name__ == "__main__":
    raise SystemExit(main())

# Dry-run example (no writes):
# python -m src.scribe.cli.run_cycle --cycle 2026-02 --map src/scribe/assets/reports/report_map.example.json
