"""Public, independently usable Python API."""

from contextlib import contextmanager

from backend import open_backend
from core import SetupSession
from info import InfoMixin
from wifi import WifiMixin
from advanced import AdvancedMixin


class SetupDevice(InfoMixin, WifiMixin, AdvancedMixin, SetupSession):
    """USB network settings API. Use connect() for normal backend ownership."""


@contextmanager
def connect(backend: str = "auto", *, usbscan_port: str | None = None,
            timeout: float = 30.0, io_timeout: float = 120.0,
            encoding: str = "utf-8", legacy_key: bool = False):
    """Open USB, acquire setup ownership, then release and close on exit."""
    with open_backend(backend, usbscan_port=usbscan_port, io_timeout=io_timeout) as transport:
        with SetupDevice(transport, timeout=timeout, encoding=encoding, legacy_key=legacy_key) as device:
            yield device
