"""Configuration and image-output helpers shared by the Python front ends."""

from __future__ import annotations

import configparser
import argparse
import ipaddress
import os
import struct
from pathlib import Path

from driver import ColorMode, Config, DriverError, ScanResult


def _get(
    parser: configparser.ConfigParser,
    section: str,
    key: str,
    fallback: str = "",
) -> str:
    return parser.get(section, key, fallback=fallback).strip()


def _get_int(
    parser: configparser.ConfigParser,
    section: str,
    key: str,
    fallback: int,
) -> int:
    try:
        return parser.getint(section, key, fallback=fallback)
    except ValueError as error:
        raise DriverError(f"[{section}] {key} must be an integer") from error


def load_config_file(path: str | os.PathLike[str]) -> Config:
    config_path = Path(path)
    if not config_path.is_file():
        raise DriverError(f"configuration file does not exist: {config_path}")
    parser = configparser.ConfigParser(interpolation=None)
    try:
        with config_path.open("r", encoding="utf-8-sig") as file:
            parser.read_file(file)
    except (OSError, configparser.Error, UnicodeError) as error:
        raise DriverError(f"cannot read configuration file: {error}") from error

    config = Config(
        path=str(config_path),
        scanner_ip=_get(parser, "scanner", "ip"),
        control_port=_get_int(parser, "scanner", "control_port", 53218),
        app_port=_get_int(parser, "scanner", "app_port", 53219),
        discovery_port=_get_int(parser, "scanner", "discovery_port", 52217),
        manager_id=_get(parser, "identity", "wifi_manager_id"),
        password_required=_get_int(
            parser, "credential", "password_required", 1
        )
        != 0,
        password=_get(parser, "credential", "password"),
        timeout_seconds=max(
            5, min(300, _get_int(parser, "network", "timeout_seconds", 30))
        ),
        dpi=_get_int(parser, "scan", "dpi", 300),
        color_mode=ColorMode(_get(parser, "scan", "color_mode", "color")),
        overscan=parser.getboolean("scan", "overscan", fallback=True),
        max_image_mb=max(
            1, min(1024, _get_int(parser, "scan", "max_image_mb", 256))
        ),
        output=_get(parser, "scan", "output", "output/ix100_scan.bmp"),
    )

    try:
        ipaddress.IPv4Address(config.scanner_ip)
    except ipaddress.AddressValueError as error:
        raise DriverError(
            "[scanner] ip is not a valid IPv4 address"
        ) from error
    if any(port < 1 or port > 65535 for port in (
        config.control_port, config.app_port, config.discovery_port
    )):
        raise DriverError("scanner ports must be between 1 and 65535")
    if (
        len(config.manager_id) != 16
        or not all(character in "0123456789abcdefABCDEF" for character in config.manager_id)
        or set(config.manager_id) == {"0"}
    ):
        raise DriverError("[identity] wifi_manager_id must be 16 hexadecimal characters and not all zero")
    if config.password_required and (
        not 1 <= len(config.password) <= 16
        or not all(0x21 <= ord(character) <= 0x7E for character in config.password)
    ):
        raise DriverError("password must contain 1-16 printable ASCII characters")
    return config


def add_scan_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dpi", type=int, help="scan resolution (overrides INI)")
    parser.add_argument(
        "--color-mode", choices=[mode.value for mode in ColorMode],
        help="device color mode (overrides INI)",
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


def default_config_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "config" / "ix100.local.ini")


def save_scan_image(output: str | os.PathLike[str], result: ScanResult) -> Path:
    """Write uncompressed color, gray or mono pixels to a top-down BMP."""
    image = result.image
    width, height = result.info.width, result.info.height
    bits_per_pixel = result.color_mode.bits_per_pixel
    source_stride = (width * bits_per_pixel + 7) // 8
    if width == 0 or height == 0 or len(image) != source_stride * height:
        raise DriverError("image length does not match its mode and READ80 dimensions")
    if result.info.horizontal_dpi == 0 or result.info.vertical_dpi == 0:
        raise DriverError("READ80 returned zero image resolution")
    target_stride = (source_stride + 3) & ~3
    body_size = target_stride * height
    colors_used = (1 << bits_per_pixel) if bits_per_pixel <= 8 else 0
    palette = b"".join(
        bytes([index * 255 // (colors_used - 1)] * 3 + [0])
        for index in range(colors_used)
    )
    pixel_offset = 54 + len(palette)
    if width > 0x7FFFFFFF or height > 0x7FFFFFFF or body_size + pixel_offset > 0xFFFFFFFF:
        raise DriverError("image exceeds BMP format limits")
    destination = Path(output)
    temporary = Path(f"{destination}.part")
    file_header = struct.pack("<2sIHHI", b"BM", pixel_offset + body_size, 0, 0, pixel_offset)
    info_header = struct.pack(
        "<IiiHHIIiiII", 40, width, -height, 1, bits_per_pixel, 0, body_size,
        (result.info.horizontal_dpi * 10000 + 127) // 254,
        (result.info.vertical_dpi * 10000 + 127) // 254, colors_used, 0,
    )
    padding = bytes(target_stride - source_stride)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("wb") as stream:
            stream.write(file_header)
            stream.write(info_header)
            stream.write(palette)
            for offset in range(0, len(image), source_stride):
                stream.write(image[offset:offset + source_stride])
                stream.write(padding)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except OSError as error:
        raise DriverError(f"cannot save BMP: {error}") from error
    print(f"saved {pixel_offset + body_size} bytes to {destination} "
          f"(BMP {result.color_mode.value} {bits_per_pixel}-bit, "
          f"{width}x{height}, valid_height={height})")
    return destination


__all__ = [
    "add_scan_options",
    "apply_scan_options",
    "default_config_path",
    "load_config_file",
    "save_scan_image",
]
