"""Start once, scan each inserted page automatically, and press Enter to end."""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import sys

from bmp_output import DEFAULT_OUTPUT_DIR, save_bmp
from cli_common import add_scan_options, report
from scanner_driver import (
    ColorMode,
    ScanMode,
    ScanSettings,
    open_scan_batch,
)


def end_requested() -> bool:
    """Poll console input on the same thread that owns all USB operations."""
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="directory for timestamped BMP files (default: output/)",
    )
    add_scan_options(parser)
    return parser


def interactive_loop(
    output_dir: Path, dpi: int, backend: str, color_mode: ColorMode = ColorMode.COLOR,
    *, overscan: bool = True,
) -> int:
    if not sys.stdin.isatty():
        raise RuntimeError("continuous scanning requires an interactive terminal")
    settings = ScanSettings(
        dpi=dpi, overscan=overscan,
        mode=ScanMode.CONTINUOUS, color_mode=color_mode,
    )
    output_dir = output_dir.expanduser().resolve()
    pages = 0
    with open_scan_batch(backend, settings, reporter=report) as batch:
        print("连续扫描已开始，放入纸张即可自动扫描。")
        print("按回车结束（当前页会读完并保存）；Ctrl-C 中止。", flush=True)
        try:
            while True:
                print("等待放入纸张……", flush=True)
                if not batch.wait_for_paper(end_requested):
                    break
                page = batch.scan_page()
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
                output = output_dir / f"ix110-{stamp}.bmp"
                save_bmp(output, page)
                pages += 1
                print(
                    f"已保存：{output} ({page.width} x {page.height}, "
                    f"{output.stat().st_size} bytes)"
                )
        except (KeyboardInterrupt, EOFError):
            print("\n收到中止请求。")
        print("正在结束扫描批次并释放设备资源……", flush=True)
    print(f"会话结束，共保存 {pages} 页。")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return interactive_loop(
        args.output_dir, args.dpi, args.backend, ColorMode(args.color_mode),
        overscan=args.overscan,
    )


if __name__ == "__main__":
    raise SystemExit(main())
