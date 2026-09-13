# Continuous scanning

[简体中文](INTERACTIVE.md) | [English](INTERACTIVE.en.md) | [日本語](INTERACTIVE.ja.md)

Run from `ix100/wifi/`:

```powershell
python src/scan_interactive.py --output-dir output --config config/ix100.local.ini
```

The program connects to the scanner, starts one continuous job, and automatically waits for paper. Each inserted page is scanned and saved as a BMP, then it waits again. Color, grayscale and monochrome are saved as 24-, 8- and 1-bit files respectively. Paper inserted before startup is also scanned automatically.

Use `--dpi INTEGER`, `--color-mode color|gray|mono` and `--overscan` / `--no-overscan` to override INI settings. Defaults are 300 DPI, color and overscan enabled. The same settings apply throughout the job.

`--output-dir DIR` selects the save directory; if omitted, the parent of INI `[scan] output` is used. The directory is used unchanged, without the time expansion performed by `scan_direct.py`. Each filename includes a timestamp and session sequence number, such as `ix100-20260913-120000-000-0001.bmp`. Output retains all valid pixels for the final dimensions, without inversion or cropping.

Press Enter to request completion: while waiting for paper, cleanup begins immediately; during scanning, the current page is read and saved first, then the job ends and the device is released. Ctrl+C aborts. Scan or save failures also exit and attempt to end the job and release the reservation.

An interactive terminal is required. Keyboard input and scanning are handled serially on the same thread. Enter pressed during scanning is processed after the current page is saved. The job and device reservation are kept between pages, with cleanup on exit.

The current continuous-job implementation has not been validated on hardware. Uncompressed grayscale and monochrome response formats and polarity are also unconfirmed.
