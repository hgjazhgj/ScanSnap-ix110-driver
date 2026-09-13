#!/usr/bin/env python3
"""One-shot command-line front end for the iX100 Wi-Fi driver."""

from __future__ import annotations

import argparse
import sys

from app_common import (
    default_config_path,
    generate_manager_id,
    load_config_file,
    save_scan_image,
)
from driver import (
    DriverError,
    DriverSession,
    discover_devices,
)


def _add_config(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default=default_config_path(), metavar="FILE")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone ScanSnap iX100 Wi-Fi driver")
    commands = parser.add_subparsers(dest="command", required=True)
    _add_config(commands.add_parser("check-config", help="validate the INI file"))
    _add_config(commands.add_parser("discover", help="send scanner discovery probes"))
    _add_config(
        commands.add_parser("validate-params", help="send scan parameters without scanning")
    )

    scan = commands.add_parser("scan", help="start one scan immediately")
    scan.add_argument("output", nargs="?", help="output BMP path (suffix normalized to .bmp)")
    _add_config(scan)

    listen = commands.add_parser(
        "listen-once", help="wait for the scanner panel button, then scan once"
    )
    listen.add_argument("output", nargs="?", help="output BMP path (suffix normalized to .bmp)")
    listen.add_argument("--wait", type=int, default=0, metavar="SECONDS")
    _add_config(listen)

    commands.add_parser("generate-manager-id", help="generate a host manager ID")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command == "generate-manager-id":
        print(generate_manager_id())
        return 0

    config = load_config_file(arguments.config)
    if arguments.command == "check-config":
        print(
            f"configuration is valid: scanner={config.scanner_ip} dpi={config.dpi} "
            f"password_chars={len(config.password)}"
        )
        return 0
    if arguments.command == "discover":
        return discover_devices(config)

    with DriverSession(config) as driver:
        driver.reserve()
        if arguments.command == "validate-params":
            driver.validate_scan_parameters()
            driver.release()
            return 0
        if arguments.command == "listen-once":
            if arguments.wait < 0:
                raise DriverError("--wait must not be negative")
            driver.wait_for_panel_trigger(arguments.wait)
        result = driver.scan()
        save_scan_image(arguments.output or config.output, result)
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
