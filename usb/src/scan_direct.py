"""Scan one page from a ScanSnap iX100/iX110."""

from __future__ import annotations

import argparse
from pathlib import Path

from bmp_output import default_output, save_bmp
from cli_common import add_scan_options, report
from scanner_driver import (
    ColorMode,
    MODEL_WINDOW_HEIGHT_UNITS,
    ScanMode,
    ScanSettings,
    open_scan_batch,
    stop_scanner,
)


def scan(
    output: Path, dpi: int, backend: str, color_mode: ColorMode = ColorMode.COLOR,
    *, height_units: int = MODEL_WINDOW_HEIGHT_UNITS, overscan: bool = True,
) -> tuple[int, int]:
    """Compatibility wrapper for one-page callers."""
    settings = ScanSettings(
        dpi=dpi, height_units=height_units, overscan=overscan,
        mode=ScanMode.SINGLE, color_mode=color_mode,
    )
    with open_scan_batch(backend, settings, reporter=report) as batch:
        page = batch.scan_page()
    save_bmp(output, page)
    return page.width, page.height


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path)
    add_scan_options(parser)
    parser.add_argument(
        "--stop",
        action="store_true",
        help="end an acquisition left active by an interrupted/older run",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.stop:
        stop_scanner(args.backend, reporter=report)
        return 0
    output = (args.output or default_output()).expanduser().resolve()
    width, height = scan(
        output, args.dpi, args.backend, ColorMode(args.color_mode),
        height_units=args.height_units, overscan=args.overscan,
    )
    print(f"saved: {output} ({width} x {height}, {output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
