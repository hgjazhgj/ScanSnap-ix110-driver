"""USB setup operations reconstructed from the official SCApi implementation.

See ADVANCED_IMPLEMENTATION.md for original addresses and model restrictions.
No command is sent at import time. Packet offsets below are payload relative.
"""

from __future__ import annotations

import base64
import struct
import time

from common import (SetupError, operation, put_text, get_text, u32, put_u32,
                     encode_secret, decode_secret, require_size)


class AdvancedMixin:
    def _advanced_model(self) -> str:
        return self.get_model().strip().removeprefix("ScanSnap ")

    def _require_advanced_model(self, models: tuple, feature: str) -> str:
        model = self._advanced_model()
        if model not in models:
            raise SetupError(f"{feature}: official implementation does not support {model}; "
                             f"supported binary branch: {', '.join(models)}")
        return model

    @operation("Set the scanner name, scan connection password and password display setting", mutates=True)
    def set_system_settings(self, name: str, password: str = "",
                            password_display: int = 0) -> dict:
        """Usb_Mobile_Setting / FUN_1001a3b0; empty password disables PwdMode."""
        data = bytearray(0x88)
        put_text(data, 0, 0x41, name, self.encoding)
        put_u32(data, 0x4C, int(bool(password)))
        if password:
            data[0x50:0x80] = encode_secret(password, 0x30, self.legacy_key, self.encoding)
        put_u32(data, 0x84, password_display)
        self.exchange(0x1002, bytes(data))
        return {"name": name, "password_required": bool(password),
                "password_display": password_display}

    @operation("Read the EH/ReadyNotificationPort notification port")
    def get_eh_port(self) -> dict:
        return {"eh_port": self.get_system_settings()["eh_port"]}

    @operation("Set the EH/ReadyNotificationPort notification port", mutates=True)
    def set_eh_port(self, port: int) -> dict:
        """Usb_EHInfo_Setting; this does not change 53218/53219/52217."""
        data = bytearray(0x204)
        put_u32(data, 0, port)
        self.exchange(0x100A, bytes(data))
        return {"eh_port": port}

    @operation("Read the two sets of registered PC host IDs")
    def get_registered_pcs(self) -> dict:
        """FUN_10014c10: read four bytes; first two hold the big-endian length."""
        length_data = self.diagnostic(b"GET HOSTID LEN  ", 4)
        require_size(length_data, 4, "host ID length")
        length = int.from_bytes(length_data[:2], "big")
        if length == 0 or length > 0x1F8:
            raise SetupError(f"host ID data has invalid device length {length}")
        data = self.diagnostic(b"GET HOSTID DATA ", length)
        require_size(data, 8, "host ID data")
        count = data[0]
        require_size(data, 8 + count * 16, "host ID records")
        records = [{"host_id": data[8 + i * 16:16 + i * 16].hex().upper(),
                    "additional_host_id": data[16 + i * 16:24 + i * 16].hex().upper()}
                   for i in range(count)]
        return {"count": count, "computers": records}

    @operation("Register PC host IDs as hexadecimal strings", mutates=True)
    def register_pc(self, host_id: str, additional_host_id: str = "") -> dict:
        """Usb_WifiConnectPC_Register; each ID is eight bytes on the wire."""
        first = bytes.fromhex(host_id).ljust(8, b"\0")
        second = bytes.fromhex(additional_host_id).ljust(8, b"\0")
        result = self.diagnostic(b"REG HOSTID DATA " + first + second, 2)
        require_size(result, 2, "register host ID")
        if result[0]:
            official_result = result[0] if result[0] in (0x80, 0xFF) else 0x5B
            raise SetupError(f"register host ID: device status 0x{result[0]:02X}, "
                             f"official result 0x{official_result:02X}")
        return {"registered": True}

    @operation("Initialize PC registration data (CLR HOSTID ADATA)", mutates=True)
    def initialize_registered_pcs(self) -> dict:
        """Official API is initialization; the exact slot scope is not inferred."""
        result = self.diagnostic(b"CLR HOSTID ADATA", 2)
        require_size(result, 2, "initialize host IDs")
        if result[0]:
            official_result = result[0] if result[0] in (0x80, 0xFF) else 0x5B
            raise SetupError(f"initialize host IDs: device status 0x{result[0]:02X}, "
                             f"official result 0x{official_result:02X}")
        return {"initialized": True}

    @operation("Write official Possession_Setting (SET OCCUPA RIGHT)", mutates=True)
    def set_possession_setting(self, value: int) -> dict:
        """Usb_Possession_Setting: nonzero selects 0x80; second byte remains zero."""
        payload = bytes((0x80 if value else 0, 0))
        result = self.diagnostic(b"SET OCCUPA RIGHT" + payload, 2)
        require_size(result, 2, "SET OCCUPA RIGHT")
        if result[0]:
            official_result = 0x80 if result[0] == 0x80 else 0x5B
            raise SetupError(f"SET OCCUPA RIGHT: device status 0x{result[0]:02X}, "
                             f"official result 0x{official_result:02X}")
        return {"possession_setting": value, "official_result": 0}

    @operation("Write the raw integer argument for official Reset_invalidation", mutates=True)
    def reset_invalidation(self, value: int) -> dict:
        """Usb_Reset_invalidation; do not infer erase-profile or factory-reset semantics."""
        self.exchange(0x1015, struct.pack("<I", value))
        return {"reset_invalidation": value, "completed": True}

    @operation("Upload a certificate file to device temporary storage", mutates=True)
    def upload_certificate(self, data: bytes, file_id: str = "CertificateFile") -> dict:
        """FUN_10011150: 4000-byte chunks in fixed 0xFF0-byte payloads."""
        for offset in range(0, len(data), 4000):
            chunk = data[offset:offset + 4000]
            payload = bytearray(0xFF0)
            put_text(payload, 0, 0x21, file_id, self.encoding)
            put_u32(payload, 0x24, len(data))
            put_u32(payload, 0x28, offset)
            put_u32(payload, 0x2C, len(chunk))
            payload[0x50:0x50 + len(chunk)] = chunk
            self.exchange(0x100B, bytes(payload))
        return {"file_id": file_id, "bytes_uploaded": len(data)}

    @operation("Register an uploaded certificate and its import password", mutates=True)
    def register_certificate(self, kind: int, filename: str,
                             password: str = "") -> dict:
        """Usb_CertificateFile_Register / FUN_1001a290."""
        payload = bytearray(0x128)
        struct.pack_into("<H", payload, 0, kind)
        put_text(payload, 8, 0x21, filename, self.encoding)
        if password:
            payload[0x29:0xE9] = encode_secret(password, 0xC0, self.legacy_key, self.encoding)
        self.exchange(0x100C, bytes(payload))
        return {"kind": kind, "filename": filename, "registered": True}

    @operation("Read the certificate list")
    def list_certificates(self, kind: int) -> dict:
        """Usb_Certificate_List; 16-byte prefix, up to ten 0x158-byte records."""
        payload = bytearray(0x10)
        struct.pack_into("<H", payload, 0, kind)
        data = self.exchange(9, bytes(payload), read_size=0xD80)
        count = u32(data)
        if count > 10:
            raise SetupError(f"certificate list: device count {count} exceeds response capacity")
        require_size(data, 0x10 + count * 0x158, "certificate list")
        entries = []
        for i in range(count):
            base = 0x10 + i * 0x158
            entries.append({
                "filename": get_text(data, base, 0x21, self.encoding),
                "issuer": get_text(data, base + 0x21, 0x81, self.encoding),
                "valid_until": get_text(data, base + 0xA2, 0x14, self.encoding),
                "subject": get_text(data, base + 0xB6, 0x81, self.encoding),
            })
        return {"kind": kind, "count": count, "certificates": entries}

    @operation("Read certificate details")
    def get_certificate_info(self, kind: int, get_info: int,
                             filename: str = "") -> dict:
        """Usb_Certification_Info / FUN_1001dae0. get_info is the official selector."""
        payload = bytearray(0x6A)
        struct.pack_into("<H", payload, 0, kind)
        struct.pack_into("<H", payload, 4, get_info)
        put_text(payload, 8, 0x21, filename, self.encoding)
        data = self.exchange(8, bytes(payload), read_size=0x8EE)
        require_size(data, 0x8EE, "certificate details")
        result = {"version": int.from_bytes(data[:2], "little")}
        for field, offset, size in (
                ("serial_number", 8, 0x3C), ("signature_algorithm", 0x44, 0x21),
                ("issuer", 0x65, 0x401), ("valid_from", 0x466, 0x14),
                ("valid_until", 0x47A, 0x14), ("subject", 0x48E, 0x401),
                ("public_key_description", 0x88F, 0x5F)):
            result[field] = get_text(data, offset, size, self.encoding)
        return result

    @operation("Delete the specified certificate", mutates=True)
    def delete_certificate(self, kind: int, filename: str = "") -> dict:
        payload = bytearray(0x66)
        struct.pack_into("<H", payload, 0, kind)
        put_text(payload, 4, 0x21, filename, self.encoding)
        self.exchange(0x100E, bytes(payload))
        return {"kind": kind, "filename": filename, "deleted": True}

    @operation("Read DNS settings (official binary branch for iX1300/iX1500/iX1600 only)")
    def get_dns(self) -> dict:
        self._require_advanced_model(("iX1300", "iX1500", "iX1600"), "DNS")
        data = self.exchange(0x10F, read_size=0x24, request_size=0x24)
        return {"mode": u32(data), "primary": get_text(data, 4, 16, self.encoding),
                "secondary": get_text(data, 20, 16, self.encoding)}

    @operation("Set DNS settings (official binary branch for iX1300/iX1500/iX1600 only)", mutates=True)
    def set_dns(self, mode: int, primary: str = "", secondary: str = "") -> dict:
        self._require_advanced_model(("iX1300", "iX1500", "iX1600"), "DNS")
        payload = bytearray(0x24)
        put_u32(payload, 0, mode)
        put_text(payload, 4, 16, primary, self.encoding)
        put_text(payload, 20, 16, secondary, self.encoding)
        self.exchange(0x110F, bytes(payload))
        return {"mode": mode, "primary": primary, "secondary": secondary}

    @operation("Read proxy settings (official binary branch for iX1300/iX1500/iX1600 only)")
    def get_proxy(self) -> dict:
        self._require_advanced_model(("iX1300", "iX1500", "iX1600"), "proxy")
        data = self.exchange(0x0D, read_size=0x514, request_size=0x514)
        require_size(data, 0x514, "proxy settings")
        enabled = u32(data) == 1
        auth = enabled and u32(data, 0x108) == 1
        return {"enabled": enabled,
                "address": get_text(data, 4, 0x100, self.encoding) if enabled else "",
                "port": u32(data, 0x104) if enabled else 8080,
                "authentication": auth,
                "username": get_text(data, 0x10C, 0x101, self.encoding) if auth else "",
                "password": decode_secret(data[0x210:0x510], True, self.encoding) if auth else ""}

    @operation("Set proxy settings (official binary branch for iX1300/iX1500/iX1600 only)", mutates=True)
    def set_proxy(self, enabled: bool, address: str = "", port: int = 8080,
                  authentication: bool = False, username: str = "",
                  password: str = "") -> dict:
        self._require_advanced_model(("iX1300", "iX1500", "iX1600"), "proxy")
        payload = bytearray(0x514)
        put_u32(payload, 0, int(enabled))
        put_u32(payload, 0x104, port if enabled else 8080)
        if enabled:
            put_text(payload, 4, 0x100, address, self.encoding)
            put_u32(payload, 0x108, int(authentication))
            if authentication:
                put_text(payload, 0x10C, 0x101, username, self.encoding)
                if password:
                    payload[0x210:0x510] = encode_secret(password, 0x300, True, self.encoding)
        self.exchange(0x101C, bytes(payload))
        return {"enabled": enabled, "configured": True}

    @operation("Read the connection frequency-band enumeration (officially iX1300 only)")
    def get_connect_frequency(self) -> dict:
        self._require_advanced_model(("iX1300",), "connection frequency")
        return {"frequency": u32(self.exchange(0x110, read_size=4, request_size=0))}

    @operation("Set the connection frequency-band enumeration (officially iX1300 only)", mutates=True)
    def set_connect_frequency(self, frequency: int) -> dict:
        self._require_advanced_model(("iX1300",), "connection frequency")
        self.exchange(0x1110, struct.pack("<I", frequency))
        return {"frequency": frequency}

    @operation("Read the roaming enumeration (officially iX1300 only)")
    def get_roaming(self) -> dict:
        self._require_advanced_model(("iX1300",), "roaming")
        return {"roaming": u32(self.exchange(0x111, read_size=4, request_size=0))}

    @operation("Set the roaming enumeration (officially iX1300 only)", mutates=True)
    def set_roaming(self, roaming: int) -> dict:
        self._require_advanced_model(("iX1300",), "roaming")
        self.exchange(0x1111, struct.pack("<I", roaming))
        return {"roaming": roaming}

    @operation("Read the communication protocol enumeration, not a port number")
    def get_protocol(self) -> dict:
        return {"protocol": u32(self.exchange(0x113, read_size=16, request_size=16))}

    @operation("Set the communication protocol enumeration (official values 0/1, not port numbers)", mutates=True)
    def set_protocol(self, protocol: int) -> dict:
        payload = bytearray(16)
        payload[0] = protocol
        self.exchange(0x1117, bytes(payload))
        return {"protocol": protocol}

    @operation("Read device authentication requirements and official status codes")
    def get_device_auth_requirement(self) -> dict:
        """Usb_Is_Red_Device / 100142E0; bit, firmware gate and result remain distinct."""
        data = self.scsi(bytes.fromhex("12 01 F0 00 83 00"), data_in_size=0x83)
        require_size(data, 0x83, "authentication capability INQUIRY")
        if not data[0x82] & 0x80:
            return {"capability_bit": False, "official_state": 0}
        model = self._advanced_model()
        if model == "iX2500":
            raise SetupError("iX2500 authentication requires the separate JSON firmware branch")
        firmware = self.diagnostic(b"GET FIRMVERSION ", 80)
        require_size(firmware, 80, "firmware version")
        minimum = {"iX100": b"BE00", "iX110": b"BE00", "iX1300": b"0L00"}.get(model)
        state = 1 if minimum is not None and firmware[:4] < minimum else 2
        return {"capability_bit": True, "official_state": state,
                "firmware_gate": firmware[:4].decode("ascii")}

    @operation("Read the device authentication key (query branch of Usb_Operate_Auth_Device for older models)")
    def get_device_auth(self) -> dict:
        """Return the opaque 64-byte key; official frontend stores it as Base64.

        PfuSsWifiTool.il:130349-130367 allocates byte[64], never UTF-8 text.
        Availability of bytes does not mean this device requires authentication.
        """
        data = self.exchange(0x112, read_size=0x40, request_size=0)
        require_size(data, 0x40, "device authentication")
        key = data[:0x40]
        return {"authentication_key": key, "authentication_key_size": len(key),
                "authentication_key_base64": base64.b64encode(key).decode("ascii")}

    @operation("Read maintenance mode")
    def get_maintenance_mode(self) -> dict:
        return {"mode": u32(self.exchange(0xF002, read_size=4, request_size=0))}

    @operation("Set maintenance mode (official token erasure enters with 1 and exits with 0)", mutates=True)
    def set_maintenance_mode(self, mode: int) -> dict:
        self.exchange(0xF001, struct.pack("<I", mode))
        return {"mode": mode}

    @operation("Execute a device command through the official maintenance interface", mutates=True)
    def execute_device_command(self, command: str) -> dict:
        data = self.exchange(0xF003, command.encode(self.encoding), read_size=0xFF0)
        require_size(data, 4, "device command response")
        return {"exit_status": u32(data),
                "secret_output": get_text(data, 4, len(data) - 4, self.encoding)}

    @operation("Read a device file through the official paginated interface")
    def get_device_file(self, path: str) -> dict:
        """FUN_10013c10; response +12 is the next cursor and +16 is data size."""
        cursor = 0
        parts = []
        deadline = time.monotonic() + self.timeout
        for _ in range(3000):
            part = self.exchange(5, path.encode(self.encoding), read_size=0xFF0, offset=cursor)
            header = self.last_response_header
            size = u32(header, 16)
            require_size(part, size, "device file chunk")
            if size > 0xFF0:
                raise SetupError("device file chunk exceeds requested capacity")
            parts.append(part[:size])
            if size < 0xFF0:
                return {"path": path, "data": b"".join(parts)}
            cursor = u32(header, 12)
            if time.monotonic() >= deadline:
                raise SetupError("device file transfer timed out before final chunk")
        raise SetupError("device file transfer exceeded the official 3000-chunk budget")

    @operation("Erase the device access token by entering maintenance mode and issuing the official command", mutates=True)
    def erase_access_token(self) -> dict:
        self.set_maintenance_mode(1)
        try:
            result = self.execute_device_command("/usr/local/scanner/bin/cldcmu/erase_token")
            if result["exit_status"]:
                raise SetupError(f"erase token command returned {result['exit_status']}")
            return {"erased": True}
        finally:
            self.set_maintenance_mode(0)

    @operation("Reset wireless settings and reproduce the official iX110 name/SSID restoration branch", mutates=True)
    def reset_wifi_settings(self) -> dict:
        """FUN_10012e00: reset, then iX100-family serial-based iX110 handling."""
        model = self._advanced_model()
        if model == "iX2500":
            raise SetupError("iX2500 reset requires its separate official setup implementation")
        self.exchange(0x1113 if model == "iX1300" else 0x1008)
        result = {"reset": True, "ix110_name_restored": False}
        if model not in ("iX100", "iX110"):
            return result
        serial = self.get_serial_number()
        # Official comparison uses the first three serial characters against D2A.
        if serial[:3] < "D2A":
            return result
        ap = self.get_ap_settings()
        system = self.get_ap_system_info()
        name = "iX110-" + serial
        self.set_system_settings(name, system["password"], system["password_display"])
        self.set_ap_wifi(name, ap["stealth"], ap["channel"], ap["security"],
                         ap["encryption"], ap["wifi_key"], ap["key_display"])
        result.update({"ix110_name_restored": True, "name": name, "ssid": name})
        return result
