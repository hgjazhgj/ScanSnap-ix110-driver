"""Shared console reporting and scan options for the command-line entries."""

import argparse

from scanner_driver import MODEL_WINDOW_HEIGHT_UNITS


def report(message: str) -> None:
    print(message, flush=True)


def add_scan_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="scan resolution (default: 300 DPI)",
    )
    parser.add_argument(
        "--height",
        dest="height_units",
        type=int,
        metavar="UNITS",
        default=MODEL_WINDOW_HEIGHT_UNITS,
        help=(
            "height in 1/1200 inch units, used as supplied; "
            "model reference range: "
            "1..42307; official 300-DPI color values: normal 17204, long 42307 "
            "(default); gray/mono normal: 17202; no input range validation"
        ),
    )
    parser.add_argument(
        "--overscan",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "select width before alignment: 10368 units when on (default), "
            "10200 when off; height is unchanged"
        ),
    )
    parser.add_argument(
        "--color-mode",
        choices=("color", "gray", "mono"),
        default="color",
        help="scan in color, grayscale, or black and white (default: color)",
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "libusb", "usbscan"),
        default="auto",
        help="USB backend (default: libusb, with Windows usbscan open fallback)",
    )
