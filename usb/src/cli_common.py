"""Shared console reporting and scan options for the command-line entries."""

import argparse


def report(message: str) -> None:
    print(message, flush=True)


def add_scan_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help=(
            "scan resolution (default: 300 DPI); window height is 17828 units "
            "at 600 DPI and 42307 otherwise (1/1200 inch units)"
        ),
    )
    parser.add_argument(
        "--overscan",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "send width 10368 units when on (default), 10208 when off "
            "(1/1200 inch units); height is unchanged"
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
