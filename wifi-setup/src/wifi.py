"""iX100-family binary Wi-Fi setup commands, independent of the official DLL.

Original-function references and field tables: ../WIFI_IMPLEMENTATION.md.
All methods require an already owned SetupDevice USB configuration session.
"""

from __future__ import annotations

import struct

from common import (
    SetupError, decode_secret, encode_secret, get_text, operation, put_text,
    put_u32, require_size, u32,
)


PROFILE_SIZE = 0x30C
PROFILES_SIZE = 0xF4C
# Offsets are relative to a profile's SSID, following the 16-byte list header.
PROFILE_TEXT_FIELDS = {
    "ssid": (0, 0x21), "security": (0x21, 7), "encryption": (0x28, 5),
    "eap_type": (0x2D, 5), "phase2": (0x40, 9), "user_id": (0x49, 0x41),
    "anonymous_identity": (0x14B, 0x41), "certificate_name": (0x24D, 0x21),
    "ip": (0x284, 16), "netmask": (0x294, 16), "gateway": (0x2A4, 16),
}
PROFILE_INTEGER_FIELDS = {"ca_check": 0x34, "dhcp": 0x280}
PROFILE_SECRET_FIELDS = {"eap_password": 0x8A, "wifi_key": 0x18C}


class WifiMixin:
    """STA, direct AP, stored profiles, and WPS operations."""

    def _wifi_secret(self, value: str) -> bytes:
        return encode_secret(value, legacy=self.legacy_key, encoding=self.encoding)

    def _read_wifi_secret(self, data: bytes, offset: int) -> str:
        require_size(data, offset + 192)
        return decode_secret(data[offset:offset + 192], legacy=self.legacy_key,
                             encoding=self.encoding)

    @operation("Set router SSID, authentication, encryption and Wi-Fi key", mutates=True)
    def set_wifi(self, ssid: str, security: str, encryption: str, wifi_key: str) -> None:
        """Usb_Wifi_Setting / FUN_10019f30; e.g. security=WPA2, encryption=AES."""
        data = bytearray(0xF8)
        put_text(data, 0, 0x21, ssid, self.encoding)
        put_text(data, 0x24, 7, security)
        put_text(data, 0x2C, 5, encryption)
        data[0x34:0xF4] = self._wifi_secret(wifi_key)
        self.exchange(0x1006, data)

    @operation("Set STA 802.1X / EAP identity, certificate checking and wireless key", mutates=True)
    def set_wifi_8021x(self, ssid: str, security: str, encryption: str,
                      eap_type: str = "", phase2: str = "", user_id: str = "",
                      eap_password: str = "", anonymous_identity: str = "",
                      wifi_key: str = "", ca_check: int = 0) -> None:
        """Usb_Wifi_Setting_8021X / FUN_1001a070, binary non-iX2500 branch."""
        data = bytearray(0x370)
        for offset, size, value in (
            (0, 0x21, ssid), (0x21, 7, security), (0x28, 5, encryption),
            (0x2D, 5, eap_type), (0x62, 9, phase2), (0x6B, 0x41, user_id),
            (0x16D, 0x41, anonymous_identity),
        ):
            put_text(data, offset, size, value, self.encoding)
        put_u32(data, 0x34, ca_check)
        data[0xAC:0x16C] = self._wifi_secret(eap_password)
        data[0x1AE:0x26E] = self._wifi_secret(wifi_key)
        self.exchange(0x100D, data)

    @operation("Set STA DHCP or static IPv4, netmask and gateway", mutates=True)
    def set_ip(self, dhcp: int, ip: str = "", netmask: str = "", gateway: str = "") -> None:
        """Usb_Ip_Setting: 0x8c-byte payload with textual IPv4 fields."""
        data = bytearray(0x8C)
        put_u32(data, 0, dhcp)
        for offset, value in ((4, ip), (20, netmask), (36, gateway)):
            put_text(data, offset, 16, value)
        self.exchange(0x1003, data)

    @operation("Diagnose the configured STA wireless connection", mutates=True)
    def diagnose_wifi(self) -> None:
        """Usb_Wifi_Diagnostic; completion checks the command result."""
        self.exchange(0x1009)

    @operation("Read the startup Wi-Fi mode")
    def get_startup_wifi_mode(self) -> int:
        return u32(self.exchange(0x103, read_size=4, request_size=0))

    @operation("Set the startup Wi-Fi mode (iX100 branch)", mutates=True)
    def set_startup_wifi_mode(self, mode: int) -> None:
        """FUN_100155c0: iX100 command 0x1106; other models use other commands."""
        self.exchange(0x1106, struct.pack("<I", mode))

    @operation("Read the current Wi-Fi mode")
    def get_wifi_mode(self) -> int:
        return u32(self.exchange(0x104, read_size=4, request_size=0))

    @operation("Switch Wi-Fi mode immediately (iX100 branch)", mutates=True)
    def set_wifi_mode(self, mode: int) -> None:
        self.exchange(0x1107, struct.pack("<I", mode))

    @operation("Read direct-connect AP SSID, security, IP and DHCP server settings")
    def get_ap_settings(self) -> dict:
        """Usb_Ap_Setting_Info / FUN_1001e7d0, including device key decoding."""
        data = self.exchange(0x102, read_size=0x2C8, request_size=0x2C8)
        require_size(data, 0x2C8, "AP settings")
        text_fields = {
            "ssid": (0, 0x21), "security": (0x21, 7), "encryption": (0x28, 5),
            "ip": (0x1E0, 16), "netmask": (0x1F0, 16),
            "lease_start": (0x270, 16), "lease_end": (0x280, 16),
        }
        result = {name: get_text(data, offset, size, self.encoding)
                  for name, (offset, size) in text_fields.items()}
        result.update({name: u32(data, offset) for name, offset in {
            "stealth": 0x148, "key_display": 0x140, "channel": 0x144,
            "wps_status": 0xF0, "dhcp_server": 0x268, "lease_time": 0x26C,
        }.items()})
        result["wifi_key"] = self._read_wifi_secret(data, 0x2D)
        return result

    @operation("Read direct-connect AP status, MAC, scanner name and connection settings")
    def get_ap_system_info(self) -> dict:
        """Usb_Ap_System_Info / FUN_1001e090; system tail comes from config file."""
        system = self.get_system_settings()
        data = self.exchange(0x101, read_size=0x3C4, request_size=0x3C4)
        require_size(data, 0x3C4, "AP system information")
        text_fields = {
            "ssid": (0xB8, 0x21), "security": (0xD9, 7), "encryption": (0xE0, 5),
            "mac": (0x294, 18), "ip": (0x2DC, 16), "netmask": (0x2EC, 16),
            "lease_start": (0x36C, 16), "lease_end": (0x37C, 16),
            "host_name": (0, 0x40),
        }
        result = {name: get_text(data, offset, size, self.encoding)
                  for name, (offset, size) in text_fields.items()}
        result.update({name: u32(data, offset) for name, offset in {
            "stealth": 0x200, "channel": 0x2A8, "wps_status": 0x1A8,
            "dhcp_server": 0x364, "lease_time": 0x368,
        }.items()})
        result["wifi_key"] = self._read_wifi_secret(data, 0xE5)
        result.update(system)
        return result

    @operation("Set direct-connect AP SSID, stealth mode, channel and security parameters", mutates=True)
    def set_ap_wifi(self, ssid: str, stealth: int, channel: int, security: str,
                    encryption: str, wifi_key: str, key_display: int = 0) -> None:
        """Usb_Ap_Wifi_Setting / FUN_10015470 / FUN_1001a4f0."""
        data = bytearray(0x1DC)
        put_text(data, 0, 0x21, ssid, self.encoding)
        put_text(data, 0x21, 7, security)
        put_text(data, 0x28, 5, encryption)
        data[0x2D:0xED] = self._wifi_secret(wifi_key)
        for offset, value in ((0x140, key_display), (0x144, channel), (0x148, stealth)):
            put_u32(data, offset, value)
        self.exchange(0x1101, data)

    @operation("Set direct-connect AP IPv4, netmask, DHCP server, lease time and address pool", mutates=True)
    def set_ap_ip(self, ip: str, netmask: str, dhcp_server: int, lease_time: int,
                  lease_start: str, lease_end: str) -> None:
        """Usb_Ap_Ip_Setting: lease_time uses the official raw LeaseIPTerm unit."""
        data = bytearray(0xEC)
        for offset, value in ((4, ip), (20, netmask), (0x94, lease_start), (0xA4, lease_end)):
            put_text(data, offset, 16, value)
        put_u32(data, 0x8C, dhcp_server)
        put_u32(data, 0x90, lease_time)
        self.exchange(0x1102, data)

    def _get_profiles_payload(self) -> bytes:
        data = self.exchange(0xB, read_size=PROFILES_SIZE, request_size=PROFILES_SIZE)
        require_size(data, PROFILES_SIZE, "Wi-Fi profiles")
        # This validates a device-reported count before interpreting records.
        if u32(data) > 5:
            raise SetupError("Wi-Fi profile count exceeds the five-entry response")
        return data

    def _profile_decode(self, record: bytes, index: int) -> dict:
        result = {name: get_text(record, offset, size, self.encoding)
                  for name, (offset, size) in PROFILE_TEXT_FIELDS.items()}
        result.update({name: u32(record, offset)
                       for name, offset in PROFILE_INTEGER_FIELDS.items()})
        result.update({name: decode_secret(record[offset:offset + 192], legacy=False,
                                          encoding=self.encoding)
                       for name, offset in PROFILE_SECRET_FIELDS.items()})
        result["index"] = index
        return result

    @operation("Read all saved Wi-Fi profiles and their IP settings")
    def get_profiles(self) -> list:
        """Usb_Profile_Info / FUN_1001eec0; returned index is zero-based."""
        data = self._get_profiles_payload()
        return [self._profile_decode(data[16 + i * PROFILE_SIZE:16 + (i + 1) * PROFILE_SIZE], i)
                for i in range(u32(data))]

    @operation("Register a Wi-Fi / 802.1X profile at the specified number", mutates=True)
    def register_profile(self, profile_no: int, ssid: str, security: str,
                         encryption: str, eap_type: str = "", phase2: str = "",
                         user_id: str = "", eap_password: str = "",
                         anonymous_identity: str = "", wifi_key: str = "",
                         certificate_name: str = "", ca_check: int = 0) -> None:
        """Usb_Profile_Register / FUN_1001a650: zero-based profile_no; count appends."""
        data = bytearray(0x290)
        put_u32(data, 0, profile_no)
        fields = dict(ssid=ssid, security=security, encryption=encryption,
                      eap_type=eap_type, phase2=phase2, user_id=user_id,
                      anonymous_identity=anonymous_identity, certificate_name=certificate_name)
        for name, value in fields.items():
            offset, size = PROFILE_TEXT_FIELDS[name]
            put_text(data, 16 + offset, size, value, self.encoding)
        put_u32(data, 0x44, ca_check)
        for offset, value in ((0x9A, eap_password), (0x19C, wifi_key)):
            data[offset:offset + 192] = encode_secret(value, legacy=False, encoding=self.encoding)
        self.exchange(0x100F, data)

    def _profile_patch(self, data: bytearray, record_start: int, changes: dict) -> None:
        for name, value in changes.items():
            if name == "index":
                continue
            if name in PROFILE_TEXT_FIELDS:
                offset, size = PROFILE_TEXT_FIELDS[name]
                put_text(data, record_start + offset, size, value, self.encoding)
            elif name in PROFILE_INTEGER_FIELDS:
                put_u32(data, record_start + PROFILE_INTEGER_FIELDS[name], value)
            else:
                offset = record_start + PROFILE_SECRET_FIELDS[name]
                data[offset:offset + 192] = encode_secret(value, legacy=False, encoding=self.encoding)

    @operation("Update existing profiles by zero-based index, preserving unspecified profiles and unknown fields", mutates=True)
    def set_profiles(self, profiles: list) -> None:
        """Each dict supplies index and changed fields; no implicit removal or append."""
        data = bytearray(self._get_profiles_payload())
        count = u32(data)
        for changes in profiles:
            # Indexing the existing records naturally rejects a missing record.
            record_start = list(range(16, 16 + count * PROFILE_SIZE, PROFILE_SIZE))[changes["index"]]
            self._profile_patch(data, record_start, changes)
        self.exchange(0x1012, data)

    @operation("Explicitly replace the profile list: retain/reorder by index and remove omitted profiles from the active list", mutates=True)
    def replace_profiles(self, profiles: list) -> None:
        """Desired full list; index copies an existing record, no index creates a new one.

        Existing record bytes and unknown list-header bytes are preserved. Entries
        beyond the new count remain untouched and are outside the active list.
        """
        original = self._get_profiles_payload()
        records = [original[16 + i * PROFILE_SIZE:16 + (i + 1) * PROFILE_SIZE]
                   for i in range(u32(original))]
        data = bytearray(original)
        put_u32(data, 0, len(profiles))
        for index, changes in enumerate(profiles):
            record = records[changes["index"]] if "index" in changes else bytes(PROFILE_SIZE)
            start = 16 + index * PROFILE_SIZE
            memoryview(data)[start:start + PROFILE_SIZE] = record
            self._profile_patch(data, start, changes)
        self.exchange(0x1012, data)

    @operation("Update DHCP/IP settings of one existing profile, preserving other profiles and keys", mutates=True)
    def set_profile_ip(self, index: int, dhcp: int, ip: str = "",
                       netmask: str = "", gateway: str = "") -> None:
        self.set_profiles([dict(index=index, dhcp=dhcp, ip=ip, netmask=netmask, gateway=gateway)])

    @operation("Apply the saved Wi-Fi profiles", mutates=True)
    def apply_profiles(self) -> None:
        self.exchange(0x1013)

    @operation("Diagnose the Wi-Fi connection for the specified profile number", mutates=True)
    def diagnose_profile(self, profile_no: int) -> None:
        self.exchange(0x1014, struct.pack("<I", profile_no))

    def _wps_start(self, command: int, payload: bytes, wait: bool) -> None:
        self.send_setup(command, payload)
        if wait:
            self.receive_setup(command)

    @operation("Start STA WPS push-button/PIN pairing and wait in the same session by default", mutates=True)
    def start_wps(self, pin: str = "", wait: bool = True) -> None:
        """Empty pin selects push-button mode; USB ownership must persist until done."""
        if pin:
            data = bytearray(8)
            put_text(data, 0, 8, pin)
            self._wps_start(0x1005, data, wait)
        else:
            self._wps_start(0x1004, b"", wait)

    @operation("Receive the started STA WPS result in the current USB session")
    def get_wps_result(self, pin_mode: bool = False, wait: bool = True) -> None:
        self.receive_setup(0x1005 if pin_mode else 0x1004, wait=wait)

    @operation("Cancel WPS pairing and wait for the result in the same session by default", mutates=True)
    def cancel_wps(self, wait: bool = True) -> None:
        # Usb_Wps_Send(mode=2) replaces the pending WPS transaction. It must
        # not wait for pairing to finish before sending its cancellation.
        if self._pending is not None and self._pending[0] in (
                0x1004, 0x1005, 0x1103, 0x1104, 0x1010, 0x1011, 0x101A):
            self._pending = None
        self._wps_start(0x1007, b"", wait)

    @operation("Receive the WPS cancellation result in the current USB session")
    def get_wps_cancel_result(self, wait: bool = True) -> None:
        self.receive_setup(0x1007, wait=wait)

    @operation("Start direct-connect AP WPS push-button/PIN pairing and wait by default", mutates=True)
    def start_ap_wps(self, pin: str = "", wait: bool = True) -> None:
        if pin:
            data = bytearray(8)
            put_text(data, 0, 8, pin)
            self._wps_start(0x1104, data, wait)
        else:
            self._wps_start(0x1103, b"", wait)

    @operation("Receive the direct-connect AP WPS result in the current USB session")
    def get_ap_wps_result(self, pin_mode: bool = False, wait: bool = True) -> None:
        self.receive_setup(0x1104 if pin_mode else 0x1103, wait=wait)

    @operation("Set the direct-connect AP WPS status", mutates=True)
    def set_ap_wps_status(self, status: int) -> None:
        self.exchange(0x1105, struct.pack("<I", status))

    @operation("Start the official AP WPS mode 3 operation and wait by default", mutates=True)
    def start_ap_wps_mode3(self, wait: bool = True) -> None:
        """Usb_Ap_Wps_Send mode 3: command 0x101a + zero dword; keep raw naming."""
        self._wps_start(0x101A, bytes(4), wait)

    @operation("Receive the AP WPS mode 3 result in the current USB session")
    def get_ap_wps_mode3_result(self, wait: bool = True) -> None:
        self.receive_setup(0x101A, wait=wait)

    @operation("Register a profile using WPS push-button/PIN pairing and wait by default", mutates=True)
    def start_profile_wps(self, pin: str = "", wait: bool = True) -> None:
        if pin:
            data = bytearray(8)
            put_text(data, 0, 8, pin)
            self._wps_start(0x1011, data, wait)
        else:
            self._wps_start(0x1010, b"", wait)

    @operation("Receive the profile WPS result in the current USB session")
    def get_profile_wps_result(self, pin_mode: bool = False, wait: bool = True) -> None:
        self.receive_setup(0x1011 if pin_mode else 0x1010, wait=wait)
