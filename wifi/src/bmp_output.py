"""BMP output helpers independent from scanner communication."""

from __future__ import annotations

import os
from pathlib import Path
import struct

from driver import DriverError, ScanResult


def save_bmp(path: Path, page: ScanResult) -> None:
    """Write uncompressed color, gray or mono pixels to a top-down BMP."""
    width, height = page.info.width, page.info.height
    bits_per_pixel = page.color_mode.bits_per_pixel
    source_stride = (width * bits_per_pixel + 7) // 8
    if width == 0 or height == 0 or len(page.image) != source_stride * height:
        raise DriverError("image length does not match its mode and READ80 dimensions")
    if page.info.horizontal_dpi == 0 or page.info.vertical_dpi == 0:
        raise DriverError("READ80 returned zero image resolution")
    target_stride = (source_stride + 3) & ~3
    image_size = target_stride * height
    # Indexed BMP: 0 is black; the largest index is white. Raw 1-bit
    # rows already put the leftmost pixel in the most significant bit.
    colors = (1 << bits_per_pixel) if bits_per_pixel <= 8 else 0
    palette = b"".join(
        bytes((value, value, value, 0))
        for value in (index * 255 // (colors - 1) for index in range(colors))
    )
    pixel_offset = 54 + len(palette)
    if (
        width > 0x7FFFFFFF
        or height > 0x7FFFFFFF
        or image_size + pixel_offset > 0xFFFFFFFF
    ):
        raise DriverError("image exceeds BMP format limits")
    temporary = Path(f"{path}.part")
    file_header = struct.pack(
        "<2sIHHI",
        b"BM",
        pixel_offset + image_size,
        0,
        0,
        pixel_offset,
    )
    info_header = struct.pack(
        "<IiiHHIIiiII",
        40,
        width,
        -height,
        1,
        bits_per_pixel,
        0,
        image_size,
        (page.info.horizontal_dpi * 10000 + 127) // 254,
        (page.info.vertical_dpi * 10000 + 127) // 254,
        colors,
        0,
    )
    padding = b"\0" * (target_stride - source_stride)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("wb") as stream:
            stream.write(file_header)
            stream.write(info_header)
            stream.write(palette)
            for offset in range(0, len(page.image), source_stride):
                stream.write(page.image[offset : offset + source_stride])
                stream.write(padding)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise DriverError(f"cannot save BMP: {error}") from error
