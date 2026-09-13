"""Cross-platform PyUSB/libusb transport for ScanSnap iX100/iX110."""

from __future__ import annotations

import os
from contextlib import suppress
from typing import Any

import usb.core
import usb.util

from transport_protocol import FujitsuUsbProtocol


KNOWN_SCANSNAP_IDS = (
    (0x05CA, 0x03C8, "RICOH ScanSnap iX110"),
    (0x04C5, 0x13F4, "Fujitsu ScanSnap iX100"),
)
# Backward-compatible name for callers that imported the original constant.
KNOWN_IX100_IDS = KNOWN_SCANSNAP_IDS


class LibusbDeviceUnavailable(RuntimeError):
    """Raised when libusb cannot find or open a supported scanner."""


def packaged_libusb_backend() -> Any | None:
    """Use the bundled Windows libusb DLL and the system backend elsewhere."""
    if os.name != "nt":
        return None
    try:
        import libusb_package
    except ImportError as error:
        raise LibusbDeviceUnavailable(
            "libusb-package is required on Windows; install requirements.txt"
        ) from error
    backend = libusb_package.get_libusb1_backend()
    if backend is None:
        raise LibusbDeviceUnavailable("libusb-package could not load libusb-1.0")
    return backend


class LibusbTransport(FujitsuUsbProtocol):
    """Exclusive bulk access through PyUSB and a libusb-compatible driver."""

    def __init__(self, timeout_ms: int = 120_000, backend: Any | None = None):
        self.timeout_ms = timeout_ms
        self._backend = backend
        self._device: Any | None = None
        self._interface_number: int | None = None
        self._endpoint_in: int | None = None
        self._endpoint_out: int | None = None
        self._claimed = False
        self._detached_kernel_driver = False
        self.description = "PyUSB/libusb ScanSnap iX100/iX110"

    @property
    def interface_number(self) -> int | None:
        return self._interface_number

    @property
    def endpoint_in(self) -> int | None:
        return self._endpoint_in

    @property
    def endpoint_out(self) -> int | None:
        return self._endpoint_out

    def _find_device(self) -> tuple[Any, str]:
        backend = self._backend
        if backend is None:
            backend = packaged_libusb_backend()
            self._backend = backend
        for vendor_id, product_id, name in KNOWN_SCANSNAP_IDS:
            device = usb.core.find(
                idVendor=vendor_id,
                idProduct=product_id,
                backend=backend,
            )
            if device is not None:
                return device, name
        ids = ", ".join(
            f"{vid:04X}:{pid:04X}" for vid, pid, _ in KNOWN_SCANSNAP_IDS
        )
        hint = (
            " On Windows, bind the scanner to WinUSB before using libusb."
            if os.name == "nt"
            else " Check USB permissions and that no other driver owns the interface."
        )
        raise LibusbDeviceUnavailable(
            f"no supported ScanSnap iX100/iX110 found ({ids}).{hint}"
        )

    def __enter__(self) -> "LibusbTransport":
        if self._device is not None:
            raise RuntimeError("libusb transport is already open")
        try:
            device, fallback_name = self._find_device()
            self._device = device
            try:
                configuration = device.get_active_configuration()
            except usb.core.USBError:
                device.set_configuration()
                configuration = device.get_active_configuration()

            interface = usb.util.find_descriptor(
                configuration,
                custom_match=lambda candidate: any(
                    usb.util.endpoint_type(endpoint.bmAttributes)
                    == usb.util.ENDPOINT_TYPE_BULK
                    for endpoint in candidate
                ),
            )
            if interface is None:
                raise LibusbDeviceUnavailable(
                    "ScanSnap has no interface with bulk pipes"
                )

            interface_number = int(interface.bInterfaceNumber)
            self._interface_number = interface_number
            if hasattr(device, "is_kernel_driver_active"):
                try:
                    if device.is_kernel_driver_active(interface_number):
                        device.detach_kernel_driver(interface_number)
                        self._detached_kernel_driver = True
                except (NotImplementedError, usb.core.USBError):
                    pass

            usb.util.claim_interface(device, interface_number)
            self._claimed = True

            def find_bulk_endpoint(direction: int) -> Any:
                return usb.util.find_descriptor(
                    interface,
                    custom_match=lambda endpoint: (
                        usb.util.endpoint_type(endpoint.bmAttributes)
                        == usb.util.ENDPOINT_TYPE_BULK
                        and usb.util.endpoint_direction(endpoint.bEndpointAddress)
                        == direction
                    ),
                )

            endpoint_in = find_bulk_endpoint(usb.util.ENDPOINT_IN)
            endpoint_out = find_bulk_endpoint(usb.util.ENDPOINT_OUT)
            if endpoint_in is None or endpoint_out is None:
                raise LibusbDeviceUnavailable(
                    "ScanSnap bulk IN/OUT endpoints are missing"
                )

            self._endpoint_in = int(endpoint_in.bEndpointAddress)
            self._endpoint_out = int(endpoint_out.bEndpointAddress)
            try:
                product = usb.util.get_string(device, device.iProduct)
            except (NotImplementedError, ValueError, usb.core.USBError):
                product = None
            self.description = (
                f"{product or fallback_name} via PyUSB/libusb "
                f"({device.idVendor:04X}:{device.idProduct:04X}, "
                f"bulk {self._endpoint_out:02X}->{self._endpoint_in:02X})"
            )
            return self
        except (NotImplementedError, usb.core.USBError) as error:
            self.close()
            hint = (
                "The device cannot be discovered or opened through libusb. "
                "On Windows, replace usbscan.sys with WinUSB; on Linux, add a udev rule."
            )
            raise LibusbDeviceUnavailable(f"{hint} Original error: {error}") from error
        except BaseException:
            self.close()
            raise

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        device = self._device
        interface_number = self._interface_number
        try:
            if device is not None:
                try:
                    if self._claimed and interface_number is not None:
                        with suppress(NotImplementedError, usb.core.USBError):
                            usb.util.release_interface(device, interface_number)
                finally:
                    try:
                        if self._detached_kernel_driver and interface_number is not None:
                            with suppress(NotImplementedError, usb.core.USBError):
                                device.attach_kernel_driver(interface_number)
                    finally:
                        with suppress(NotImplementedError, usb.core.USBError):
                            usb.util.dispose_resources(device)
        finally:
            self._device = None
            self._interface_number = None
            self._endpoint_in = None
            self._endpoint_out = None
            self._claimed = False
            self._detached_kernel_driver = False

    def _write(self, data: bytes) -> None:
        if self._device is None or self._endpoint_out is None:
            raise RuntimeError("libusb transport is not open")
        transferred = self._device.write(
            self._endpoint_out,
            data,
            timeout=self.timeout_ms,
        )
        if transferred != len(data):
            raise OSError(f"short libusb write: {transferred}/{len(data)}")

    def _read(self, size: int) -> bytes:
        if self._device is None or self._endpoint_in is None:
            raise RuntimeError("libusb transport is not open")
        data = self._device.read(
            self._endpoint_in,
            size,
            timeout=self.timeout_ms,
        )
        return bytes(data)
