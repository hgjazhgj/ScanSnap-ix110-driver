"""USB identity and network-information readers ported from the official SCApi.

All offsets below refer to payloads after the 20-byte SETUP NET response header.
Evidence addresses and limitations are recorded in ../INFO_IMPLEMENTATION.md.
"""

from __future__ import annotations

import struct

from common import SetupError, decode_secret, get_text, operation, require_size, u32


def _serial_info(eeprom: bytes) -> dict:
    """Port Usb_Get_SerialNoString and FUN_10005b50, without guessing RF identity."""
    require_size(eeprom, 0x200, "EEPROM")
    count = int.from_bytes(eeprom[0x64:0x67], "big")
    prefix_bytes = eeprom[0x5C:0x5F]
    suffix_byte = eeprom[0x78]
    prefix = "".join(chr(value) if 0x20 <= value <= 0x7E else "$"
                     for value in prefix_bytes)
    suffix = chr(suffix_byte) if 0x20 <= suffix_byte <= 0x7E else "$"
    if not prefix_bytes[0] or not suffix_byte:
        serial = f"{count:06d}"
    else:
        if 1_000_000 <= count < 3_000_000:
            # Official grouping omits I, O, Q, S, X and Z.
            number = "ABCDEFGHJKLMNPRTUVWY"[count // 100_000 - 10]
            number += f"{count % 100_000:05d}"
        else:
            number = f"{count:06d}"
        serial = prefix + suffix + number
    return {"serial_number": serial, "area": eeprom[0x77],
            "serial_counter": count, "prefix": prefix, "suffix_char": suffix}


def _config_value(raw: bytes, label: bytes, default: bytes) -> bytes:
    """Read the first LF-terminated value like FUN_1001bb80 (also accepts CRLF)."""
    position = raw.find(label)
    if position < 0:
        return default
    start = position + len(label)
    end = raw.find(b"\n", start)
    if end < 0:
        return default
    return raw[start:end].rstrip(b"\r")


def _system_settings(raw: bytes, legacy: bool, encoding: str) -> dict:
    """Decode the four official config-file fields without logging credentials."""
    try:
        mode = int(_config_value(raw, b"PwdMode=", b"1"))
        display = int(_config_value(raw, b"PwdDisp=", b"1"))
        port_bytes = _config_value(raw, b"ReadyNotificationPort=", b"")
        port = int(port_bytes) if port_bytes else None
    except ValueError:
        raise SetupError("invalid numeric field in device configuration") from None
    encoded = _config_value(raw, b"PwdCode=", b"")
    # This field's official destination has a 16-byte password capacity.
    if len(encoded) > 48:
        raise SetupError("invalid password field length in device configuration")
    return {"password_required": mode,
            "password": decode_secret(encoded, legacy=legacy, encoding=encoding),
            "password_display": display, "eh_port": port,
            "ready_notification_port": port}


class InfoMixin:
    """Read device identity, STA settings, current state and access-point lists."""

    def _read_configfile(self) -> tuple[int, bytes]:
        """Issue command 1 then command 2 with the official receive allocation."""
        size = self.get_configfile_size()
        if size > 0xFF0:
            raise SetupError("device configuration exceeds the legacy 4080-byte payload")
        raw = self.exchange(2, read_size=0xFF0, request_size=size)
        require_size(raw, size, "configuration file")
        return size, raw[:size]

    def _read_device_info(self, extended: bool) -> dict:
        """Read only the binary record; standalone MAC/SSID reads need no secrets."""
        size = 0x230 if extended else 0x248
        raw = self.exchange(7 if extended else 4, read_size=size, request_size=size)
        require_size(raw, size, "device information")
        if extended:
            text_offsets = {
                "scanner_name": 0, "functional_version": 0x41, "ssid": 0xB8,
                "security": 0xD9, "encryption": 0xE0, "eap": 0xE5,
                "phase2": 0xEA, "mac_address": 0x130, "connection_mode": 0x144,
                "ieee80211_mode": 0x168, "ip_address": 0x1A8,
                "netmask": 0x1B8, "gateway": 0x1C8,
            }
            integer_offsets = {"current_profile_number": 0xF8, "channel": 0x158,
                               "signal_strength": 0x15C, "radio_level": 0x160,
                               "dhcp": 0x1A4}
        else:
            text_offsets = {
                "scanner_name": 0, "functional_version": 0x44, "ssid": 0x4C,
                "security": 0x70, "encryption": 0x78, "mac_address": 0x144,
                "connection_mode": 0x158, "ieee80211_mode": 0x17C,
                "ip_address": 0x1BC, "netmask": 0x1CC, "gateway": 0x1DC,
            }
            integer_offsets = {"channel": 0x16C, "signal_strength": 0x170,
                               "radio_level": 0x174, "dhcp": 0x1B8,
                               "ap_connection_status": 0x244}
        result = {key: get_text(raw, offset, encoding=self.encoding)
                  for key, offset in text_offsets.items()}
        result.update({key: u32(raw, offset) for key, offset in integer_offsets.items()})
        # Official %ld formatting and frontend int32 preserve negative dBm and
        # the current-profile sentinel -1 (PfuSsWifiTool.il:109886,19108).
        for key in ("signal_strength", "current_profile_number"):
            if key in integer_offsets:
                result[key] = struct.unpack_from("<i", raw, integer_offsets[key])[0]
        if extended:
            result["ap_connection_status"] = struct.unpack_from("<H", raw, 0x74)[0]
            result["authentication_status"] = struct.unpack_from("<H", raw, 0x78)[0]
            # The source appends a band label only for newer-model DAT_101ff834.
            # Keep the wire text unchanged and expose the source field separately.
            if self.legacy_key:
                result["frequency_text"] = get_text(raw, 0x14C, encoding=self.encoding)
        else:
            # FUN_1001bf20 always uses the aQwe seed here, irrespective of model flag.
            result["wifi_key"] = decode_secret(raw[0x80:0x144], encoding=self.encoding)
        return result

    def _scan_access_points(self, command: int) -> list:
        """Parse FUN_1001d7a0's count and 60-byte records; no host Wi-Fi API."""
        raw = self.exchange(command, read_size=0x788, request_size=0x788)
        require_size(raw, 8, "access-point list")
        count = u32(raw, 4)
        require_size(raw, 8 + count * 0x3C, "access-point records")
        result = []
        for index in range(count):
            record = raw[8 + index * 0x3C:8 + (index + 1) * 0x3C]
            result.append({"ssid": get_text(record, 0, encoding=self.encoding),
                           "security": get_text(record, 0x24, encoding=self.encoding),
                           "encryption": get_text(record, 0x2C, encoding=self.encoding),
                           "radio_level": u32(record, 0x38),
                           "signal_strength": struct.unpack_from("<i", record, 0x34)[0]})
        return result

    @operation("读取机身 EEPROM 原始 512 字节", mutates=False)
    def get_eeprom(self) -> bytes:
        """Read EEPROM with the exact official 16-byte diagnostic; never write it."""
        raw = self.diagnostic(b"DEBUG,E2T,RED  W", 0x200)
        require_size(raw, 0x200, "EEPROM")
        return raw

    @operation("读取机身序列号及 EEPROM area 字段", mutates=False)
    def get_serial_info(self) -> dict:
        """Return the official body serial and raw area byte, not an RF-chip serial."""
        return _serial_info(self.get_eeprom())

    @operation("读取机身序列号", mutates=False)
    def get_serial_number(self) -> str:
        """Return the EEPROM serial formatted by the official body-serial algorithm."""
        return self.get_serial_info()["serial_number"]

    @operation("读取 EEPROM 的 area 字节（枚举含义未确认）", mutates=False)
    def get_eeprom_area(self) -> int:
        """Return EEPROM +0x77 without inventing region or RF-chip semantics."""
        return self.get_eeprom()[0x77]

    @operation("读取标准 INQUIRY 型号信息", mutates=False)
    def get_model_info(self) -> dict:
        """Read actual INQUIRY identity; SCApi's model getter itself used STI cache."""
        raw = self.scsi(bytes.fromhex("12 00 00 00 60 00"), data_in_size=96)
        require_size(raw, 36, "standard INQUIRY identity")
        return {"vendor": get_text(raw, 8, 8, "ascii").rstrip(),
                "model": get_text(raw, 16, 16, "ascii").rstrip(),
                "revision": get_text(raw, 32, 4, "ascii").rstrip()}

    @operation("读取扫描仪型号名", mutates=False)
    def get_model(self) -> str:
        """Return the actual INQUIRY product name for model-specific operations."""
        return self.get_model_info()["model"]

    @operation("读取设备固件版本及原始版本记录", mutates=False)
    def get_firmware_info(self) -> dict:
        """Use old-model GET FIRMVERSION, not the iX2500-only exported JSON getter."""
        raw = self.diagnostic(b"GET FIRMVERSION ", 0x20)
        require_size(raw, 0x20, "firmware version")
        return {"firmware_version": get_text(raw, 0, 4, "ascii"),
                "functional_subversion": raw[0x1B] - ord("0"),
                "raw_version_record": raw.hex()}

    @operation("读取设备固件版本", mutates=False)
    def get_firmware_version(self) -> str:
        """Return the first four firmware-version characters consumed by SCApi."""
        return self.get_firmware_info()["firmware_version"]

    @operation("读取无线功能版本", mutates=False)
    def get_functional_version(self) -> str:
        """Read command 10's 16-byte functional-version text."""
        raw = self.exchange(10, read_size=0x10, request_size=0x10)
        require_size(raw, 0x10, "functional version")
        return get_text(raw, encoding=self.encoding)

    @operation("读取硬件 Wi-Fi 开关状态", mutates=False)
    def get_wifi_status(self) -> dict:
        """Read C2 byte +0x10 bit 7, distinct from possession's +0x14 check."""
        raw = self.scsi(bytes.fromhex("C2 00 00 00 00 00 00 00 20 00"), data_in_size=0x20)
        require_size(raw, 0x20, "hardware status")
        enabled = bool(raw[0x10] & 0x80)
        return {"wifi_enabled": enabled, "official_status": 0 if enabled else 7}

    @operation("读取设备配置文件长度", mutates=False)
    def get_configfile_size(self) -> int:
        """Read command 1; its request data size is zero, result is a little-endian u32."""
        return u32(self.exchange(1, read_size=4, request_size=0))

    @operation("读取完整网络配置文件及已解码系统字段（包含秘密）", mutates=False)
    def get_configfile(self) -> dict:
        """Read config text and its official system fields; raw text is marked secret."""
        size, raw = self._read_configfile()
        result = _system_settings(raw, self.legacy_key, self.encoding)
        result.update(size=size, secret_configfile=raw.split(b"\0", 1)[0].decode(self.encoding))
        return result

    @operation("读取连接密码设置及 ReadyNotificationPort", mutates=False)
    def get_system_settings(self) -> dict:
        """Read PwdMode/PwdCode/PwdDisp/ReadyNotificationPort with official defaults."""
        _, raw = self._read_configfile()
        return _system_settings(raw, self.legacy_key, self.encoding)

    @operation("读取基础设备网络信息", mutates=False)
    def get_device_info(self, include_system: bool = True) -> dict:
        """Read command 4, optionally prepending the official config-file reads."""
        system = self.get_system_settings() if include_system else {}
        return {**self._read_device_info(False), **system}

    @operation("读取 802.1X 扩展设备网络信息", mutates=False)
    def get_device_info_8021x(self, include_system: bool = True) -> dict:
        """Read command 7 including current profile number, EAP and auth status."""
        system = self.get_system_settings() if include_system else {}
        return {**self._read_device_info(True), **system}

    @operation("读取设备 MAC 地址", mutates=False)
    def get_mac_address(self, extended: bool = True) -> str:
        """Read MAC directly from command 7/4 without retrieving connection passwords."""
        return self._read_device_info(extended)["mac_address"]

    @operation("读取扫描仪网络名称", mutates=False)
    def get_scanner_name(self, extended: bool = True) -> str:
        """Read the user-configurable scanner name, distinct from its model name."""
        return self._read_device_info(extended)["scanner_name"]

    @operation("读取路由器 SSID、认证和加密设置", mutates=False)
    def get_wifi_settings(self, extended: bool = True) -> dict:
        """Read STA Wi-Fi settings; command 7 does not return the wireless key."""
        info = self._read_device_info(extended)
        keys = ("ssid", "security", "encryption", "eap", "phase2", "wifi_key")
        return {key: info[key] for key in keys if key in info}

    @operation("读取 DHCP、IPv4、子网掩码和网关", mutates=False)
    def get_ip_settings(self, extended: bool = True) -> dict:
        """Read STA addressing settings from the official device-info record."""
        info = self._read_device_info(extended)
        return {key: info[key] for key in ("dhcp", "ip_address", "netmask", "gateway")}

    @operation("读取当前无线连接状态", mutates=False)
    def get_connection_status(self, extended: bool = True) -> dict:
        """Read current connection mode, channel, signal and AP connection status."""
        info = self._read_device_info(extended)
        return {key: info[key] for key in ("connection_mode", "channel", "signal_strength",
                                          "radio_level", "ieee80211_mode", "ap_connection_status")}

    @operation("读取当前 Wi-Fi 档案编号", mutates=False)
    def get_profile_number(self) -> int:
        """Read command 7's +0xf8 value that SCApi cached for Usb_Get_ProfileNo."""
        return self._read_device_info(True)["current_profile_number"]

    @operation("由扫描仪搜索周围无线网络", mutates=False)
    def scan_access_points(self) -> list:
        """Request the device's basic AP survey (command 3), without starting a paper scan."""
        return self._scan_access_points(3)

    @operation("由扫描仪搜索包含 802.1X 信息的无线网络", mutates=False)
    def scan_access_points_8021x(self) -> list:
        """Request the extended AP survey (command 6), using the same record decoder."""
        return self._scan_access_points(6)
