# Python API

[简体中文](PYTHON_API.md) | [English](PYTHON_API.en.md) | [日本語](PYTHON_API.ja.md)

[User documentation](../README.en.md)

Add `ix100/usb/src/` to `PYTHONPATH`, or start Python in `src/`:

```python
from pathlib import Path

from bmp_output import save_bmp
from scanner_driver import ColorMode, ScanSettings, open_scan_batch

settings = ScanSettings(
    dpi=300, color_mode=ColorMode.GRAY,
    overscan=True,
)
with open_scan_batch("auto", settings, reporter=print) as batch:
    page = batch.scan_page()
save_bmp(Path("output/page.bmp"), page)
```

`save_bmp()` saves to the supplied path without expanding time formatting. To add a timestamp, generate a path with `datetime.now().strftime()` yourself; `scan_direct.py` already does this before accessing the device.

`ScanSettings` defaults to single-page mode, ending the batch after successfully reading one page, with `dpi=300` and `overscan=True`. Its constructor accepts neither width nor height. Width is 10368 with overscan enabled, or 10208 with it disabled; height is 17828 at 600 DPI, or 42307 otherwise. Dimensions use **1/1200 inch**, with the same dimensions in the base and extended fields. Default 300 DPI color with overscan uses 10368×42307 units and a pixel budget of 2592×10577.

Each batch sends page3C and SET WINDOW once during initialization; subsequent pages reuse those settings. For multiple pages, set `mode=ScanMode.CONTINUOUS` (import `ScanMode` from `scanner_driver`). Before each page, call `batch.wait_for_paper(should_stop)` and call `scan_page()` only after it returns `True`. `should_stop` is a callback returning a boolean. Leaving `with` ends the batch and releases transport resources.

`window_width_units` and `window_height_units` give the transmitted dimensions; `maximum_width_pixels` and `maximum_lines` check READ80 upper bounds. The line budget is `ceil(window_height_units * dpi / 1200)`. Both width values are sent directly. Read stride is computed from the actual stream width returned by the device: `ceil(actual_stream_width * bits_per_pixel / 8)`; remaining monochrome bits still occupy one byte. Dimension and complete-image checks remain in place. BMP rows are zero-padded to four-byte boundaries using the actual row length, without changing image width. The current dimension selection is a host policy, not a reproduction of every official paper-size calculation.

`color_mode` accepts `ColorMode.COLOR`, `ColorMode.GRAY` or `ColorMode.MONO`. `ScannedPage` contains `pixels`, `width`, `height` and `color_mode`, but no DPI. `pixels` holds pixel data for the selected mode; dimensions come from the device, and `color_mode` identifies the bit depth. `save_bmp()` writes 0 to both pixels-per-meter fields, leaving physical resolution unspecified. Requested scan DPI is still controlled by `ScanSettings.dpi`.

Transport modules are `src/transport_libusb.py` and `src/transport_usbscan.py`, with shared framing in `src/transport_protocol.py`. `src/usbscan_device.py` provides Windows port discovery.
