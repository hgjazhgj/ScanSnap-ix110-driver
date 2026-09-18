#!/usr/bin/env python3
"""Start once, scan each inserted page automatically, and press Enter to end."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

from app_common import default_config_path, load_config_file
from bmp_output import save_bmp
from cli_common import (
    add_scan_options,
    apply_scan_options,
    end_requested,
    report,
    report_saved,
)
from driver import Config, DriverError, DriverSession


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=default_config_path(), metavar="FILE")
    parser.add_argument("--output-dir", metavar="DIR")
    add_scan_options(parser)
    return parser


def _output_path(directory: Path, sequence: int) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
    return directory / f"ix100-{stamp}-{sequence:04d}.bmp"


def interactive_loop(output_dir: Path, config: Config) -> int:
    pages = 0
    with DriverSession(config, reporter=report) as driver:
        driver.reserve()
        with driver.batch() as batch:
            report(
                "Continuous scanning started. Insert paper to scan automatically. "
                f"BMP output directory: {output_dir}"
            )
            report(
                "Press Enter to finish after the current page is read and saved; "
                "Ctrl-C to abort."
            )
            while True:
                report("Waiting for paper...")
                if not batch.wait_for_paper(end_requested):
                    break
                page = batch.scan_page()
                output = _output_path(output_dir, pages + 1)
                save_bmp(output, page)
                report_saved(output, page.info.width, page.info.height)
                pages += 1
            report("Ending the scan batch and releasing device resources...")
    report(f"Session ended. Saved {pages} page(s).")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not sys.stdin.isatty():
        raise DriverError("continuous scanning requires an interactive terminal")
    config = load_config_file(args.config)
    apply_scan_options(config, args)
    output_dir = Path(args.output_dir) if args.output_dir else Path(config.output).parent
    if str(output_dir) in ("", "."):
        output_dir = Path("output")
    return interactive_loop(output_dir, config)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)
    except (DriverError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
