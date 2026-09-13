"""
CLI entrypoint for Formatter v1.

Example:
  python -m src.scribe.cli.format --pdf /path/to/report.pdf --office president

Optional:
  --dpi 300
  --out src/scribe/output/reports_png
  --no-trim
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.scribe.tools.formatter_service import FormatterService


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Scribe Formatter v1: PDF -> PNG appendix assets")
    p.add_argument("--pdf", required=True, help="Path to a PDF report file.")
    p.add_argument("--office", required=True, help="Office stem for naming (e.g., president, dining).")
    p.add_argument("--dpi", type=int, default=FormatterService.DEFAULT_DPI, help="Render DPI (default: 300).")
    p.add_argument("--out", default=None,
                   help="Output directory (default: src/scribe/output/appendix_assets/<ts>/<office>).")
    p.add_argument("--no-trim", action="store_true", help="Disable whitespace trimming (even if Pillow is available).")
    p.add_argument("--json", action="store_true", help="Print full JSON result to stdout.")
    return p


def main() -> int:
    args = build_parser().parse_args()

    svc = FormatterService()
    result = svc.pdf_to_pngs_v1(
        pdf_path=args.pdf,
        office=args.office,
        output_dir=args.out,
        dpi=args.dpi,
        trim_whitespace=(not args.no_trim),
    )

    if args.json:
        print(json.dumps(result, indent=2))
        return 0 if result.get("success") else 1

    print("\n=== Format Result ===")
    print(f"Success: {result.get('success')}")
    print(f"Status: {result.get('status')}")
    print(f"PDF: {result.get('pdf_path')}")
    print(f"Office: {result.get('office')}")
    print(f"DPI: {result.get('dpi')}")
    print(f"Pages: {result.get('pages')}")
    print(f"Output dir: {result.get('output_dir')}")
    print(f"Manifest: {result.get('manifest_path')}")
    print(f"Images: {len(result.get('images') or [])}")

    # Show the generated filenames (not full paths) for quick copying into LaTeX naming conventions
    images = result.get("images") or []
    if images:
        print("\nGenerated:")
        for pth in images:
            print(f"  - {Path(pth).name}")

    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
