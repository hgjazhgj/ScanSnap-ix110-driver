"""Cross-platform ScanSnap iX100 Wi-Fi protocol driver.

This module contains only scanner/network protocol code.  It deliberately does
not parse command-line arguments, read configuration files, or encode images so
that both command-line front ends can share the same hardware implementation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import ipaddress
import socket
import struct
import threading
import time


PROTOCOL_VERSION = 0x0010
MAX_TCP_FRAME = 2 * 1024 * 1024
READ_BLOCK_SIZE = 0x40000
KEY = b"VENS"
Reporter = Callable[[str], None]


class DriverError(RuntimeError):
    """An iX100 network/protocol operation failed."""


class ColorMode(str, Enum):
    COLOR = "color"
    GRAY = "gray"
    MONO = "mono"

    @property
    def bits_per_pixel(self) -> int:
        return {"color": 24, "gray": 8, "mono": 1}[self.value]

    @property
    def composition(self) -> int:
        return {"color": 5, "gray": 2, "mono": 0}[self.value]

    @property
    def data_format(self) -> int:
        return 0x40 if self is ColorMode.MONO else 0x10


@dataclass
class Config:
    path: str = ""
    scanner_ip: str = ""
    control_port: int = 53218
    app_port: int = 53219
    discovery_port: int = 52217
    manager_id: str = ""
    password_required: bool = True
    password: str = ""
    timeout_seconds: int = 30
    dpi: int = 300
    color_mode: ColorMode = ColorMode.COLOR
    overscan: bool = True
    max_image_mb: int = 256
    output: str = "output/ix100_scan.bmp"


@dataclass(frozen=True)
class ImageInfo:
    width: int = 0
    height: int = 0
    horizontal_dpi: int = 0
    vertical_dpi: int = 0


@dataclass(frozen=True)
class ScanResult:
    """Uncompressed top-down pixels with mandatory READ80 dimensions and mode."""

    image: bytes
    info: ImageInfo
    color_mode: ColorMode = ColorMode.COLOR


@dataclass(frozen=True)
class HardwareStatus:
    paper_present: bool
    top_sensor: bool
    cover_open: bool
    temperature_stop: bool
    raw: bytes


@dataclass(frozen=True)
class NetworkIdentity:
    local_ip: str
    mac: bytes
    broadcast_ip: str


@dataclass(frozen=True)
class _ScannerReply:
    status: int
    scanner_status: int
    data: bytes
    frame: bytes


@dataclass(frozen=True)
class _ScanParameters:
    preread: bytes
    parameters: bytes


def _put_be16(frame: bytearray, offset: int, value: int) -> None:
    if offset + 2 > len(frame):
        raise DriverError("internal frame overflow")
    struct.pack_into(">H", frame, offset, value & 0xFFFF)


def _put_be32(frame: bytearray, offset: int, value: int) -> None:
    if offset + 4 > len(frame):
        raise DriverError("internal frame overflow")
    struct.pack_into(">I", frame, offset, value & 0xFFFFFFFF)


def _get_be16(frame: bytes | bytearray, offset: int) -> int:
    if offset + 2 > len(frame):
        raise DriverError("short protocol frame")
    return struct.unpack_from(">H", frame, offset)[0]


def _get_be32(frame: bytes | bytearray, offset: int) -> int:
    if offset + 4 > len(frame):
        raise DriverError("short protocol frame")
    return struct.unpack_from(">I", frame, offset)[0]


def _hex(data: bytes) -> str:
    return data.hex(" ")


def _validate_key(frame: bytes | bytearray, offset: int = 4) -> None:
    if len(frame) < offset + 4 or frame[offset : offset + 4] not in (KEY, b"ssNR"):
        raise DriverError("protocol frame has an invalid key")


def _parse_mac(text: str) -> bytes:
    compact = text.replace(":", "").replace("-", "").replace(".", "").strip()
    if len(compact) < 12:
        raise DriverError("selected network adapter has no six-byte MAC address")
    try:
        value = bytes.fromhex(compact[:12])
    except ValueError as error:
        raise DriverError("selected network adapter has an invalid MAC address") from error
    if len(value) != 6:
        raise DriverError("selected network adapter has no six-byte MAC address")
    return value + b"\x00\x00"


def route_identity(scanner_ip: str, port: int) -> NetworkIdentity:
    """Resolve the IPv4 interface used to reach the scanner.

    psutil supplies the one portable API needed here: enumerating interface
    addresses and their MAC addresses on both Windows and Linux.
    """

    try:
        scanner_address = str(ipaddress.IPv4Address(scanner_ip))
    except ipaddress.AddressValueError as error:
        raise DriverError(f"invalid IPv4 address: {scanner_ip}") from error

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
            route.connect((scanner_address, port))
            local_ip = route.getsockname()[0]
    except OSError as error:
        raise DriverError(f"cannot determine route to scanner: {error}") from error

    try:
        import psutil  # type: ignore[import-not-found]
    except ImportError as error:
        raise DriverError(
            "missing dependency 'psutil'; install requirements.txt first"
        ) from error

    link_family = getattr(psutil, "AF_LINK", getattr(socket, "AF_PACKET", None))
    for records in psutil.net_if_addrs().values():
        ipv4_record = next(
            (
                record
                for record in records
                if record.family == socket.AF_INET and record.address == local_ip
            ),
            None,
        )
        if ipv4_record is None:
            continue
        link_record = next(
            (record for record in records if record.family == link_family), None
        )
        if link_record is None:
            raise DriverError("selected network adapter has no MAC address")
        mac = _parse_mac(link_record.address)
        if ipv4_record.broadcast:
            broadcast = ipv4_record.broadcast
        elif ipv4_record.netmask:
            network = ipaddress.IPv4Network(
                f"{local_ip}/{ipv4_record.netmask}", strict=False
            )
            broadcast = str(network.broadcast_address)
        else:
            raise DriverError("selected network adapter has no IPv4 netmask")
        return NetworkIdentity(local_ip, mac, broadcast)
    raise DriverError("cannot match the scanner route to a network adapter")


def _receive_exact(sock: socket.socket, size: int) -> bytes:
    result = bytearray()
    while len(result) < size:
        try:
            chunk = sock.recv(size - len(result))
        except OSError as error:
            raise DriverError(f"receive failed: {error}") from error
        if not chunk:
            raise DriverError("peer closed the connection")
        result.extend(chunk)
    return bytes(result)


def _receive_frame(sock: socket.socket) -> bytes:
    prefix = _receive_exact(sock, 4)
    total = _get_be32(prefix, 0)
    if total < 8 or total > MAX_TCP_FRAME:
        raise DriverError(f"invalid TCP frame length {total}")
    frame = prefix + _receive_exact(sock, total - 4)
    _validate_key(frame)
    return frame


class _TcpChannel:
    def __init__(self, ip: str, port: int, timeout: int) -> None:
        self._ip = ip
        self._port = port
        self._timeout = timeout
        self._socket: socket.socket | None = None

    def _ensure_connected(self) -> socket.socket:
        if self._socket is not None:
            return self._socket
        try:
            candidate = socket.create_connection(
                (self._ip, self._port), timeout=self._timeout
            )
        except OSError as error:
            raise DriverError(
                f"TCP connect to {self._ip}:{self._port} failed: {error}"
            ) from error
        try:
            candidate.settimeout(self._timeout)
            greeting = _receive_frame(candidate)
            if len(greeting) != 16:
                raise DriverError("scanner greeting is not 16 bytes")
            status = _get_be32(greeting, 8)
            if status != 0:
                raise DriverError(
                    f"scanner rejected TCP connection, status={status}"
                )
        except BaseException:
            candidate.close()
            raise
        self._socket = candidate
        return candidate

    def exchange(self, request: bytes | bytearray) -> bytes:
        try:
            sock = self._ensure_connected()
            try:
                sock.sendall(request)
            except OSError as error:
                raise DriverError(f"send failed: {error}") from error
            return _receive_frame(sock)
        except BaseException:
            self.close()
            raise

    def exchange_split(self, request: bytes | bytearray, split_offset: int) -> bytes:
        if split_offset <= 0 or split_offset >= len(request):
            raise DriverError("invalid split send offset")
        try:
            sock = self._ensure_connected()
            try:
                sock.sendall(request[:split_offset])
                sock.sendall(request[split_offset:])
            except OSError as error:
                raise DriverError(f"send failed: {error}") from error
            return _receive_frame(sock)
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close()
            finally:
                self._socket = None


def _fill_common(frame: bytearray, mac: bytes) -> None:
    if len(mac) != 8 or len(frame) < 24:
        raise DriverError("invalid internal common frame")
    _put_be32(frame, 0, len(frame))
    frame[4:8] = KEY
    frame[16:24] = mac


def _password_wire_value(password: str) -> bytearray:
    mask = "pFusCANsNapFiPfu"
    if len(password) > len(mask):
        raise DriverError("password is longer than the 16-character protocol field")
    encoded = bytearray(48)
    for index, character in enumerate(password):
        value = ord(character) + ord(mask[index]) + 11
        encoded[index * 3] = 48 + value // 100
        encoded[index * 3 + 1] = 48 + value // 10 % 10
        encoded[index * 3 + 2] = 48 + value % 10
    return encoded


def _clock_fields() -> tuple[int, int, int]:
    now = datetime.now().astimezone()
    date = (now.year << 16) | (now.month << 8) | now.day
    clock = (now.hour << 24) | (now.minute << 16) | (now.second << 8)
    offset = now.utcoffset()
    # The protocol follows Windows TIME_ZONE_INFORMATION Bias: seconds west
    # of UTC, hence the inverse of datetime's UTC offset.
    timezone_seconds = -int(offset.total_seconds()) if offset is not None else 0
    return date, clock, timezone_seconds


def _build_reserve(
    config: Config,
    identity: NetworkIdentity,
    trigger_port: int,
    clock: tuple[int, int, int],
) -> bytearray:
    request = bytearray(0x80)
    _fill_common(request, identity.mac)
    _put_be32(request, 8, 0x11)
    _put_be16(request, 0x20, PROTOCOL_VERSION)
    request[0x22] = 30
    _put_be32(request, 0x24, 0)
    _put_be32(request, 0x28, 1 if config.password_required else 0)
    request[0x2C:0x30] = socket.inet_aton(identity.local_ip)
    _put_be32(request, 0x30, trigger_port)
    date, time_value, timezone_seconds = clock
    _put_be32(request, 0x64, date)
    _put_be32(request, 0x68, time_value)
    try:
        manager = bytearray.fromhex(config.manager_id)
    except ValueError as error:
        raise DriverError("manager_id is not hexadecimal") from error
    try:
        if len(manager) != 8:
            raise DriverError("manager_id must contain exactly 16 hexadecimal digits")
        request[0x6C:0x74] = manager
    finally:
        manager[:] = bytes(len(manager))
    _put_be32(request, 0x74, timezone_seconds)
    if config.password_required:
        encoded = _password_wire_value(config.password)
        try:
            request[0x34:0x64] = encoded
        finally:
            encoded[:] = bytes(len(encoded))
    return request


def _build_app_request(command: int, mac: bytes) -> bytes:
    request = bytearray(0x20)
    _fill_common(request, mac)
    _put_be32(request, 8, command)
    if command == 0x12:
        _put_be32(request, 0x18, 1)
    return bytes(request)


def _build_scanner_request(
    total: int,
    cdb_length: int,
    data_in: int,
    data_out: int,
    opcode: int,
    mac: bytes,
) -> bytearray:
    if total < 64:
        raise DriverError("internal scanner request is too short")
    request = bytearray(total)
    _fill_common(request, mac)
    _put_be32(request, 8, 1)
    _put_be32(request, 0x20, cdb_length)
    _put_be32(request, 0x24, data_in)
    _put_be32(request, 0x28, data_out)
    request[0x30] = opcode
    return request


def _parse_scanner_reply(frame: bytes, data_offset: int = 40) -> _ScannerReply:
    if len(frame) < 40:
        raise DriverError("scanner response is shorter than 40 bytes")
    return _ScannerReply(
        status=_get_be32(frame, 8),
        scanner_status=_get_be32(frame, 12),
        data=frame[data_offset:] if len(frame) > data_offset else b"",
        frame=frame,
    )


def _require_app_success(frame: bytes, expected_size: int, operation: str) -> None:
    if len(frame) != expected_size:
        raise DriverError(
            f"{operation} response length is {len(frame)}, expected {expected_size}"
        )
    status = _get_be32(frame, 8)
    if status != 0:
        # Android reverse/SSDevCtl.java:1186,1223-1227 maps RESERVE -4 to
        # errOccupied (Used by other), before any scan parameters are sent.
        if operation == "RESERVE" and status == 0xFFFFFFFC:
            raise DriverError(
                "RESERVE failed: scanner is in use by another client "
                "(status=-4 / 0xFFFFFFFC); disconnect that client and try again"
            )
        raise DriverError(f"{operation} failed, status={status}")


def _require_scanner_success(
    reply: _ScannerReply, operation: str, expected_data: int
) -> None:
    if reply.status != 0 or reply.scanner_status != 0:
        raise DriverError(
            f"{operation} failed, status={reply.status} "
            f"scanner_status={reply.scanner_status}"
        )
    if len(reply.data) != expected_data:
        raise DriverError(
            f"{operation} returned {len(reply.data)} data bytes, "
            f"expected {expected_data}"
        )


def _append_read_payload(
    reply: _ScannerReply,
    sequence: int,
    block: int,
    image: bytearray,
    maximum_image_size: int,
) -> int:
    if len(reply.frame) < 42:
        raise DriverError("short READ response")
    if reply.frame[40] != sequence or reply.frame[41] != block:
        raise DriverError("READ response sequence/block mismatch")
    if len(image) + len(reply.data) > maximum_image_size:
        raise DriverError("image exceeds configured max_image_mb")
    image.extend(reply.data)
    return len(reply.data)


def _parse_image_info(data: bytes) -> ImageInfo:
    if len(data) < 22:
        raise DriverError("READ(0x80) image metadata is too short")
    info = ImageInfo(
        width=_get_be32(data, 8),
        height=_get_be32(data, 12),
        horizontal_dpi=_get_be16(data, 18),
        vertical_dpi=_get_be16(data, 20),
    )
    if info.width == 0 or info.height == 0:
        raise DriverError("READ(0x80) returned zero image dimensions")
    return info


def _build_scan_parameters(
    dpi: int,
    *,
    color_mode: ColorMode = ColorMode.COLOR,
    overscan: bool = True,
    continuous: bool = False,
) -> _ScanParameters:
    # Host width selection: Android reverse/SSDevCtl.java:7511,7609 provides
    # ordinary full-width paper 10208 and automatic paper 10368. Choosing these
    # by overscan does not reproduce an official automatic-paper combination.
    width_1200 = 10368 if overscan else 10208
    # Windows reverse/sshctlnet/selected-extra.c:29-34,87-89,124-125;
    # selected-memory.txt:2, addresses 101b2474 (17828) and 101b2414 (42307).
    height_1200 = 17828 if dpi == 600 else 42307

    preread = bytearray(32)
    _put_be16(preread, 0, dpi)
    _put_be16(preread, 2, dpi)
    _put_be32(preread, 4, width_1200)
    _put_be32(preread, 8, height_1200)
    preread[12] = color_mode.composition

    params = bytearray(80)
    params[0:4] = b"\x00\x01\x01\x01"
    # Android reverse/SSDevCtl.java:4531-4532,4750-4752.
    params[2] = int(overscan)
    params[6:13] = b"\x80\x80\x80\xd0\x80\x80\x80"
    # Windows SshCtlNet scan_12190.c:153-158: continuous AsynchronusRead.
    params[6] = 0xC1 if continuous else 0x80
    # Windows reverse/sshctlnet/scan_12190.c:177,254-257: the 600-DPI branch
    # requires capability == 0. iX100 model 1 has capability 1 at 101b2574
    # (selected-memory-2.txt:1), so this byte remains zero at every DPI.
    params[13] = 0
    params[15] = 1
    params[31] = 0x30
    tail = 32
    params[tail] = 0
    # Android reverse/SSDevCtl.java:7483-7485,7670-7677 defines format/composition.
    params[tail + 1] = color_mode.data_format
    _put_be16(params, tail + 2, dpi)
    _put_be16(params, tail + 4, dpi)
    params[tail + 6] = color_mode.composition
    # Compression 0/argument 0: color raw trial on 2026-09-13; gray/mono raw
    # combinations still require their own device verification.
    params[tail + 7] = 0
    params[tail + 8] = 0
    _put_be32(params, tail + 10, width_1200)
    _put_be32(params, tail + 14, height_1200)
    # Android reverse/SSDevCtl.java:7523-7528,7536-7538: mono double resolution;
    # threshold, automatic binary mode and default density stay zero.
    params[tail + 25] = int(color_mode is ColorMode.MONO)
    return _ScanParameters(bytes(preread), bytes(params))


def decode_raw_image(
    stream: bytes, info: ImageInfo, color_mode: ColorMode = ColorMode.COLOR
) -> bytes:
    """Accept complete pixels or remove the observed APP0/COM insertion.

    Evidence: ../../../ix-100-wifi-dev/WIFI_VALIDATION_UNCOMPRESSED_20260913.md.
    The observed color stream inserts metadata at byte 2 with compression off.
    Pixels retain their device order and polarity; mono rows occupy whole bytes.
    """
    expected = ((info.width * color_mode.bits_per_pixel + 7) // 8) * info.height
    if info.width == 0 or info.height == 0:
        raise DriverError("uncompressed image has zero dimensions")
    if len(stream) == expected:
        return stream
    position = 2
    for marker in (b"\xff\xe0", b"\xff\xfe"):
        if len(stream) < position + 4 or stream[position:position + 2] != marker:
            raise DriverError("uncompressed stream is missing the expected APP0/COM metadata")
        length = _get_be16(stream, position + 2)
        end = position + 2 + length
        if length < 2 or end > len(stream):
            raise DriverError("uncompressed stream has incomplete metadata")
        content = stream[position + 4:end]
        if marker == b"\xff\xe0":
            if length != 16 or content[:5] != b"JFIF\0":
                raise DriverError("uncompressed stream has an unsupported APP0 segment")
        elif content not in (b"PFU ScanSnap #iX100", b"PFU ScanSnap #iX110"):
            raise DriverError("uncompressed stream has an unsupported scanner comment")
        position = end
    actual = len(stream) - (position - 2)
    if actual != expected:
        raise DriverError(
            f"uncompressed image length mismatch: {actual} bytes, expected {expected} "
            f"for {info.width}x{info.height} {color_mode.value} "
            f"{color_mode.bits_per_pixel}-bit"
        )
    return stream[:2] + stream[position:]


class _Ix100Driver:
    def __init__(
        self,
        config: Config,
        identity: NetworkIdentity,
        reporter: Reporter | None = None,
    ) -> None:
        self._config = config
        self._identity = identity
        self.report = print if reporter is None else reporter
        self._control = _TcpChannel(
            config.scanner_ip, config.control_port, config.timeout_seconds
        )
        self._app = _TcpChannel(
            config.scanner_ip, config.app_port, config.timeout_seconds
        )
        self._trigger_socket: socket.socket | None = None
        self._trigger_port = 0
        self._keepalive_stop = threading.Event()
        self._keepalive_thread: threading.Thread | None = None
        self._reserved = False
        self._sequence_state = 1
        self._batch: ScanBatch | None = None

    def reserve(self) -> None:
        if self._reserved:
            return
        self._bind_trigger_socket()
        request = _build_reserve(
            self._config, self._identity, self._trigger_port, _clock_fields()
        )
        try:
            response = self._app.exchange(request)
        finally:
            request[:] = bytes(len(request))
        _require_app_success(response, 20, "RESERVE")
        self._reserved = True
        try:
            self._start_keepalive()
            self._inquiry()
            self._device_information()
        except BaseException as error:
            try:
                self.release()
            except BaseException as cleanup:
                self.report(f"RELEASE failed after initialization error: {cleanup}")
                error.add_note(f"RELEASE failed: {cleanup}")
            raise
        self.report(f"reserved scanner; trigger UDP port={self._trigger_port}")

    def release(self) -> None:
        errors: list[BaseException] = []
        if self._batch is not None:
            try:
                self._batch.close()
            except BaseException as error:
                errors.append(error)
        try:
            self._stop_keepalive()
        except BaseException as error:
            errors.append(error)
        if self._reserved:
            try:
                response = self._app.exchange(
                    _build_app_request(0x12, self._identity.mac)
                )
                _require_app_success(response, 16, "RELEASE")
                self.report("RELEASE succeeded")
            except BaseException as error:
                errors.append(error)
        self._reserved = False
        if self._trigger_socket is not None:
            self._trigger_socket.close()
            self._trigger_socket = None
        self._control.close()
        self._app.close()
        if errors:
            for error in errors[1:]:
                self.report(f"session cleanup also failed: {error}")
                errors[0].add_note(f"session cleanup also failed: {error}")
            raise errors[0]

    def scan(self) -> ScanResult:
        with ScanBatch(self, continuous=False) as batch:
            return batch.scan_page()

    def hardware_status(self) -> HardwareStatus:
        if not self._reserved:
            raise DriverError("scanner is not reserved")
        # GET HARDWARE STATUS: pfussnetif/initialize.c:233-239.
        # CDB: C2 00 00 00 00 00 00 00 20 00.
        request = _build_scanner_request(64, 10, 32, 0, 0xC2, self._identity.mac)
        request[0x38] = 32
        reply = self._exchange_scanner(request)
        if reply.status == 0 and reply.scanner_status == 2:
            raise DriverError(f"GET HARDWARE STATUS check condition; sense={_hex(self._request_sense())}")
        _require_scanner_success(reply, "GET HARDWARE STATUS", 32)
        data = reply.data
        # Windows scan_page.c:217-234; Android SSDevCtl.java:5426-5449,5512-5517.
        return HardwareStatus(
            paper_present=not bool(data[3] & 0x80),
            top_sensor=bool(data[2] & 0x80),
            cover_open=bool(data[3] & 0x20),
            temperature_stop=bool(data[17] & 0x20),
            raw=data,
        )

    def _exchange_scanner(self, request: bytes | bytearray) -> _ScannerReply:
        return _parse_scanner_reply(self._control.exchange(request))

    def _inquiry(self) -> None:
        request = _build_scanner_request(64, 6, 0x60, 0, 0x12, self._identity.mac)
        request[0x31] = 0
        request[0x32] = 0
        request[0x34] = 0x60
        reply = self._exchange_scanner(request)
        _require_scanner_success(reply, "INQUIRY", 0x60)
        vendor = reply.data[8:16].decode("ascii", errors="replace")
        product = reply.data[16:32].decode("ascii", errors="replace")
        self.report(f"inquiry vendor='{vendor}' product='{product}'")

    def _device_information(self) -> None:
        response = self._app.exchange(_build_app_request(0x13, self._identity.mac))
        _require_app_success(response, 0x70, "DEVICE INFORMATION")

    def _set_scan_parameters(self, *, continuous: bool = False) -> None:
        params = _build_scan_parameters(
            self._config.dpi,
            color_mode=self._config.color_mode,
            overscan=self._config.overscan,
            continuous=continuous,
        )
        self.report(
            f"scan settings dpi={self._config.dpi} "
            f"color_mode={self._config.color_mode.value} "
            f"overscan={self._config.overscan} "
            f"width_1200={_get_be32(params.preread, 4)} "
            f"height_1200={_get_be32(params.preread, 8)}"
        )
        preread = _build_scanner_request(96, 10, 0, 32, 0xE9, self._identity.mac)
        _put_be32(preread, 0x34, 32)
        preread[64:96] = params.preread
        reply = self._exchange_scanner(preread)
        _require_scanner_success(reply, "SET PRE-READ", 0)

        set_params = _build_scanner_request(144, 6, 0, 80, 0xD4, self._identity.mac)
        set_params[0x34] = 80
        set_params[64:144] = params.parameters
        reply = _parse_scanner_reply(self._control.exchange_split(set_params, 96))
        if reply.status == 0 and reply.scanner_status == 2:
            try:
                sense_text = _hex(self._request_sense())
            except Exception as error:
                sense_text = f"failed: {error}"
            raise DriverError(f"SET PARAMS check condition; sense={sense_text}")
        _require_scanner_success(reply, "SET PARAMS", 0)

    def _start_job(self) -> None:
        request = _build_scanner_request(72, 6, 8, 8, 0xD5, self._identity.mac)
        request[0x33] = 0
        request[0x34] = 8
        request[0x35] = 8
        _require_scanner_success(self._exchange_scanner(request), "START JOB", 8)

    def _start_paper(self) -> None:
        request = _build_scanner_request(64, 6, 0, 0, 0xE0, self._identity.mac)
        _require_scanner_success(self._exchange_scanner(request), "START PAPER", 0)

    def _end_job(self) -> None:
        request = _build_scanner_request(64, 6, 0, 0, 0xD6, self._identity.mac)
        _require_scanner_success(self._exchange_scanner(request), "END JOB", 0)

    def _cancel_read(self) -> None:
        request = _build_scanner_request(64, 6, 0, 0, 0xD8, self._identity.mac)
        _require_scanner_success(self._exchange_scanner(request), "CANCEL READ", 0)

    def _request_sense(self) -> bytes:
        request = _build_scanner_request(64, 6, 0x12, 0, 0x03, self._identity.mac)
        request[0x34] = 0x12
        reply = self._exchange_scanner(request)
        _require_scanner_success(reply, "REQUEST SENSE", 0x12)
        return reply.data

    def _get_image_info(self) -> bytes:
        request = _build_scanner_request(64, 12, 0x20, 0, 0x28, self._identity.mac)
        request[0x32] = 0x80
        request[0x33] = 0
        request[0x35] = 0
        request[0x38] = 0x20
        reply = self._exchange_scanner(request)
        _require_scanner_success(reply, "READ(0x80)", 0x20)
        return reply.data

    def _read_page(self) -> bytes:
        self._sequence_state ^= 1
        sequence = self._sequence_state
        image = bytearray()
        maximum = self._config.max_image_mb * 1024 * 1024
        deadline = time.monotonic() + 180
        block = 0
        empty_blocks = 0
        while time.monotonic() < deadline:
            busy_attempts = 0
            while True:
                request = _build_scanner_request(
                    64, 12, READ_BLOCK_SIZE, 0, 0x28, self._identity.mac
                )
                request[0x32] = 0
                request[0x33] = 2
                request[0x35] = 0
                request[0x36] = 4
                request[0x37] = 0
                request[0x38] = 0
                request[0x3A] = sequence
                request[0x3B] = block
                reply = _parse_scanner_reply(self._control.exchange(request), 42)
                if reply.status != 0:
                    raise DriverError(f"READ transport status={reply.status}")
                if reply.scanner_status == 8:
                    busy_attempts += 1
                    if (busy_attempts > self._config.timeout_seconds * 10
                            or time.monotonic() >= deadline):
                        raise DriverError("READ remained busy until timeout")
                    time.sleep(0.1)
                    continue
                if reply.scanner_status not in (0, 2):
                    raise DriverError(
                        f"READ scanner_status={reply.scanner_status}"
                    )
                if reply.scanner_status == 2 and len(reply.frame) == 40:
                    appended = 0
                else:
                    appended = _append_read_payload(reply, sequence, block, image, maximum)
                final = " (final)" if reply.scanner_status == 2 else ""
                self.report(
                    f"read block={block} bytes={appended} "
                    f"total={len(image)}{final}"
                )
                if reply.scanner_status == 2:
                    sense = self._request_sense()
                    self.report(f"page end sense={_hex(sense)}")
                    if ((sense[0] & 0x7F) in (0x70, 0x7F)
                            and (sense[2] & 15) == 0 and sense[12:14] == b"\0\0"
                            and (sense[2] & 0x60) and image):
                        return bytes(image)
                    raise DriverError(
                        "READ check condition is not a clean EOM/ILI; " + _hex(sense)
                    )
                empty_blocks = empty_blocks + 1 if appended == 0 else 0
                if empty_blocks >= 3:
                    raise DriverError("READ repeatedly returned no image data")
                block = (block + 1) & 255
                break
        raise DriverError("READ exceeded the 180-second image time budget")

    def _bind_trigger_socket(self) -> None:
        # Common reservation callback port, also used by direct scanning:
        # ../../../ix-100-wifi-dev/reverse/sshctlnet/create_device.c:170-188
        # and reverse/pfussnetif/reserve.c:147-167,249-250 (RESERVE offset 0x30).
        # No panel-event consumer is attached to this socket.
        try:
            trigger = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            trigger.bind((self._identity.local_ip, 0))
            self._trigger_port = trigger.getsockname()[1]
        except OSError as error:
            try:
                trigger.close()
            except UnboundLocalError:
                pass
            raise DriverError(f"trigger bind failed: {error}") from error
        self._trigger_socket = trigger

    def _start_keepalive(self) -> None:
        self._keepalive_stop.clear()
        thread = threading.Thread(
            target=self._keepalive_loop, name="ix100-keepalive", daemon=True
        )
        thread.start()
        self._keepalive_thread = thread

    def _stop_keepalive(self) -> None:
        self._keepalive_stop.set()
        if self._keepalive_thread is not None:
            self._keepalive_thread.join()
            self._keepalive_thread = None

    def _keepalive_loop(self) -> None:
        packet = bytearray(32)
        packet[0:4] = KEY
        _put_be32(packet, 4, 1)
        packet[8:12] = socket.inet_aton(self._identity.local_ip)
        packet[12:20] = self._identity.mac
        _put_be32(packet, 20, 0xFF)
        _put_be16(packet, 24, PROTOCOL_VERSION)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
                udp.bind((self._identity.local_ip, 0))
                while not self._keepalive_stop.wait(5.0):
                    try:
                        udp.sendto(
                            packet,
                            (self._config.scanner_ip, self._config.discovery_port),
                        )
                    except OSError:
                        pass
        except OSError:
            pass


class ScanBatch:
    """One E9/D4/D5 job; each page uses E0/READ/READ80, with one final D6.

    All control-channel operations, including paper polling and cleanup, run
    serially on the caller's thread. Enter can finish after the current page.
    """

    def __init__(self, driver: _Ix100Driver, *, continuous: bool) -> None:
        self._driver = driver
        self.report = driver.report
        self.continuous = continuous
        self.page_number = 0
        self._started = False
        self._job_attempted = False
        self._needs_cancel = False
        self._closed = False

    def open(self) -> ScanBatch:
        if self._closed:
            raise DriverError("batch is closed")
        if self._started:
            return self
        driver = self._driver
        if not driver._reserved:
            raise DriverError("scanner is not reserved")
        if driver._batch is not None:
            raise DriverError("scanner already has an active batch")
        driver._batch = self
        try:
            driver._set_scan_parameters(continuous=self.continuous)
            # D5 may reach the scanner even when its response is lost.
            self._job_attempted = True
            self._needs_cancel = True
            driver._start_job()
            self._started = True
            self._needs_cancel = False
            return self
        except BaseException as error:
            driver._control.close()
            self._close_after_error(error)
            raise

    def _require_active(self) -> None:
        if not self._started or self._closed:
            raise DriverError("batch is not active")

    def wait_for_paper(self, should_stop: Callable[[], bool]) -> bool:
        """Wait for !HE && TOP without issuing E0 until paper is ready."""
        self._require_active()
        try:
            while not should_stop():
                state = self._driver.hardware_status()
                if should_stop():
                    return False
                if state.temperature_stop:
                    raise DriverError("scanner stopped because of battery temperature")
                if state.cover_open:
                    raise DriverError("scanner cover is open")
                if state.top_sensor and state.paper_present:
                    # SSDevCtl.java:8173-8193 allows the inserted page to settle.
                    time.sleep(0.2)
                    return not should_stop()
                if state.top_sensor:
                    raise DriverError("scanner paper sensors prevent feeding")
                time.sleep(0.3)
            return False
        except BaseException as error:
            self._driver._control.close()
            self._close_after_error(error)
            raise

    def scan_page(self) -> ScanResult:
        self._require_active()
        if self.page_number and not self.continuous:
            raise DriverError("single-page batch has already scanned its page")
        driver = self._driver
        try:
            self._needs_cancel = True
            driver._start_paper()
            stream = driver._read_page()
            self._needs_cancel = False
            info = _parse_image_info(driver._get_image_info())
            color_mode = driver._config.color_mode
            result = ScanResult(
                image=decode_raw_image(stream, info, color_mode),
                info=info,
                color_mode=color_mode,
            )
            self.page_number += 1
            self.report(
                f"image info width={info.width} valid_height={info.height} "
                f"dpi={info.horizontal_dpi}x{info.vertical_dpi} "
                f"color_mode={color_mode.value} bits_per_pixel={color_mode.bits_per_pixel} "
                f"bytes={len(result.image)}"
            )
            return result
        except BaseException as error:
            # Never let cleanup consume a partly read or malformed TCP frame.
            driver._control.close()
            self._close_after_error(error)
            raise

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._started = False
        driver = self._driver
        if driver._batch is self:
            driver._batch = None
        if not self._job_attempted:
            return
        errors = []
        if self._needs_cancel:
            try:
                driver._cancel_read()
            except BaseException as error:
                errors.append(f"CANCEL READ: {error}")
        try:
            driver._end_job()
            self.report("END JOB succeeded")
        except BaseException as error:
            errors.append(f"END JOB: {error}")
        if errors:
            raise DriverError("job cleanup failed: " + "; ".join(errors))

    def _close_after_error(self, error: BaseException) -> None:
        try:
            self.close()
        except BaseException as cleanup:
            self.report(f"batch cleanup also failed: {cleanup}")
            error.add_note(f"batch cleanup also failed: {cleanup}")

    def __enter__(self) -> ScanBatch:
        return self.open()

    def __exit__(self, _type: object, error: BaseException | None, _traceback: object) -> None:
        if error is None:
            self.close()
        else:
            self._close_after_error(error)


class DriverSession:
    """Public reusable scanner session.

    Constructing a session resolves the route only; reserve() performs the first
    scanner connection.  Use it as a context manager to ensure RELEASE is sent.
    """

    def __init__(self, config: Config, reporter: Reporter | None = None) -> None:
        self.config = config
        self.report = print if reporter is None else reporter
        self.identity = route_identity(config.scanner_ip, config.control_port)
        self._driver = _Ix100Driver(config, self.identity, reporter=self.report)
        self.report(
            f"route local_ip={self.identity.local_ip} "
            f"local_mac={_hex(self.identity.mac[:6])} "
            f"broadcast={self.identity.broadcast_ip}"
        )

    def __enter__(self) -> DriverSession:
        return self

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        try:
            self.close()
        except BaseException as error:
            if isinstance(_value, BaseException):
                self.report(f"RELEASE failed: {error}")
                _value.add_note(f"RELEASE failed: {error}")
            else:
                raise

    def close(self, suppress_errors: bool = False) -> None:
        try:
            self._driver.release()
        except Exception:
            if not suppress_errors:
                raise

    def reserve(self) -> None:
        self._driver.reserve()

    def release(self) -> None:
        self._driver.release()

    def scan(self) -> ScanResult:
        return self._driver.scan()

    def batch(self, *, continuous: bool = True) -> ScanBatch:
        return ScanBatch(self._driver, continuous=continuous)

    def hardware_status(self) -> HardwareStatus:
        return self._driver.hardware_status()

__all__ = [
    "ColorMode",
    "Config",
    "DriverError",
    "DriverSession",
    "ImageInfo",
    "HardwareStatus",
    "Reporter",
    "ScanBatch",
    "ScanResult",
    "decode_raw_image",
]
