"""Windows usbscan.sys transport for Fujitsu/Ricoh SCSI-over-USB packets."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from transport_protocol import FujitsuUsbProtocol


GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_ATTRIBUTE_SYSTEM = 0x00000004


class UsbscanTransport(FujitsuUsbProtocol):
    """Exclusive synchronous access to one usbscan.sys device port."""

    def __init__(self, port: str | None = None):
        self._requested_port = port
        self.port = port
        self.description = "Windows usbscan.sys"
        if port is not None:
            self.description += f" at {port}"
        self._handle: int | None = None
        self._pipe_control: int | None = None
        self._base_read: int | None = None
        self._pipe_read: int | None = None
        self._pipe_write: int | None = None
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._declare_functions()

    def _declare_functions(self) -> None:
        self._kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        self._kernel32.CreateFileW.restype = wintypes.HANDLE
        self._kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel32.CloseHandle.restype = wintypes.BOOL
        self._kernel32.ReadFile.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPVOID,
        ]
        self._kernel32.ReadFile.restype = wintypes.BOOL
        self._kernel32.WriteFile.argtypes = self._kernel32.ReadFile.argtypes
        self._kernel32.WriteFile.restype = wintypes.BOOL

    def _open_handle(self, path: str, access: int) -> int:
        handle = self._kernel32.CreateFileW(
            path, access, 0, None, OPEN_EXISTING, FILE_ATTRIBUTE_SYSTEM, None
        )
        if handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        return handle

    def __enter__(self) -> "UsbscanTransport":
        if self._handle is not None:
            raise RuntimeError("usbscan transport is already open")
        port = self._requested_port
        if port is None:
            from discovery import find_ix100_driver

            port = str(find_ix100_driver().get("port") or "")
            if not port.startswith(r"\\.\Usbscan"):
                raise RuntimeError("the ScanSnap driver did not publish a usbscan port")
        self.port = port
        self.description = f"Windows usbscan.sys at {port}"
        # This order and access split mirror SSiX100rh-x64.dll. usbscan.sys
        # exposes bulk IN as "\\0" and bulk OUT as "\\2"; the base handle is
        # only the control channel. No sharing prevents protocol interleaving.
        try:
            self._handle = self._open_handle(
                self.port, GENERIC_READ | GENERIC_WRITE
            )
            self._pipe_control = self._open_handle(
                self.port + r"\0", GENERIC_READ | GENERIC_WRITE
            )
            self._base_read = self._open_handle(self.port, GENERIC_READ)
            self._pipe_read = self._open_handle(self.port + r"\0", GENERIC_READ)
            self._pipe_write = self._open_handle(self.port + r"\2", GENERIC_WRITE)
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    @property
    def handle(self) -> int:
        if self._handle is None:
            raise RuntimeError("usbscan transport is not open")
        return self._handle

    def close(self) -> None:
        for attribute in (
            "_handle",
            "_pipe_control",
            "_base_read",
            "_pipe_read",
            "_pipe_write",
        ):
            handle = getattr(self, attribute)
            if handle is not None:
                setattr(self, attribute, None)
                self._kernel32.CloseHandle(handle)

    def _write(self, data: bytes) -> None:
        if self._pipe_write is None:
            raise RuntimeError("usbscan bulk OUT pipe is not open")
        buffer = ctypes.create_string_buffer(data, len(data))
        transferred = wintypes.DWORD()
        ok = self._kernel32.WriteFile(
            self._pipe_write,
            buffer,
            len(data),
            ctypes.byref(transferred),
            None,
        )
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())
        if transferred.value != len(data):
            raise OSError(f"short usbscan write: {transferred.value}/{len(data)}")

    def _read(self, size: int) -> bytes:
        if self._pipe_read is None:
            raise RuntimeError("usbscan bulk IN pipe is not open")
        buffer = ctypes.create_string_buffer(size)
        transferred = wintypes.DWORD()
        ok = self._kernel32.ReadFile(
            self._pipe_read,
            buffer,
            size,
            ctypes.byref(transferred),
            None,
        )
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())
        return buffer.raw[: transferred.value]
