"""Independent iX100 setup-session protocol, reconstructed from SCApi.

Evidence: reverse/scapi/usb-api.c FUN_1000f1a0, FUN_1000f440,
FUN_10016ec0, FUN_100174e0, FUN_100175a0. USB framing and sense
handling follow ix100-usb, without entering a paper-scanning job.
"""

from __future__ import annotations

import struct
import time

from common import SetupError, operation, require_size, u32


SETUP_PREFIX = b"SETUP NET CMD   "
SETUP_START = b"SETUP NET START "
SETUP_END = b"SETUP NET END   "


class CommandError(SetupError):
    def __init__(self, command: int, result: int):
        self.command = command
        self.result = result
        super().__init__(f"setup command 0x{command:04X} failed: result=0x{result:08X}")


class SetupSession:
    """Own one setup session over a supplied, already-open USB transport.

    The caller owns the transport. This context manages only SETUP NET
    START/END; connect() also opens and closes the selected USB backend.
    Methods are synchronous and must be called serially on one session.
    """

    def __init__(self, transport, *, timeout: float = 30.0,
                 encoding: str = "utf-8", legacy_key: bool = False):
        self.transport = transport
        self.timeout = timeout
        self.encoding = encoding
        self.legacy_key = legacy_key
        self.last_response = b""
        self.last_response_header = b""
        self._owned = False
        self._closed = False
        self._pending = None

    def __enter__(self):
        self.acquire_setup()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.close()
        except Exception as cleanup_error:
            if exc_value is None:
                raise
            exc_value.add_note(f"setup session cleanup also failed: {cleanup_error}")

    def scsi(self, cdb: bytes, *, data_out: bytes | None = None,
             data_in_size: int = 0) -> bytes:
        """Execute a configuration CDB; preserve one-read DATA-IN semantics.

        Status 8 and BUSY on REQUEST SENSE repeat the original transaction
        without a sleep/retry ceiling. REQUEST SENSE status 2 is not recursive.
        This layer is for setup/diagnostic CDBs, not image READ/RIC jobs.
        """
        if self._closed:
            raise SetupError("setup session is closed")
        while True:
            result = self.transport.command(cdb, data_out=data_out, data_in_size=data_in_size)
            status = result.scsi_status
            if status == 8:
                continue
            if status == 2:
                sense_result = self.transport.command(b"\x03\0\0\0\x12\0", data_in_size=18)
                if sense_result.scsi_status == 8:
                    continue
                if sense_result.scsi_status not in (0, 2):
                    raise SetupError(f"REQUEST SENSE: invalid status 0x{sense_result.scsi_status:02X}")
                sense = sense_result.data
                require_size(sense, 18, "REQUEST SENSE")
                if len(sense) != 18 or (sense[0] & 0x7F) not in (0x70, 0x7F):
                    raise SetupError("REQUEST SENSE: unsupported response format")
                if sense[2] & 0x6F:
                    raise SetupError(f"CDB 0x{cdb[0]:02X}: sense key=0x{sense[2] & 15:X}, "
                                     f"ASC/ASCQ={sense[12]:02X}/{sense[13]:02X}, "
                                     f"EOM={bool(sense[2] & 0x40)}, ILI={bool(sense[2] & 0x20)}")
            elif status != 0:
                raise SetupError(f"CDB 0x{cdb[0]:02X}: invalid status 0x{status:02X}")
            if data_in_size and result.embedded_status:
                raise SetupError("received embedded USB success status instead of configuration data")
            return result.data

    def send_diagnostic(self, data: bytes) -> None:
        self.scsi(b"\x1d\0\0" + len(data).to_bytes(2, "big") + b"\0", data_out=data)

    def receive_diagnostic(self, size: int) -> bytes:
        return self.scsi(b"\x1c\0\0" + size.to_bytes(2, "big") + b"\0", data_in_size=size)

    def diagnostic(self, data: bytes, read_size: int) -> bytes:
        """One direct diagnostic exchange, with no SETUP NET CMD header."""
        self.send_diagnostic(data)
        return self.receive_diagnostic(read_size)

    @operation("Acquire the USB wireless setup session (the CLI releases it on exit)", mutates=True)
    def acquire_setup(self) -> dict:
        if not self._owned:
            response = self.diagnostic(SETUP_START, 1)
            require_size(response, 1, "SETUP NET START")
            if response[0]:
                raise SetupError(f"SETUP NET START rejected: 0x{response[0]:02X}")
            self._owned = True
        return {"setup_session_owned": True}

    @operation("Release the current USB wireless setup session", mutates=True)
    def release_setup(self) -> dict:
        if self._owned:
            self._owned = False
            self._pending = None
            response = self.diagnostic(SETUP_END, 1)
            require_size(response, 1, "SETUP NET END")
            if response[0]:
                raise SetupError(f"SETUP NET END rejected: 0x{response[0]:02X}")
        return {"setup_session_owned": False}

    def close(self) -> None:
        if not self._closed:
            try:
                self.release_setup()
            finally:
                self._closed = True

    def send_setup(self, command: int, payload: bytes = b"", *,
                   request_size: int | None = None, argument: int = 0) -> None:
        if not self._owned:
            raise SetupError("no setup-session ownership; use connect() or acquire_setup()")
        if self._pending is not None:
            raise SetupError("a configuration operation is still pending; receive its result first")
        if request_size is None:
            request_size = len(payload)
        block = ((16 + len(payload)).to_bytes(2, "big") + b"\0\0"
                 + struct.pack("<IIII", command, 0, argument, request_size) + payload)
        data = SETUP_PREFIX + block
        started = time.monotonic()
        self.send_diagnostic(data)
        self._pending = (command, data, started)

    def receive_setup(self, command: int, read_size: int = 0, *, wait: bool = True) -> bytes:
        """Read a result; status 1 polls 1C only, status 83 reacquires then resends.

        Unlike transport BUSY this asynchronous layer uses the official 500 ms
        interval and 360-poll ceiling. A caller-provided timeout is in seconds.
        """
        pending = self._pending
        if pending is not None and pending[0] != command:
            raise SetupError("a different configuration command is pending")
        started = pending[2] if pending else time.monotonic()
        polls = 0
        try:
            while True:
                response = self.receive_diagnostic(20 + read_size)
                require_size(response, 1, "setup status")
                state = response[0]
                self.last_response = response
                self.last_response_header = response[:20]
                if state == 1:
                    if not wait:
                        raise SetupError("configuration operation is still pending")
                    if polls >= 360 or time.monotonic() - started > self.timeout:
                        raise TimeoutError(f"setup command 0x{command:04X} timed out")
                    time.sleep(0.5)
                    polls += 1
                    continue
                if state == 0x83 and pending is not None:
                    self._owned = False
                    self.acquire_setup()
                    self.send_diagnostic(pending[1])
                    polls = 0
                    continue
                if state:
                    raise SetupError(f"setup command 0x{command:04X}: state=0x{state:02X}")
                require_size(response, 20, "setup response header")
                result = u32(response, 8)
                if result:
                    raise CommandError(command, result)
                length = u32(response, 16)
                require_size(response, 20 + length, "setup payload")
                return response[20:20 + length]
        finally:
            # Keep the pending request only for the explicitly asynchronous poll.
            if wait or not self.last_response or self.last_response[0] != 1:
                self._pending = None

    def exchange(self, command: int, payload: bytes = b"", read_size: int = 0,
                 request_size: int | None = None, *, argument: int = 0,
                 offset: int | None = None) -> bytes:
        if offset is not None:
            argument = offset
        self.send_setup(command, payload, request_size=request_size, argument=argument)
        return self.receive_setup(command, read_size)
