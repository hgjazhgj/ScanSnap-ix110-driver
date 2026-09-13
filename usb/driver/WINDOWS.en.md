# Windows driver setup

[简体中文](WINDOWS.md) | [English](WINDOWS.en.md) | [日本語](WINDOWS.ja.md)

This guide applies to USB scanning and the bundled [Wi-Fi setup](../../wifi-setup/README.en.md). Wi-Fi setup configures wireless networking over USB and therefore needs the correct USB driver binding. Pure Wi-Fi scanning does not need these USB drivers.

## Choose a driver

| Current situation | Setup | Program option |
| --- | --- | --- |
| Official ScanSnap USB driver already installed | Keep the binding; exit ScanSnap Home before running | `--backend usbscan` |
| Official software not installed, or a generic USB driver is preferred | Bind the scanner to WinUSB with Zadig as below | `--backend libusb` |
| Already bound to WinUSB | Install Python dependencies and use directly | `--backend libusb` |

`usbscan.sys` and `winusb.sys` are two bindings for the same USB interface. After switching to WinUSB, ScanSnap Home cannot access that interface. Restore the official driver as described below when you need official USB functionality.

The default `--backend auto` tries libusb first, falling back to usbscan only if opening fails on Windows. It neither installs nor switches drivers, and never changes backends during scanning or configuration.

## Identify the device

Connect and turn on the scanner. Find it in Device Manager, open “Properties → Details → Hardware Ids”, and check:

| Model | Hardware ID |
| --- | --- |
| ScanSnap iX110 | `USB\VID_05CA&PID_03C8` |
| ScanSnap iX100 | `USB\VID_04C5&PID_13F4` |

The ID may have an `&REV_...` suffix. The official driver name for iX110 may appear as iX100; identify the device by VID/PID. “Driver → Driver Details” shows whether it currently uses `usbscan.sys` or `winusb.sys`.

## Use an existing official driver

If the official USB driver already works, no binding change is needed. Exit ScanSnap Home and other scanning programs, then install this project's Python dependencies.

To install or repair the official driver, select your model and Windows version through the [official ScanSnap software download page](https://www.pfu.ricoh.com/global/scanners/scansnap/support/software/org56.html) for the device's sales region, and follow the official installer. This release does not include Ricoh/PFU driver files.

Use `--backend usbscan` for scanning. Usbscan ports are discovered dynamically; do not assume a fixed port number. USB scanning and Wi-Fi setup use exclusive access and cannot run simultaneously.

## Configure WinUSB with Zadig

These steps manually install or replace the device's current driver. Finish scanning and setup jobs and exit related programs first.

1. Download and run [Zadig](https://zadig.akeo.ie/), granting administrator permission when Windows asks.
2. Enable `Options → List All Devices` to include devices with official drivers.
3. Select the scanner and verify `USB ID` is `05CA:03C8` or `04C5:13F4`. Do not select a USB hub or another device.
4. Select **WinUSB** as the target driver.
5. Verify the device and target driver, then click `Install Driver` or `Replace Driver`, depending on the current binding.
6. Wait for successful installation, confirm the current driver shows WinUSB, and close Zadig.

These UI steps follow the [official Zadig guide](https://github.com/pbatard/libwdi/wiki/Zadig#basic-usage). Zadig installs the binding for the local device; this project's development INF template is not needed. This release currently provides no signed automatic WinUSB installer.

## Install dependencies and run

Python 3.11 or later is required. Run from `ix100/usb/`:

```powershell
python -m pip install -r requirements.txt
python -B src/scan_direct.py --help
```

`requirements.txt` supplies PyUSB plus `libusb-package` and the libusb DLL for Windows; no manual DLL copying is needed. Installing Python dependencies does not bind the scanner to WinUSB; complete the binding steps separately. `--help` only checks the program entry point, does not access the device, and does not prove that the driver works.

When ready to scan, insert paper and choose the command matching the current binding:

```powershell
# Official usbscan driver
python src/scan_direct.py --backend usbscan

# WinUSB driver
python src/scan_direct.py --backend libusb
```

Both commands access the device and scan one page. See the [USB guide](../README.en.md) for continuous scanning and other options.

Wi-Fi setup has its own dependencies and entry point. Its `usbscan` backend only needs the Python standard library and the installed official driver. For `libusb`, install `requirements.txt` from `ix100/wifi-setup/`. Connection options follow the device subcommand; see [Wi-Fi setup](../../wifi-setup/README.en.md).

## Restore the official driver

Finish this project's scanning or setup job, then locate the scanner by hardware ID in Device Manager.

- If “Properties → Driver → Roll Back Driver” is available and the previous driver was official, use it.
- Otherwise, repair or reinstall using the official installer for the model. If you already have a complete official driver package, specify it under “Update driver → Browse my computer for drivers”.

Follow Windows prompts and reboot only if requested. Confirm that the restored driver is `usbscan.sys`, then use `--backend usbscan`. For manual installation and rollback, see [Microsoft's Device Manager driver instructions](https://support.microsoft.com/en-us/windows/update-drivers-through-device-manager-in-windows-ec62f46c-ff14-c91d-eead-d7126dc1f7b6).

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Scanner missing from Zadig | Check USB connection and power; enable `List All Devices` |
| `libusb-package is required` or libusb DLL cannot load | Install `requirements.txt` using the same Python interpreter that runs the entry point |
| libusb cannot find or open the scanner | Verify hardware ID and WinUSB binding; close programs using the device |
| usbscan cannot find a port | Confirm official `usbscan.sys` binding; use `libusb` if switched to WinUSB |
| Device busy or access denied | End other scanning/setup jobs and exit official software; administrator rights do not override another program's exclusive access |
| Official software cannot scan over USB after installing WinUSB | Restore the official driver as above |

Successful driver installation or help output does not mean every scan mode has been validated on hardware.
