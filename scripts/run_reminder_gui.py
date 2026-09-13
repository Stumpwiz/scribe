import argparse
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch the Scribe reminder GUI directly (no Crew orchestration)."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Bind port (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    parser.add_argument(
        "--allow-send",
        action="store_true",
        help="Allow real sends. By default DRY_RUN=true is enforced for safety.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    project_root = Path(__file__).resolve().parents[1]
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    if not args.allow_send and os.getenv("DRY_RUN") is None:
        os.environ["DRY_RUN"] = "true"

    from scribe.ui import create_app

    app = create_app()
    print(f"Starting reminder GUI on http://{args.host}:{args.port} (DRY_RUN={os.getenv('DRY_RUN', '')})")
    app.run(host=args.host, port=args.port, debug=args.debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
