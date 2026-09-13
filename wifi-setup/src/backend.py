"""Open one USB backend; never switch transports after a device command starts."""

from __future__ import annotations

from contextlib import contextmanager
import os


@contextmanager
def open_backend(backend: str = "auto", *, usbscan_port: str | None = None,
                 io_timeout: float = 120.0):
    if backend == "usbscan" or (backend == "auto" and usbscan_port is not None):
        from transport_usbscan import UsbscanTransport
        transport = UsbscanTransport(usbscan_port)
        transport.__enter__()
    else:
        try:
            from transport_libusb import LibusbDeviceUnavailable, LibusbTransport
        except ImportError:
            if backend != "auto" or os.name != "nt":
                raise
            from transport_usbscan import UsbscanTransport
            transport = UsbscanTransport(usbscan_port)
            transport.__enter__()
        else:
            transport = LibusbTransport(timeout_ms=int(io_timeout * 1000))
            try:
                transport.__enter__()
            except LibusbDeviceUnavailable:
                if backend != "auto" or os.name != "nt":
                    raise
                from transport_usbscan import UsbscanTransport
                transport = UsbscanTransport(usbscan_port)
                transport.__enter__()
    try:
        yield transport
    finally:
        transport.close()
