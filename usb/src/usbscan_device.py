"""Locate the installed iX100/iX110 usbscan driver and its current port."""

from __future__ import annotations

import winreg


IMAGE_CLASS_KEY = (
    r"SYSTEM\CurrentControlSet\Control\Class"
    r"\{6bdd1fc6-810f-11d0-bec7-08002be2092f}"
)
SCANSNAP_HARDWARE_IDS = {
    r"usb\vid_05ca&pid_03c8": "ScanSnap iX110",
    r"usb\vid_04c5&pid_13f4": "ScanSnap iX100",
}

def _query_value(key: winreg.HKEYType, name: str, default=None):
    try:
        return winreg.QueryValueEx(key, name)[0]
    except FileNotFoundError:
        return default


def find_ix100_driver() -> dict[str, object]:
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, IMAGE_CLASS_KEY) as class_key:
        index = 0
        while True:
            try:
                subkey_name = winreg.EnumKey(class_key, index)
            except OSError:
                break
            index += 1
            if not subkey_name.isdigit():
                continue
            with winreg.OpenKey(class_key, subkey_name) as device_key:
                matching_id = str(
                    _query_value(device_key, "MatchingDeviceId", "")
                ).lower()
                friendly_name = str(
                    _query_value(device_key, "FriendlyName", "")
                )
                physical_model = next(
                    (
                        model
                        for hardware_id, model in SCANSNAP_HARDWARE_IDS.items()
                        if matching_id.startswith(hardware_id)
                    ),
                    None,
                )
                if physical_model is None and not any(
                    model in friendly_name.lower() for model in ("ix100", "ix110")
                ):
                    continue
                result: dict[str, object] = {
                    "registry_instance": subkey_name,
                    "friendly_name": friendly_name,
                    "matching_device_id": matching_id,
                    "service": _query_value(device_key, "NTMPDriver"),
                    "user_mode_driver_clsid": _query_value(device_key, "USDClass"),
                    "port": _query_value(device_key, "CreateFileName"),
                    "driver_inf": _query_value(device_key, "InfPath"),
                    "driver_version": _query_value(device_key, "DriverVersion"),
                    "driver_date": _query_value(device_key, "DriverDate"),
                }
                if physical_model is not None:
                    result["physical_model"] = physical_model
                try:
                    with winreg.OpenKey(device_key, "DeviceData") as data_key:
                        result["twain_source"] = _query_value(data_key, "TwainDS")
                        result["model"] = _query_value(data_key, "Model")
                except FileNotFoundError:
                    pass
                return result
    raise RuntimeError(
        "No installed ScanSnap iX110 (05CA:03C8) or iX100 (04C5:13F4) "
        "usbscan driver was found; the reused iX110 driver may identify it as iX100"
    )


