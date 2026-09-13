"""Configuration and image-output helpers shared by the Python front ends."""

from __future__ import annotations

import configparser
import ipaddress
import os
import secrets
import struct
import sys
from pathlib import Path

from driver import Config, DriverError, ScanResult


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


def _portable_path(value: str) -> str:
    # Existing configuration uses backslashes. Interpret those as path
    # separators on POSIX while preserving normal Windows behavior.
    return value.replace("\\", "/") if os.sep == "/" else value


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

    scanner_ip = _get(parser, "scanner", "ip")
    if not scanner_ip:
        scanner_ip = _get(parser, "scanner", "default_ip")
    app_port = _get_int(parser, "scanner", "app_port", 0)
    if app_port == 0:
        app_port = _get_int(parser, "scanner", "notification_port", 53219)
    config = Config(
        path=str(config_path),
        scanner_ip=scanner_ip,
        scanner_name=_get(parser, "scanner", "name", "ScanSnap iX100"),
        scanner_serial=_get(parser, "scanner", "serial"),
        scanner_mac=_get(parser, "scanner", "mac"),
        control_port=_get_int(parser, "scanner", "control_port", 53218),
        app_port=app_port,
        discovery_port=_get_int(parser, "scanner", "discovery_port", 52217),
        manager_id=_get(parser, "host", "manager_id"),
        password_required=_get_int(
            parser, "credential", "password_required", 1
        )
        != 0,
        password=_get(parser, "credential", "password"),
        timeout_seconds=max(
            5, min(300, _get_int(parser, "network", "timeout_seconds", 30))
        ),
        dpi=_get_int(parser, "scan", "dpi", 300),
        max_image_mb=max(
            1, min(1024, _get_int(parser, "scan", "max_image_mb", 100))
        ),
        output=_portable_path(
            _get(parser, "scan", "output", "output/ix100_scan.bmp")
        ),
    )
    if not config.manager_id:
        config.manager_id = _get(parser, "identity", "wifi_manager_id")

    try:
        ipaddress.IPv4Address(config.scanner_ip)
    except ipaddress.AddressValueError as error:
        raise DriverError(
            "[scanner] ip/default_ip is not a valid IPv4 address"
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
        raise DriverError("manager_id must be 16 non-zero hexadecimal characters")
    if config.password_required and (
        not 1 <= len(config.password) <= 16
        or not all(0x21 <= ord(character) <= 0x7E for character in config.password)
    ):
        raise DriverError("password must contain 1-16 printable ASCII characters")
    if config.dpi not in (150, 200, 300, 600):
        raise DriverError("dpi must be 150, 200, 300, or 600")
    return config


def default_config_path() -> str:
    entry_dir = Path(sys.argv[0]).resolve().parent
    runtime_root = Path(__file__).resolve().parents[1]
    candidates = (
        runtime_root / "config" / "ix100.local.ini",
        entry_dir / "config" / "ix100.local.ini",
        entry_dir.parent / "config" / "ix100.local.ini",
        Path("config") / "ix100.local.ini",
    )
    return str(next((candidate for candidate in candidates if candidate.exists()), candidates[0]))


def generate_manager_id() -> str:
    while True:
        value = secrets.token_bytes(8)
        if any(value):
            return value.hex()


def save_scan_image(output: str | os.PathLike[str], result: ScanResult) -> Path:
    """Write uncompressed BGR pixels to a top-down 24-bit BMP atomically."""
    image = result.image
    width, height = result.info.width, result.info.height
    source_stride = width * 3
    if width == 0 or height == 0 or len(image) != source_stride * height:
        raise DriverError("BGR image length does not match its READ80 dimensions")
    if result.info.horizontal_dpi == 0 or result.info.vertical_dpi == 0:
        raise DriverError("READ80 returned zero image resolution")
    target_stride = (source_stride + 3) & ~3
    body_size = target_stride * height
    if width > 0x7FFFFFFF or height > 0x7FFFFFFF or body_size + 54 > 0xFFFFFFFF:
        raise DriverError("image exceeds BMP format limits")
    # Existing local INIs may still specify .jpg; never put BMP bytes under it.
    destination = Path(_portable_path(os.fspath(output))).with_suffix(".bmp")
    temporary = Path(f"{destination}.part")
    file_header = struct.pack("<2sIHHI", b"BM", 54 + body_size, 0, 0, 54)
    info_header = struct.pack(
        "<IiiHHIIiiII", 40, width, -height, 1, 24, 0, body_size,
        (result.info.horizontal_dpi * 10000 + 127) // 254,
        (result.info.vertical_dpi * 10000 + 127) // 254, 0, 0,
    )
    padding = bytes(target_stride - source_stride)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("wb") as stream:
            stream.write(file_header)
            stream.write(info_header)
            for offset in range(0, len(image), source_stride):
                stream.write(image[offset:offset + source_stride])
                stream.write(padding)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except OSError as error:
        raise DriverError(f"cannot save BMP: {error}") from error
    print(f"saved {54 + body_size} bytes to {destination} "
          f"(BMP BGR24, {width}x{height}, valid_height={height})")
    return destination


__all__ = [
    "default_config_path",
    "generate_manager_id",
    "load_config_file",
    "save_scan_image",
]
