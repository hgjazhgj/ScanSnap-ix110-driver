# Drivers and device permissions

[简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)

For scanning, see the [user guide](../README.en.md). USB scanning and the bundled Wi-Fi setup share these driver prerequisites.

## Windows

See [Windows driver setup](WINDOWS.en.md) for hardware IDs, using the existing official driver, configuring WinUSB with Zadig, installing Python dependencies, and restoring the official driver.

With the official driver installed, use `--backend usbscan` and exit ScanSnap Home first. Install Python dependencies as described for each component. With WinUSB already bound, use `--backend libusb`.

Supported USB IDs are `05CA:03C8` for iX110 and `04C5:13F4` for iX100. The official iX110 driver name may appear as iX100. Ports are discovered dynamically; no fixed Usbscan number is needed.

This release does not include a signed WinUSB installer. WinUSB and official usbscan are alternative bindings for the same interface; after switching to WinUSB, ScanSnap Home cannot access the device through that USB interface.

## Linux

Install the system libusb runtime, then run from `ix100/usb/`:

```bash
sudo install -m 0644 driver/60-scansnap-ix100.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Reconnect the scanner. If your desktop environment does not support `TAG+=uaccess`, adjust the [permission rules](60-scansnap-ix100.rules) for your local user groups.

## macOS

With Homebrew, run `brew install libusb`, then install the component's Python dependencies.
