"""Shared value codecs and public-operation metadata; no device access on import."""

from __future__ import annotations

import struct
from typing import Callable


SETUP_SECRET_SEED = b"aQweSrTywuIoppAsFdfGuhjkslZxCcvBAnmqNweRstyuNiopaAsdPfghajKlPzxc"
LEGACY_SECRET_SEED = b"pFusCANsNapFiPfu" * 18


class SetupError(RuntimeError):
    """Device, protocol, or configuration-operation failure."""


def operation(description: str, *, mutates: bool = False) -> Callable:
    """Expose a device method as a CLI subcommand without executing it."""
    def decorate(function: Callable) -> Callable:
        function.operation_description = description
        function.operation_mutates = mutates
        return function
    return decorate


def require_size(data: bytes, size: int, name: str = "device response") -> None:
    """Check device output before interpreting fields, preserving short reads."""
    if len(data) < size:
        raise SetupError(f"{name}: short response ({len(data)}/{size} bytes)")


def u32(data: bytes, offset: int = 0) -> int:
    require_size(data, offset + 4)
    return struct.unpack_from("<I", data, offset)[0]


def put_u32(buffer: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<I", buffer, offset, value)


def get_text(data: bytes, offset: int = 0, size: int | None = None,
             encoding: str = "utf-8") -> str:
    if size is None:
        size = len(data) - offset
    require_size(data, offset + size)
    return data[offset:offset + size].split(b"\0", 1)[0].decode(encoding)


def put_text(buffer: bytearray, offset: int, size: int, value: str,
             encoding: str = "utf-8") -> None:
    raw = value.encode(encoding)
    # A fixed-size view cannot silently grow the packet on an oversized value.
    memoryview(buffer)[offset:offset + size] = raw.ljust(size, b"\0")


def encode_secret(value: str, capacity: int = 192, legacy: bool = False,
                  encoding: str = "utf-8") -> bytes:
    """Official decimal-triplet obfuscation, FUN_10001d40 (not encryption)."""
    seed = LEGACY_SECRET_SEED if legacy else SETUP_SECRET_SEED
    raw = value.encode(encoding)
    encoded = "".join(f"{(v if v < 128 else v - 256) + seed[i] + 11:03d}"
                      for i, v in enumerate(raw)).encode("ascii")
    result = bytearray(capacity)
    memoryview(result)[:len(encoded)] = encoded
    return bytes(result)


def decode_secret(value: bytes, legacy: bool = False, encoding: str = "utf-8") -> str:
    """Decode device output, checking malformed triplets without revealing it."""
    seed = LEGACY_SECRET_SEED if legacy else SETUP_SECRET_SEED
    raw = value.split(b"\0", 1)[0]
    if len(raw) % 3 or len(raw) // 3 > len(seed):
        raise SetupError("malformed encoded secret in device response")
    try:
        decoded = bytes((int(raw[i:i + 3]) - seed[i // 3] - 11) & 255
                        for i in range(0, len(raw), 3))
        return decoded.decode(encoding)
    except (ValueError, UnicodeError) as error:
        raise SetupError("malformed encoded secret in device response") from error
