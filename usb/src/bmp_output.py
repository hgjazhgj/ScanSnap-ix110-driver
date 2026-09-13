"""BMP output helpers independent from scanner communication."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import struct

from scanner_driver import ScannedPage


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"


def default_output(directory: Path | None = None, prefix: str = "ix100") -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
    return (directory or DEFAULT_OUTPUT_DIR) / f"{prefix}-{stamp}.bmp"


def save_bmp(path: Path, page: ScannedPage) -> None:
    bits = page.color_mode.bits_per_pixel
    source_stride = (page.width * bits + 7) // 8
    target_stride = (source_stride + 3) & ~3
    image_size = target_stride * page.height
    ppm = round(page.dpi / 0.0254)
    # Indexed BMP: 0 is black; the largest index is white. Raw 1-bit
    # rows already put the leftmost pixel in the most significant bit.
    colors = (1 << bits) if bits <= 8 else 0
    palette = b"".join(
        bytes((value, value, value, 0))
        for value in (index * 255 // (colors - 1) for index in range(colors))
    )
    pixel_offset = 54 + len(palette)
    file_header = struct.pack(
        "<2sIHHI", b"BM", pixel_offset + image_size, 0, 0, pixel_offset
    )
    info_header = struct.pack(
        "<IiiHHIIiiII",
        40,
        page.width,
        -page.height,
        1,
        bits,
        0,
        image_size,
        ppm,
        ppm,
        colors,
        0,
    )
    padding = b"\0" * (target_stride - source_stride)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        stream.write(file_header)
        stream.write(info_header)
        stream.write(palette)
        for offset in range(0, len(page.pixels), source_stride):
            stream.write(page.pixels[offset : offset + source_stride])
            stream.write(padding)
