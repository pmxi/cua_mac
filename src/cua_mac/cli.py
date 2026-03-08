from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from cua_mac.mac import MacComputerBackend
from cua_mac.loop import run_computer_loop


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

    run_parser = subparsers.add_parser(
        "run",
        help="Run one local computer-use task against the current macOS desktop.",
    )
    run_parser.add_argument("prompt", help="Task prompt sent to the model.")
    run_parser.add_argument(
        "--max-turns",
        type=int,
        default=None,
        help="Optional maximum loop turns before forcing exit.",
    )
    run_parser.add_argument("--model", default="gpt-5.4", help="Responses API model name.")
    run_parser.add_argument(
        "--action-delay-ms",
        type=float,
        default=120.0,
        help="Delay inserted after local UI actions.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    backend = MacComputerBackend(
        artifact_dir=args.artifact_dir,
        action_delay_seconds=args.action_delay_ms / 1000.0
        if hasattr(args, "action_delay_ms")
        else 0.12,
    )

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

    if args.command == "run":
        backend.ensure_accessibility_access()
        client = OpenAI()
        result = run_computer_loop(
            backend=backend,
            client=client,
            model=args.model,
            prompt=args.prompt,
            max_turns=args.max_turns,
            log=lambda message: print(message, flush=True),
        )
        print()
        print(result.final_message)
        return 0

    parser.error(f"Unhandled command: {args.command}")
    return 2
