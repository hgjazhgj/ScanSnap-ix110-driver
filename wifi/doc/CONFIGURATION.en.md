# Wi-Fi configuration

[简体中文](CONFIGURATION.md) | [English](CONFIGURATION.en.md) | [日本語](CONFIGURATION.ja.md)

Paths and commands below assume `ix100/wifi/` is the working directory. Copy `config/ix100.example.ini` to `config/ix100.local.ini`, then use the fixed section and key names below. Only the scanner IP, Manager ID, and password when password authentication is enabled are required; other entries have defaults.

```powershell
python src/generate_manager_id.py
```

The standalone script randomly generates a Manager ID. Copy it to `[identity] wifi_manager_id` and reuse it. The generator runs offline, prints the ID only to the terminal, and does not modify the configuration file.

| Setting | Meaning |
| --- | --- |
| `[identity] wifi_manager_id` | Required; 8-byte host ID as 16 hexadecimal characters, not all zero; reuse after generation |
| `[scanner] ip` | Required; scanner's current IPv4 address, available from router leases or `discover.py` results |
| `[scanner] control_port` | Optional; default 53218, scan-control TCP port |
| `[scanner] app_port` | Optional; default 53219, reservation, device information and release TCP port |
| `[scanner] discovery_port` | Optional; default 52217, UDP discovery and keepalive port |
| `[credential] password_required` | Optional; default `1`; `1` when a device connection password is required, `0` otherwise |
| `[credential] password` | Required when enabled; plaintext password on the back label, 1–16 printable ASCII characters without spaces |
| `[network] timeout_seconds` | Network/scan timeout; default 30 seconds, range 5–300 seconds |
| `[scan] dpi` | Integer scan resolution; default 300; accepting a value does not imply device support or validation |
| `[scan] color_mode` | `color`, `gray` or `mono`; default `color`; saves 24-, 8- or 1-bit BMP |
| `[scan] overscan` | `1` enables extended edge scanning, `0` disables it; default `1` |
| `[scan] max_image_mb` | Per-page receive-memory limit; default 256 MiB, range 1–1024 MiB |
| `[scan] output` | Default single-page BMP path: `output/ix100_scan.bmp`; supports `strftime` templates; use forward slashes and a `.bmp` filename |

Host IP, outbound interface, host MAC and broadcast address are selected automatically; no configuration entries are needed. The program does not read official application configuration or registry entries.

Both `scan_direct.py` and `scan_interactive.py` accept `--dpi INTEGER`, `--color-mode color|gray|mono` and `--overscan` / `--no-overscan` to override INI settings without rewriting the file. The single-page entry point takes an output path directly, for example `python src/scan_direct.py output/ix100_scan.bmp`.

Discovery reads the same configuration; `python src/discover.py --config config/ix100.local.ini` sends UDP and accesses devices.

The host selects window dimensions in 1/1200 inch: height 17828 at 600 DPI, or 42307 otherwise; width 10368 with overscan enabled, or 10208 disabled. This is the current host policy, not a complete reproduction of official automatic paper-size rules. Higher DPI needs more receive memory; use `max_image_mb` to set the per-page limit.

Without `--config`, the fixed configuration location is `ix100/wifi/config/ix100.local.ini` in the release directory. You may keep real configuration elsewhere and specify `--config FILE`; credentials need not be stored in the distribution directory.

The output positional argument of `scan_direct.py` overrides `[scan] output`. The chosen path, including directories, is expanded with `strftime` using local time before device access. Example:

```ini
[scan]
output=output/%Y%m%d/scan-%H%M%S-%f.bmp
```

`%f` means six-digit microseconds; `%%` is a literal percent sign. Write the time format directly in INI as shown. Relative output paths use the current working directory, and filenames should end in `.bmp`. The interactive entry point takes only the parent directory from this setting, performs no time expansion, and generates per-page filenames itself. This page and `config/ix100.example.ini` define the configuration format.

The current implementation requests single-sided uncompressed images and has no save-time cropping switch. Grayscale and monochrome response formats and polarity have not been confirmed on hardware. The local INI contains a plaintext password and is excluded by ignore rules; distribute and share only the template.
