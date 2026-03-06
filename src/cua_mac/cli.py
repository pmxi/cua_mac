from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from cua_mac.mac import MacComputerBackend


def default_artifact_dir() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path("artifacts") / timestamp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local macOS computer-use runner.")
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=default_artifact_dir(),
        help="Directory where screenshots are written.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    screenshot_parser = subparsers.add_parser(
        "screenshot",
        help="Capture the current screen and print the capture metadata.",
    )
    screenshot_parser.add_argument(
        "--label",
        default="manual-capture",
        help="Filename label for the screenshot.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    backend = MacComputerBackend(artifact_dir=args.artifact_dir)

    if args.command == "screenshot":
        screenshot = backend.capture_screenshot(args.label)
        print(
            json.dumps(
                {
                    "height_px": screenshot.height_px,
                    "path": str(screenshot.path),
                    "scale_factor": screenshot.scale_factor,
                    "width_px": screenshot.width_px,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    parser.error(f"Unhandled command: {args.command}")
    return 2
