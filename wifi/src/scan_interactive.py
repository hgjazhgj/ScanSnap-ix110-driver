#!/usr/bin/env python3
"""Scan inserted pages automatically in one job; press Enter to finish."""

from __future__ import annotations

import argparse
import datetime
import os
import sys
from pathlib import Path

from app_common import (
    add_scan_options,
    apply_scan_options,
    default_config_path,
    load_config_file,
    save_scan_image,
)
from driver import DriverError, DriverSession


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Start one continuous job and scan each inserted page automatically. "
            "Enter finishes after saving the current page; Ctrl-C aborts."
        )
    )
    parser.add_argument("--config", default=default_config_path(), metavar="FILE")
    parser.add_argument("--output-dir", metavar="DIR")
    add_scan_options(parser)
    return parser


def end_requested() -> bool:
    """Poll on the device-owning thread; Enter typed during a page stays queued."""
    if os.name == "nt":
        import msvcrt

        while msvcrt.kbhit():
            key = msvcrt.getwch()
            if key in ("\r", "\n", "\x1a"):
                return True
            if key in ("\0", "\xe0"):
                msvcrt.getwch()
    else:
        import select

        if select.select([sys.stdin], [], [], 0)[0]:
            sys.stdin.readline()
            return True
    return False


def _output_path(directory: Path, sequence: int) -> Path:
    now = datetime.datetime.now()
    stamp = now.strftime("%Y%m%d-%H%M%S-") + f"{now.microsecond // 1000:03d}"
    return directory / f"ix100-{stamp}-{sequence:04d}.bmp"


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if not sys.stdin.isatty():
        raise DriverError("continuous scanning requires an interactive terminal")
    config = load_config_file(arguments.config)
    apply_scan_options(config, arguments)
    output_directory = (
        Path(arguments.output_dir)
        if arguments.output_dir
        else Path(config.output).parent
    )
    if str(output_directory) in ("", "."):
        output_directory = Path("output")

    pages = 0
    with DriverSession(config) as driver:
        driver.reserve()
        with driver.batch() as batch:
            print(f"连续扫描已开始，放入纸张即可自动扫描。BMP 输出目录：{output_directory}")
            print("按回车结束（当前页会读完并保存）；Ctrl-C 中止。", flush=True)
            while True:
                print("等待放入纸张……", flush=True)
                if not batch.wait_for_paper(end_requested):
                    break
                result = batch.scan_page()
                save_scan_image(_output_path(output_directory, pages + 1), result)
                pages += 1
            print("正在结束扫描批次并释放设备资源……", flush=True)
    print(f"会话结束，共保存 {pages} 页。")
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
