"""Shared console reporting and scan options for the command-line entries."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from driver import ColorMode, Config


def report(message: str) -> None:
    print(message, flush=True)


def report_saved(output: Path, width: int, height: int) -> None:
    report(f"Saved: {output} ({width} x {height}, {output.stat().st_size} bytes)")


def end_requested() -> bool:
    """Poll console input on the same thread that owns all device operations."""
    if os.name == "nt":
        import msvcrt

        while msvcrt.kbhit():
            key = msvcrt.getwch()
            if key in ("\r", "\n", "\x1a"):
                return True
            if key in ("\0", "\xe0"):
                msvcrt.getwch()  # Consume the second half of a function key.
    else:
        import select

        if select.select([sys.stdin], [], [], 0)[0]:
            sys.stdin.readline()
            return True
    return False


def add_scan_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dpi",
        type=int,
        help="scan resolution (overrides INI)",
    )
    parser.add_argument(
        "--color-mode",
        choices=("color", "gray", "mono"),
        help="scan in color, grayscale, or black and white (overrides INI)",
    )
    overscan = parser.add_mutually_exclusive_group()
    overscan.add_argument("--overscan", dest="overscan", action="store_true")
    overscan.add_argument("--no-overscan", dest="overscan", action="store_false")
    parser.set_defaults(overscan=None)


def apply_scan_options(config: Config, arguments: argparse.Namespace) -> None:
    if arguments.dpi is not None:
        config.dpi = arguments.dpi
    if arguments.color_mode is not None:
        config.color_mode = ColorMode(arguments.color_mode)
    if arguments.overscan is not None:
        config.overscan = arguments.overscan
