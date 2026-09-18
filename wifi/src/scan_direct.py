#!/usr/bin/env python3
"""Scan one page from a ScanSnap iX100/iX110 over Wi-Fi."""

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
    report,
    report_saved,
)
from driver import DriverError, DriverSession


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output",
        nargs="?",
        help="output BMP path template for strftime (uses local time)",
    )
    parser.add_argument("--config", default=default_config_path(), metavar="FILE")
    add_scan_options(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config_file(args.config)
    apply_scan_options(config, args)
    output = Path(datetime.now().strftime(args.output or config.output))

    with DriverSession(config, reporter=report) as driver:
        driver.reserve()
        page = driver.scan()
        save_bmp(output, page)
        report_saved(output, page.info.width, page.info.height)
        driver.release()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)
    except (DriverError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
