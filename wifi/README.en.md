# ScanSnap iX100/iX110 Wi-Fi driver

[简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)

An independent Python driver for Windows/Linux, requiring neither ScanSnap Home nor official DLLs. It discovers, reserves and controls the scanner over Wi-Fi, requesting single-sided uncompressed color, grayscale or monochrome images and saving 24-, 8- or 1-bit BMP files respectively.

Use Python 3.11 or later. Run all commands from this directory, `ix100/wifi/`:

```powershell
python -m pip install -r requirements.txt
Copy-Item config/ix100.example.ini config/ix100.local.ini
python src/generate_manager_id.py
```

Edit `config/ix100.local.ini` and fill in `[scanner] ip` and `[identity] wifi_manager_id`. `[credential] password_required` is enabled by default, requiring `[credential] password` from the connection-password label on the back of the device. Set it to `0` if the device needs no password. Other settings can use defaults. The ID generator runs offline and does not modify the configuration file.

To discover scanners, use the separate entry point. This sends UDP and accesses devices:

```powershell
python src/discover.py --config config/ix100.local.ini
```

Insert paper and scan one page:

```powershell
python src/scan_direct.py output/ix100_scan.bmp
```

Defaults are 300 DPI, color, and overscan enabled. Command-line options override INI settings, for example:

```powershell
python src/scan_direct.py output/ix100_scan.bmp --dpi 300 --color-mode gray --no-overscan
```

`--color-mode` accepts `color|gray|mono`; `--overscan` enables extended edge scanning and `--no-overscan` disables it. Uncompressed grayscale and monochrome response formats and polarity have not been confirmed on hardware. Accepting an option does not mean the mode has been validated.

Scan automatically when paper is inserted; press Enter to end the continuous job:

```powershell
python src/scan_interactive.py --output-dir output
```

| Path | Purpose |
| --- | --- |
| `src/` | Driver, shared configuration and image saving, scan and standalone tool entry points |
| `requirements.txt` | Python dependencies |
| `config/ix100.example.ini` | Distributable configuration template |
| [doc/CONFIGURATION.en.md](doc/CONFIGURATION.en.md) | Fixed INI format, required fields and defaults |
| [doc/RUNNING.en.md](doc/RUNNING.en.md) | Installation, all commands and distribution |
| [doc/INTERACTIVE.en.md](doc/INTERACTIVE.en.md) | Continuous scanning, naming and exit behavior |
| [doc/API.en.md](doc/API.en.md) | Python usage |

Without `--config`, the fixed location is `config/ix100.local.ini` in this directory. Use `--config FILE` for other locations. The `scan_direct.py` output argument takes precedence over INI `[scan] output`; the default is `output/ix100_scan.bmp`. Before device access, the entire output path is expanded with `strftime` using local time. Relative paths use the current working directory. Use forward slashes and a `.bmp` filename, for example:

```powershell
python src/scan_direct.py 'output/%Y%m%d/scan-%H%M%S-%f.bmp'
```

`%f` is six-digit microseconds and `%%` is a literal percent sign. INI `[scan] output` supports the same time templates. The interactive entry point does not expand its directory and generates filenames per page. The program does not invert colors, crop, or perform lossy encoding.

The local `ix100.local.ini` contains a private identifier and plaintext password and is not distributed with the general package. Only the configuration template is included.
