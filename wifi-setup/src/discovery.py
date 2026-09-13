"""Find a usbscan port from driver registry metadata, without opening the device."""

from __future__ import annotations

from common import SetupError


IMAGE_CLASS_KEY = r"SYSTEM\CurrentControlSet\Control\Class\{6bdd1fc6-810f-11d0-bec7-08002be2092f}"
HARDWARE_IDS = {r"usb\vid_05ca&pid_03c8": "ScanSnap iX110",
                r"usb\vid_04c5&pid_13f4": "ScanSnap iX100"}


def find_ix100_driver() -> dict:
    # Delayed import makes --help and API imports work on non-Windows systems.
    import winreg
    devices = []
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, IMAGE_CLASS_KEY) as image_key:
        for index in range(winreg.QueryInfoKey(image_key)[0]):
            name = winreg.EnumKey(image_key, index)
            if not name.isdigit():
                continue
            with winreg.OpenKey(image_key, name) as device_key:
                try:
                    hardware_id = winreg.QueryValueEx(device_key, "MatchingDeviceId")[0].lower()
                    port = winreg.QueryValueEx(device_key, "CreateFileName")[0]
                except FileNotFoundError:
                    continue
                model = next((m for prefix, m in HARDWARE_IDS.items()
                              if hardware_id.startswith(prefix)), None)
                if model is not None and str(port).startswith(r"\\.\Usbscan"):
                    devices.append({"port": str(port), "model": model, "hardware_id": hardware_id})
    if len(devices) != 1:
        raise SetupError(f"Found {len(devices)} matching usbscan registrations; specify --usbscan-port.")
    return devices[0]
