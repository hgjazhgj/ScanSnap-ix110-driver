# Running and distribution

[简体中文](RUNNING.md) | [English](RUNNING.en.md) | [日本語](RUNNING.ja.md)

Use Python 3.11 or later on Windows/Linux. The only third-party dependency is `psutil`, used to enumerate network interfaces, MAC addresses and broadcast addresses. BMP encoding uses the standard library.

Run from `ix100/wifi/`:

```powershell
python -m pip install -r requirements.txt
```

Install dependencies into the interpreter actually used to run the entry points. See [CONFIGURATION.en.md](CONFIGURATION.en.md) for initial setup.

| Command | Behavior |
| --- | --- |
| `python src/scan_direct.py --help` | View options offline |
| `python src/scan_interactive.py --help` | View continuous-scanning options offline |
| `python src/generate_manager_id.py` | Generate a host ID offline without writing files |
| `python src/discover.py --config config/ix100.local.ini` | Send UDP and print discovery results |
| `python src/scan_direct.py output/ix100_scan.bmp` | Immediately scan one page and save BMP |
| `python src/scan_interactive.py --output-dir output` | Scan on paper insertion; Enter ends the continuous job |

Run device commands only after powering on the scanner, ensuring network reachability and filling in configuration. Successful `discover.py` output proves only UDP reachability; a sleeping device may still fail to establish a TCP session. Wake it before scanning.

Reservation `status=-4 / 0xFFFFFFFC` means another client occupies the scanner. End ScanSnap Home, phone or other application connections before scanning again. At this stage, scan parameters have not been submitted and paper feeding has not started.

Scan and discovery entry points accept `--config FILE`. If omitted, they use the fixed release location `ix100/wifi/config/ix100.local.ini`; other locations must be specified. `scan_direct.py` scans exactly one page. Its output positional argument overrides INI `[scan] output`, defaulting to `output/ix100_scan.bmp`. Before device access, the whole path, including directories, is expanded with `strftime` using local time. Relative paths use the current working directory; use forward slashes and a `.bmp` filename:

```powershell
python src/scan_direct.py 'output/%Y%m%d/scan-%H%M%S-%f.bmp'
```

`%f` is six-digit microseconds and `%%` is a literal percent sign. INI output supports the same templates. Interactive directories do not expand time formatting; see [INTERACTIVE.en.md](INTERACTIVE.en.md) for per-page naming.

`scan_direct.py` and `scan_interactive.py` accept `--dpi INTEGER`, `--color-mode color|gray|mono` and `--overscan` / `--no-overscan`. Specified values override INI; omitted values preserve the configuration, whose defaults are 300 DPI, color and overscan enabled. `discover.py` reads the same configuration but does not accept scan options.

Color, grayscale and monochrome save 24-, 8- and 1-bit BMP respectively. Uncompressed grayscale and monochrome response formats and polarity have not been confirmed on hardware.

A successful scan must obtain final dimensions and complete pixels, save BMP, end the job and release the device. Failures print an error and return a nonzero exit code. Paper movement or successful parameter submission alone does not mean an image was saved. For continuous-scanning exit behavior, see [INTERACTIVE.en.md](INTERACTIVE.en.md).
