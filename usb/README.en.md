# ScanSnap iX100/iX110 USB scanning

[简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)

An independent Python driver that saves single-sided color, grayscale or monochrome BMP images over USB. Supports single-page scanning and continuous jobs that scan automatically when paper is inserted, without loading official user-mode DLLs.

Run all commands below from `ix100/usb/`. Python 3.11 or later is required.

## Installation

```powershell
python -m pip install -r requirements.txt
```

| Environment | Preparation |
| --- | --- |
| Windows with the official USB driver | Use `--backend usbscan`; exit ScanSnap Home first |
| Windows already bound to WinUSB | Use `--backend libusb` |
| Windows without the official driver | Configure WinUSB with Zadig as described in [Windows driver setup](driver/WINDOWS.en.md) |
| Linux/macOS | Install the system libusb runtime; Linux also needs device permissions |

For Windows installation, switching and restoration, see [Windows driver setup](driver/WINDOWS.en.md). For Linux permissions, see [driver/README.en.md](driver/README.en.md). The default `auto` tries libusb first and falls back to usbscan only if opening fails on Windows. It never switches backends during a scan.

## Scanning

Connect the scanner, insert paper, and scan one page:

```powershell
python src/scan_direct.py
```

Continuous scanning immediately waits for paper and saves each inserted page as a separate BMP:

```powershell
python src/scan_interactive.py
```

Press Enter to finish after the current page has been read and saved. Ctrl-C aborts the current page and ends the job. Do not run two scanning programs simultaneously.

Output defaults to `output/` in this directory; missing directories are created automatically. The default single-page filename is `ix100-%Y%m%d-%H%M%S-%f.bmp`, expanded with `strftime` using local time before device access. You can also specify a destination:

```powershell
python src/scan_direct.py output/page.bmp
python src/scan_direct.py 'output/%Y%m%d/scan-%H%M%S-%f.bmp'
python src/scan_interactive.py --output-dir output
```

`scan_direct.py` expands time formatting across the entire path, including directories. `%f` is six-digit microseconds; `%%` is a literal percent sign. Custom relative paths are relative to the current working directory. The interactive entry point keeps per-page timestamp naming; `--output-dir` does not expand time formatting.

## Options

Both scan entry points share these options:

| Option | Purpose and default |
| --- | --- |
| `--dpi 300` | Scan resolution; default 300 DPI |
| `--color-mode color` | `color`, `gray` or `mono`; default color |
| `--backend auto` | `auto`, `usbscan` or `libusb` |
| `--overscan` / `--no-overscan` | Scan width: 10368 when enabled, 10208 when disabled; enabled by default |

DPI accepts integers; the device response determines whether a value is accepted. Window dimensions are in 1/1200 inch: height is fixed at 17828 for 600 DPI and 42307 for other DPI values, selected by the program. Both width values are sent directly. Scan settings are configured once at batch initialization and reused for subsequent pages in continuous scanning.

Output retains the stream width returned by the device. There is no horizontal cropping, deskewing, rotation, OCR or PDF output; incomplete images cause an error. Rows are padded only when saving BMP, as required by the file format, without changing scan width. Image dimensions use the pixel width and height returned by the device. BMP DPI is unspecified: both pixels-per-meter fields are 0.

To end a leftover job after the program was forcibly terminated:

```powershell
python src/scan_direct.py --stop --backend usbscan
```

This command accesses the device; select the appropriate backend for other drivers. Help does not access the device:

```powershell
python -B src/scan_direct.py --help
python -B src/scan_interactive.py --help
```

See the [main README](../README.en.md) for Wi-Fi scanning and wireless setup.
