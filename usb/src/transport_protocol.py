"""Shared Fujitsu/Ricoh SCSI-over-USB framing used by all transports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


USB_COMMAND_SIZE = 0x1F
USB_COMMAND_OFFSET = 0x13
USB_STATUS_SIZE = 0x0D
USB_STATUS_OFFSET = 0x09


def build_command_packet(cdb: bytes) -> bytes:
    """Wrap a SCSI CDB in the scanner's fixed 31-byte USB command frame."""
    packet = bytearray(USB_COMMAND_SIZE)
    packet[0] = 0x43
    packet[USB_COMMAND_OFFSET : USB_COMMAND_OFFSET + len(cdb)] = cdb
    return bytes(packet)


def is_embedded_success_status(data: bytes) -> bool:
    """Return true only for the exact status frame recognized by the DLL."""
    return data == b"\x53" + b"\x00" * (USB_STATUS_SIZE - 1)


@dataclass(frozen=True)
class CommandResult:
    data: bytes
    status_packet: bytes
    embedded_status: bool = False
    data_in_size: int = 0
    transferred_size: int = 0

    @property
    def short_read(self) -> bool:
        """Whether the one DATA-IN transfer returned fewer bytes than requested."""
        return self.transferred_size < self.data_in_size

    @property
    def scsi_status(self) -> int:
        return self.status_packet[USB_STATUS_OFFSET]


class CommandTransport(Protocol):
    description: str

    def command(
        self,
        cdb: bytes,
        *,
        data_out: bytes | None = None,
        data_in_size: int = 0,
    ) -> CommandResult: ...


class FujitsuUsbProtocol:
    """Protocol engine layered over one bulk writer and one bulk reader."""

    description = "Fujitsu SCSI-over-USB transport"

    def _write(self, data: bytes) -> None:
        raise NotImplementedError

    def _read(self, size: int) -> bytes:
        raise NotImplementedError

    def command(
        self,
        cdb: bytes,
        *,
        data_out: bytes | None = None,
        data_in_size: int = 0,
    ) -> CommandResult:
        self._write(build_command_packet(cdb))
        if data_out:
            self._write(data_out)

        # One DATA-IN read preserves the firmware's image/status boundary.
        data = self._read(data_in_size) if data_in_size else b""
        embedded_status = is_embedded_success_status(data)
        status = data if embedded_status else self._read(USB_STATUS_SIZE)
        if len(status) != USB_STATUS_SIZE:
            raise OSError(f"short USB status packet: {len(status)}/{USB_STATUS_SIZE}")
        return CommandResult(
            data=b"" if embedded_status else data,
            status_packet=status,
            embedded_status=embedded_status,
            data_in_size=data_in_size,
            # An embedded status counts as transferred bytes, but not image data.
            transferred_size=len(data),
        )


def inquiry(
    transport: CommandTransport, allocation_length: int = 96
) -> CommandResult:
    cdb = bytes((0x12, 0x00, 0x00, 0x00, allocation_length, 0x00))
    return transport.command(cdb, data_in_size=allocation_length)
