#!/usr/bin/env python3
"""Discover ScanSnap iX100/iX110 devices over Wi-Fi."""

from __future__ import annotations

import argparse
import select
import socket
import sys
import time

from app_common import default_config_path, load_config_file
from cli_common import report
from driver import (
    Config,
    DriverError,
    KEY,
    _hex,
    _put_be16,
    _put_be32,
    route_identity,
)


def _ascii_field(data: bytes) -> str:
    return data.split(b"\x00", 1)[0].decode("ascii", errors="replace").rstrip(" ")


def discover_devices(config: Config) -> int:
    identity = route_identity(config.scanner_ip, config.control_port)
    report(
        f"route local_ip={identity.local_ip} "
        f"local_mac={_hex(identity.mac[:6])} broadcast={identity.broadcast_ip}"
    )
    request_packets = []
    for key, version in ((KEY, 0x0010), (b"ssNR", 0x0100)):
        packet = bytearray(32)
        packet[0:4] = key
        packet[8:12] = socket.inet_aton(identity.local_ip)
        packet[12:20] = identity.mac
        _put_be32(packet, 20, 0xFF)
        _put_be16(packet, 24, version)
        request_packets.append(bytes(packet))

    found = 0
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp.bind((identity.local_ip, 0))
            udp.setblocking(False)
            targets = (
                (identity.broadcast_ip, config.discovery_port),
                (config.scanner_ip, config.discovery_port),
            )
            for _round in range(3):
                for packet in request_packets:
                    for target in targets:
                        udp.sendto(packet, target)
                until = time.monotonic() + 0.7
                while time.monotonic() < until:
                    timeout = min(0.15, max(0.0, until - time.monotonic()))
                    readable, _, _ = select.select([udp], [], [], timeout)
                    if not readable:
                        continue
                    data, source = udp.recvfrom(2048)
                    if len(data) != 144 or data[:4] not in (KEY, b"ssNR"):
                        continue
                    embedded_ip = socket.inet_ntoa(data[16:20])
                    report(
                        f"found source={source[0]} embedded_ip={embedded_ip} "
                        f"serial='{_ascii_field(data[48:80])}' "
                        f"model='{_ascii_field(data[112:136])}'"
                    )
                    found += 1
    except OSError as error:
        raise DriverError(f"discovery failed: {error}") from error
    report(f"discovery replies={found}")
    return 0 if found else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=default_config_path(), metavar="FILE")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return discover_devices(load_config_file(args.config))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)
    except (DriverError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
