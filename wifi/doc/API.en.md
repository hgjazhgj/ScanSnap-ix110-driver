# Python usage

[简体中文](API.md) | [English](API.en.md) | [日本語](API.ja.md)

Use Python 3.11 or later and install dependencies with `python -m pip install -r requirements.txt` from `ix100/wifi/`. Add `src/` to the module search path or start Python in `src/`.

| Module | Responsibility |
| --- | --- |
| `driver.py` | Device sessions, reservation and keepalive, scanning, final dimensions and uncompressed pixel recovery |
| `app_common.py` | INI, scan option overrides, output paths and BMP encoding |
| `scan_direct.py` | CLI entry point to scan one page immediately |
| `scan_interactive.py` | Automatic scanning on paper insertion within one continuous job, saving each page |
| `discover.py` | Load configuration, send UDP and print discovery results |
| `generate_manager_id.py` | Generate a Manager ID offline |

`app_common.load_config_file()` reads local configuration and `generate_manager_id.py` generates a Manager ID; neither accesses devices. `DriverSession` and scanning calls in the following example connect to the device and scan. Configuration and output paths are relative to the current working directory:

```python
from app_common import load_config_file, save_scan_image
from driver import ColorMode, DriverSession

config = load_config_file("config/ix100.local.ini")
config.dpi = 300
config.color_mode = ColorMode.COLOR
config.overscan = True
with DriverSession(config) as driver:
    driver.reserve()
    result = driver.scan()
    save_scan_image("output/ix100_scan.bmp", result)
```

The session context releases the device. `DriverSession.scan()` creates a single-page job and ends it after one page. `driver.batch(continuous=True)` provides a continuous job; its context manager starts and ends the job, `wait_for_paper(should_stop)` waits for paper, and `scan_page()` returns one scanned page. See [INTERACTIVE.en.md](INTERACTIVE.en.md) for full continuous-entry-point usage.

Import ID generation with `from generate_manager_id import generate_manager_id`. Import discovery with `from discover import discover_devices`; `discover_devices(config)` sends UDP and accesses devices.

`Config.color_mode` uses `ColorMode.COLOR`, `ColorMode.GRAY` or `ColorMode.MONO`, defaulting to `COLOR`; `Config.overscan` defaults to `True`. Set options before creating a device session. Omitted optional INI entries use defaults. See [CONFIGURATION.en.md](CONFIGURATION.en.md) for fixed section names, keys and required fields.

`ScanResult.color_mode` records the image mode. `ScanResult.image` stores raw pixels in top-to-bottom row order: 24-bit BGR for color, 8-bit single-channel for grayscale, and packed 1-bit for monochrome. Expected bytes per row are `(width * bits_per_pixel + 7) // 8`; image length must equal row bytes times final height. Uncompressed grayscale and monochrome response formats and polarity have not been confirmed on hardware.

The saver writes 24-, 8- or 1-bit BMP according to the mode, adding the required palette and row padding without inversion or cropping. It saves the supplied path unchanged. Use forward slashes and a `.bmp` filename, such as `output/ix100_scan.bmp`. `save_scan_image()` does not expand time formatting; generate timestamp paths with `datetime.now().strftime()` when needed. `scan_direct.py` already expands its output argument or INI `[scan] output` before device access.

Importing modules does not use the network, but constructing a device session selects a network interface and initializes transport. Protocol analysis and historical validation materials are not runtime dependencies.
