"""ScanSnap iX100/iX110 uncompressed color, grayscale and black-and-white driver.

Protocol evidence and known differences: ../../../ix-100-usb-dev/USB_COMMUNICATION_AUDIT_20260910.md.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from enum import Enum
import os
import struct
import time

from transport_protocol import CommandResult, CommandTransport


INVERT = bytes(range(255, -1, -1))
READ_INFO_RESPONSE_SIZE = 0x10
WINDOW_DESCRIPTOR_SIZE = 0x40
IMAGE_READ_BLOCK_SIZE = 0x80000
HARDWARE_STATUS_SIZE = 0x20
# Mercury model 101D8724+38: reference/default height, in 1/1200 inch units.
MODEL_WINDOW_HEIGHT_UNITS = 0xA543
# Mercury model 101D8724+34: maximum width, in 1/1200 inch units.
MODEL_WINDOW_WIDTH_UNITS = 0x2880
Reporter = Callable[[str], None]


def _ignore(_message: str) -> None:
    pass


def put_be(buffer: bytearray, offset: int, value: int, size: int) -> None:
    buffer[offset : offset + size] = value.to_bytes(size, "big")


@dataclass(frozen=True)
class Sense:
    raw: bytes

    @property
    def valid(self) -> bool:
        return len(self.raw) == 18 and (self.raw[0] & 0x7F) in (0x70, 0x7F)

    @property
    def key(self) -> int:
        return self.raw[2] & 0x0F

    @property
    def eom(self) -> bool:
        return bool(self.raw[2] & 0x40)

    @property
    def ili(self) -> bool:
        return bool(self.raw[2] & 0x20)

    @property
    def asc(self) -> int:
        return self.raw[12]

    @property
    def ascq(self) -> int:
        return self.raw[13]

    @property
    def information(self) -> int:
        return int.from_bytes(self.raw[3:7], "big")

    def describe(self) -> str:
        return (
            f"key=0x{self.key:02X} ASC/ASCQ=0x{self.asc:02X}/0x{self.ascq:02X} "
            f"EOM={int(self.eom)} ILI={int(self.ili)} residual={self.information}"
        )


class NoDocumentError(RuntimeError):
    """Raised when the scanner's paper sensor reports no document."""


class ScanMode(Enum):
    SINGLE = "single"
    CONTINUOUS = "continuous"


class ColorMode(Enum):
    COLOR = "color"
    GRAY = "gray"
    MONO = "mono"

    @property
    def bits_per_pixel(self) -> int:
        return {"color": 24, "gray": 8, "mono": 1}[self.value]

    @property
    def composition(self) -> int:
        return {"color": 5, "gray": 2, "mono": 0}[self.value]


class Scanner:
    """Low-level SCSI command helper layered over an open transport."""

    def __init__(self, transport: CommandTransport, reporter: Reporter | None = None):
        self.transport = transport
        self.report = reporter or _ignore
        # SSiX100 Dispatch mode 4 preserves these flags between DATA-IN calls.
        # Non-DATA-IN dispatch resets both; RIC itself is inside the dispatch.
        self._readiness_required = [True, True]
        self._closed = False

    def request_sense(self) -> Sense | None:
        result = self.transport.command(
            bytes((0x03, 0, 0, 0, 0x12, 0)), data_in_size=0x12
        )
        if result.scsi_status == 8:
            # The minidriver returns BUSY to DispatchScsiCommand, which then
            # repeats the original command rather than REQUEST SENSE alone.
            return None
        if result.scsi_status not in (0, 2):
            raise RuntimeError(
                f"REQUEST SENSE failed with status 0x{result.scsi_status:02X}"
            )
        if len(result.data) != 0x12:
            raise RuntimeError(
                f"REQUEST SENSE returned {len(result.data)}/18 bytes"
            )
        sense = Sense(result.data)
        if not sense.valid:
            raise RuntimeError("REQUEST SENSE returned an unsupported response format")
        return sense

    def _status_sense(self, name: str, result: CommandResult) -> Sense | None:
        if result.scsi_status == 2:
            return self.request_sense()
        if result.scsi_status not in (0, 8):
            raise RuntimeError(f"{name}: SCSI status 0x{result.scsi_status:02X}")
        return None

    def command(
        self,
        name: str,
        cdb: bytes,
        *,
        data_out: bytes | None = None,
        data_in_size: int = 0,
    ) -> tuple[CommandResult, Sense | None]:
        if self._closed:
            raise RuntimeError("scanner connection is closed")
        image_read = data_in_size > 0 and cdb[0] == 0x28 and cdb[2] == 0
        face = int(image_read and cdb[5] != 0)
        if not data_in_size:
            self._readiness_required[:] = [True, True]
        dispatch_sense: Sense | None = None
        # DispatchScsiCommand -> ExecuteDataIn includes conditional RIC on
        # every BUSY retry. No retry limit or host sleep belongs at this layer.
        while True:
            if image_read and self._readiness_required[face]:
                ric = bytearray(10)
                ric[0] = 0xF1
                ric[1] = cdb[1] | 0x10
                ric[2] = cdb[5]
                ric[6:9] = cdb[6:9]
                prepared = self.transport.command(bytes(ric))
                sense = self._status_sense("READINESS IMAGE CONTROL", prepared)
                if prepared.scsi_status == 8 or (prepared.scsi_status == 2 and sense is None):
                    continue
                if sense is not None:
                    dispatch_sense = sense
                    if sense.key != 0 or sense.ili:
                        raise RuntimeError(f"READINESS IMAGE CONTROL: {sense.describe()}")
                self._readiness_required[face] = False
                self.report("READINESS IMAGE CONTROL: OK")
            result = self.transport.command(
                cdb, data_out=data_out, data_in_size=data_in_size
            )
            status = result.scsi_status
            sense = self._status_sense(name, result)
            if sense is not None:
                dispatch_sense = sense
            if status == 0:
                return result, None
            status_failed = sense is None or sense.key != 0 or sense.ili
            if image_read and status_failed:
                # ExecuteDataIn retains readiness on ILI, otherwise the next
                # attempt needs RIC. The sense buffer lives for this dispatch.
                self._readiness_required[face] = not (
                    dispatch_sense is not None and dispatch_sense.ili
                )
            if status == 8 or (status == 2 and sense is None):
                continue
            return result, sense

    def checked(self, name: str, cdb: bytes, *, report: bool = True, **kwargs) -> bytes:
        result, sense = self.command(name, cdb, **kwargs)
        if sense is not None and (sense.key != 0 or sense.eom):
            detail = f"{name}: {sense.describe()}"
            if cdb[0] == 0x24:
                # Preserve the rejected window and all sense bytes before job
                # cleanup sends commands that can replace device sense state.
                detail += (
                    f"\nSET WINDOW CDB: {cdb.hex(' ')}"
                    f"\nSET WINDOW DATA: {kwargs['data_out'].hex(' ')}"
                    f"\nREQUEST SENSE DATA: {sense.raw.hex(' ')}"
                )
            raise RuntimeError(detail)
        requested = kwargs.get("data_in_size", 0)
        if requested and (result.embedded_status or len(result.data) != requested):
            raise RuntimeError(f"{name}: short data response {len(result.data)}/{requested}")
        if report:
            self.report(f"{name}: OK")
        return result.data

    def cancel_transfer(self) -> None:
        """Mercury SC_SetCancelXfer: F1 04 has no DATA-IN phase."""
        self.checked("SCANNER CONTROL / CANCEL", bytes.fromhex("F1 04 00 00 00 00 00 00 00 00"))

    def _start_job_notification(self, name: str, payload: bytes) -> None:
        """Keep device replies advisory only for the two startup notifications."""
        # SshCtl NotificationState(1) ignores SetJobMode(0)'s device result.
        # Use command(), not an exception handler around checked(): incomplete
        # I/O, short status/sense and invalid status/sense still propagate.
        _result, sense = self.command(
            name, bytes((0x15, 0x10, 0, 0, 12, 0)), data_out=payload,
        )
        if sense is not None:
            self.report(
                f"{name}: device status: {sense.describe()}; "
                "continuing startup notification as the official driver does"
            )
        else:
            self.report(f"{name}: OK")

    def set_job_active(self, active: bool) -> None:
        """Apply the iX100 MODE SELECT portion of Mercury JobMode 0/1."""
        payload = bytearray(12)
        payload[4:7] = bytes((0x2C, 6, 4 if active else 5))
        if not active:
            self.checked(
                "SCAN JOB / END", bytes((0x15, 0x10, 0, 0, 12, 0)),
                data_out=bytes(payload),
            )
            return

        self._start_job_notification("SCAN JOB / START", bytes(payload))
        # Mercury FUN_10010fa0 continues to +0x11C(0, 0, 0x11, 0) even if
        # action 4 was rejected. Its only gate is the iX100 model +0x9A field.
        # NotificationState(1) does not fail the scan on either device reply.
        self._start_job_notification(
            "SCAN JOB / PAGE 3A",
            bytes((0, 0, 0, 0, 0x3A, 6, 0x80, 0x11, 0, 0, 0, 0)),
        )

    def end_waiting_scan(self) -> None:
        """The iX100-specific first step of Mercury JobMode 1."""
        self.checked(
            "END WAITING SCAN", bytes((0x1D, 0, 0, 0, 16, 0)),
            data_out=b"END WAITING SCAN",
        )

    def finish_job(self, *, cancel: bool) -> None:
        """End transfer, waiting and job ownership, attempting every stage."""
        steps = []
        if cancel:
            steps.append(self.cancel_transfer)
        # SshCtl NotificationState(3) calls JobMode 1 in both its iX100
        # branch and its job-capability branch. These are two official calls,
        # not retries; CANCEL above is still sent only once.
        for _ in range(2):
            steps.extend((self.end_waiting_scan, lambda: self.set_job_active(False)))
        first_error: Exception | None = None
        for finish in steps:
            try:
                finish()
            except Exception as error:
                self.report(f"job cleanup failed: {error}")
                if first_error is None:
                    first_error = error
        if first_error is not None:
            raise first_error

    def object_position(self, action: int, label: str) -> None:
        """Execute Mercury SC_ObjectPosition; no subsequent TUR is inserted."""
        self.checked(f"OBJECT POSITION / {label}", bytes((0x31, action)) + bytes(8))

    def close(self) -> None:
        """Perform the minidriver's final GetStatus/TUR before port release."""
        if self._closed:
            return
        try:
            self.checked("CLOSE / TEST UNIT READY", bytes(6))
        except Exception as error:
            # The official destructor ignores GetStatus failure and proceeds
            # to release handles. Keep a completed page deliverable as well.
            self.report(f"close status query failed: {error}")
        finally:
            self._closed = True


@dataclass(frozen=True)
class ScanSettings:
    """Fixed scan windows in 1/1200 inch units, selected by DPI and overscan."""

    dpi: int = 300
    mode: ScanMode = ScanMode.SINGLE
    overscan: bool = True
    color_mode: ColorMode = ColorMode.COLOR

    @property
    def width_units(self) -> int:
        return MODEL_WINDOW_WIDTH_UNITS if self.overscan else 10208

    @property
    def maximum_width_pixels(self) -> int:
        # This is a read bound only; it does not alter the transmitted width.
        return (self.window_width_units * self.dpi + 1199) // 1200

    @property
    def window_width_units(self) -> int:
        return self.width_units

    @property
    def window_height_units(self) -> int:
        return 17828 if self.dpi == 600 else MODEL_WINDOW_HEIGHT_UNITS

    @property
    def maximum_lines(self) -> int:
        return (self.window_height_units * self.dpi + 1199) // 1200


@dataclass(frozen=True)
class ScannedPage:
    pixels: bytes
    width: int
    height: int
    color_mode: ColorMode = ColorMode.COLOR


@dataclass(frozen=True)
class ImageDimensions:
    width: int
    lines: int
    window_width: int
    window_lines: int
    effective_available: bool


def make_auto_size_detect(*, overscan: bool = False) -> tuple[bytes, bytes]:
    """Mercury page 3C: automatic length and the iX100 extra flag."""
    # SC_ModeSelectAutoSizeDetect(0,1,overscan,0,0,0,1).
    # SshCtl SetOverScan -> cap1149=4 -> mode 0xF0.
    payload = bytearray.fromhex("00 00 00 00 3C 06 00 80 08 00 00 00")
    if overscan:
        payload[9] = 0xC0
    return (
        bytes.fromhex("15 10 00 00 0C 00"),
        bytes(payload),
    )


def make_set_window(
    dpi: int, width_units: int, height_units: int,
    color_mode: ColorMode = ColorMode.COLOR,
) -> tuple[bytes, bytes]:
    # CSWParam_Lynx_Color / CSWParam_Lynx: 8-byte header + 64-byte WDB.
    # Transmit the fixed dimensions selected by ScanSettings without alignment.
    descriptor = bytearray(WINDOW_DESCRIPTOR_SIZE)
    color = color_mode is ColorMode.COLOR
    put_be(descriptor, 0x02, dpi, 2)
    put_be(descriptor, 0x04, dpi, 2)
    put_be(descriptor, 0x0E, width_units, 4)
    put_be(descriptor, 0x12, height_units, 4)
    if color_mode is ColorMode.MONO:
        descriptor[0x17] = 0x80  # Selected midpoint threshold; no halftoning.
    descriptor[0x19] = color_mode.composition
    descriptor[0x1A] = 1 if color_mode is ColorMode.MONO else 8
    descriptor[0x29] = 0  # Device gamma selection, without a downloaded LUT.
    if color:
        descriptor[0x28] = 0xC1
        descriptor[0x2A] = 1
        descriptor[0x2B] = 5
    descriptor[0x35] = 0xC0
    put_be(descriptor, 0x36, width_units, 4)
    put_be(descriptor, 0x3A, height_units, 4)

    payload = bytearray(8 + len(descriptor))
    put_be(payload, 6, len(descriptor), 2)
    payload[8:] = descriptor
    cdb = bytearray(10)
    cdb[0] = 0x24
    put_be(cdb, 6, len(payload), 3)
    return bytes(cdb), bytes(payload)


def transform_pixels(data: bytes) -> bytes:
    # iX100 raw front-image polarity: model +BE/+C2 are both 1.
    return data.translate(INVERT)


class ScanBatch:
    """A single-page or continuous batch on one scanner connection."""

    def __init__(
        self,
        scanner: Scanner,
        settings: ScanSettings,
        reporter: Reporter | None = None,
    ):
        self.scanner = scanner
        self.settings = settings
        self.report = reporter or _ignore
        self.initialized = False
        self.acquisition_active = False
        # Device job ownership survives a completed page. The normal final
        # ENDXFER branch in fjtw32 FUN_1001e0c0 sends SC_SetCancelXfer too.
        self.job_active = False
        self._transfer_started = False
        self._closed = False
        self._paper_ready = False

    def initialize(self) -> None:
        if self._closed:
            raise RuntimeError("scan batch is closed; open a new batch")
        if self.initialized:
            return
        # Mercury SC_Initialize's API readiness loop, separate from USB BUSY.
        for attempt in range(50):
            _result, sense = self.scanner.command("TEST UNIT READY", bytes(6))
            if sense is None or (sense.key == 0 and not sense.eom):
                self.report("TEST UNIT READY: OK")
                break
            if attempt != 49:
                time.sleep(0.1)
        else:
            raise RuntimeError(f"TEST UNIT READY: {sense.describe()}")

        # Mercury SC_InitializeScannerTable's iX100 vendor capability query.
        self.scanner.checked(
            "INQUIRY / CAPABILITIES", bytes((0x12, 1, 0xF0, 0, 0x79, 0)),
            data_in_size=0x79,
        )
        # Own cleanup before START, including a partial I/O failure.
        self.job_active = True
        self.scanner.set_job_active(True)
        self._configure_batch()
        self.initialized = True
        self.report(f"scan mode: {self.settings.mode.value}")
        self.report(
            f"color mode: {self.settings.color_mode.value} "
            f"({self.settings.color_mode.bits_per_pixel} bits/pixel)"
        )

    def _configure_batch(self) -> None:
        # Configure once per batch, with device gamma 0 and no LUT download.
        cdb, payload = make_auto_size_detect(overscan=self.settings.overscan)
        self.scanner.checked("AUTO SIZE DETECT", cdb, data_out=payload)

        cdb, payload = make_set_window(
            self.settings.dpi, self.settings.window_width_units,
            self.settings.window_height_units, self.settings.color_mode,
        )
        self.scanner.checked("SET WINDOW", cdb, data_out=payload)

    def paper_loaded(self) -> bool:
        """Read the iX100 paper sensor without starting a page."""
        if not self.initialized:
            raise RuntimeError("scan batch is not initialized")
        # fjtw32 cap8032 selects the iX100 extended 32-byte C2 response.
        response = self.scanner.checked(
            "GET HARDWARE STATUS", bytes.fromhex("C2 00 00 00 00 00 00 00 20 00"),
            data_in_size=HARDWARE_STATUS_SIZE, report=False,
        )
        return not bool(response[3] & 0x80)

    def wait_for_paper(self, should_stop: Callable[[], bool]) -> bool:
        """Wait for insertion or the caller's end request; issue no FEED here."""
        if not self.initialized:
            raise RuntimeError("scan batch is not initialized")
        while not should_stop():
            if self.paper_loaded():
                if should_stop():
                    return False
                self._paper_ready = True
                self.report("paper sensor: loaded")
                return True
            # Host UI/paper polling only; USB BUSY retries remain immediate.
            time.sleep(0.1)
        return False

    def _check_paper(self) -> None:
        paper_loaded = self.paper_loaded()
        self.report(f"paper sensor: {'loaded' if paper_loaded else 'empty'}")
        if not paper_loaded:
            raise NoDocumentError("the ScanSnap paper sensor reports no document")

    def _get_read_info(self, *, report: bool = True) -> ImageDimensions:
        """Mercury's 16-byte READ(type=0x80), front-window selector zero."""
        response = self.scanner.checked(
            "GET READ INFO", bytes.fromhex("28 00 80 00 00 00 00 00 10 00"),
            data_in_size=READ_INFO_RESPONSE_SIZE, report=False,
        )
        window_width, window_lines, paper_width, paper_lines = struct.unpack(
            ">4I", response
        )
        # SC_GetReadInfo uses stream width; effective width is metadata only.
        width = window_width
        lines = min(paper_lines or window_lines, window_lines)
        effective_available = paper_lines > 0

        if window_width == 0 or window_lines == 0:
            raise RuntimeError(
                "GET READ INFO returned invalid dimensions: "
                f"window={window_width}x{window_lines}, "
                f"effective={paper_width}x{paper_lines}"
            )
        if (window_width > self.settings.maximum_width_pixels
                or window_lines > self.settings.maximum_lines):
            raise RuntimeError(
                "GET READ INFO exceeds the configured scan window: "
                f"{window_width}x{window_lines} > "
                f"{self.settings.maximum_width_pixels}x{self.settings.maximum_lines}"
            )
        if effective_available and report:
            self.report(
                f"image size: {width} x {lines} "
                f"(window height {window_lines}, detected paper width {paper_width})"
            )
        elif report:
            self.report(
                f"image window: {window_width} x {window_lines}; "
                "effective height not yet available"
            )
        return ImageDimensions(
            width=width,
            lines=lines,
            window_width=window_width,
            window_lines=window_lines,
            effective_available=effective_available,
        )

    def _read_image_block(self, request: int) -> tuple[bytes, bool]:
        """Read one front-image block through the stateful RIC/READ dispatch."""
        read = bytearray(10)
        read[0] = 0x28
        put_be(read, 6, request, 3)
        while True:
            result, sense = self.scanner.command(
                "READ IMAGE", bytes(read), data_in_size=request
            )
            # Mercury API 0x8003; separate from immediate USB BUSY retries.
            if sense is not None and (sense.key, sense.asc, sense.ascq) == (3, 0x80, 0x13):
                time.sleep(0.01)
                continue
            break
        block = result.data
        page_end = False
        if sense is not None:
            if sense.key != 0:
                raise RuntimeError(f"READ IMAGE: {sense.describe()}")
            # NO SENSE residual applies without ILI; deliver only received bytes.
            if not 0 <= sense.information <= request:
                raise RuntimeError(f"READ IMAGE: invalid residual: {sense.describe()}")
            block = block[: request - sense.information]
            page_end = sense.eom
            self.report(f"image status: {sense.describe()}")
        if result.embedded_status:
            raise RuntimeError(
                "READ IMAGE received a status frame instead of image data "
                f"({result.transferred_size}/{request} bytes); page is incomplete"
            )
        if not block and not page_end:
            raise RuntimeError("READ IMAGE made no progress without an end-of-page status")
        if result.short_read:
            self.report(f"short image transfer: {result.transferred_size}/{request}")
        return block, page_end

    def scan_page(self) -> ScannedPage:
        if not self.initialized:
            raise RuntimeError("scan batch is not initialized")
        if not self._paper_ready:
            self._check_paper()
        self._paper_ready = False
        image = bytearray()
        try:
            # Arm cleanup before FEED, which may succeed before status I/O fails.
            self.acquisition_active = True
            self._transfer_started = True
            self.scanner.object_position(1, "FEED")
            self.scanner.checked("SCAN", bytes.fromhex("1B 00 00 00 01 00"), data_out=b"\0")
            dimensions = self._get_read_info()
            # READ80 +0 fixes the stream stride; +8 never changes it.
            wire_width = dimensions.window_width
            # A partial final mono byte still occupies one whole byte.
            wire_stride = (wire_width * self.settings.color_mode.bits_per_pixel + 7) // 8
            # Mercury raw worker FUN_1001a460 fits whole rows into its buffer.
            block_size = IMAGE_READ_BLOCK_SIZE // wire_stride * wire_stride
            if block_size == 0:
                raise RuntimeError("image row exceeds the image transfer buffer")
            # Initial window height bounds reading; effective height is not final.
            read_limit = wire_stride * dimensions.window_lines
            while len(image) < read_limit:
                request = min(block_size, read_limit - len(image))
                block, page_end = self._read_image_block(request)
                image.extend(block)
                self.report(
                    f"received: {len(image)}/{read_limit} bytes "
                    f"(device block {len(block)}/{request})"
                )
                if page_end:
                    break

            # fjtw32 FUN_100402e0 queries final size at EOM or the byte boundary.
            dimensions = self._get_read_info(report=False)
            if dimensions.window_width != wire_width:
                raise RuntimeError("READ INFO changed the stream width during a page")
            expected_size = wire_stride * dimensions.lines
            if len(image) < expected_size:
                raise RuntimeError(
                    "READ IMAGE ended before the complete final image: "
                    f"{len(image)}/{expected_size} bytes "
                    f"(final size {wire_width} x {dimensions.lines}, "
                    f"effective height available: {dimensions.effective_available})"
                )
            # Keep final-image bytes only; never fill missing image data.
            trailing_size = len(image) - expected_size
            if trailing_size:
                del image[expected_size:]
                self.report(f"discarded trailing image data: {trailing_size} bytes")
            height_source = "detected" if dimensions.effective_available else "window fallback"
            self.report(
                f"final image size: {wire_width} x {dimensions.lines} "
                f"({height_source}); {len(image)} {self.settings.color_mode.value} bytes"
            )
            if not image:
                raise RuntimeError("READ IMAGE ended before the first image row")
            # Page complete; retain the job until final ENDXFER/CANCEL.
            self.acquisition_active = False
            self.report("page complete")
        except BaseException:
            try:
                self.close()
            except Exception as cleanup_error:
                self.report(f"batch cleanup after scan error failed: {cleanup_error}")
            raise
        page = ScannedPage(
            pixels=transform_pixels(bytes(image)),
            width=dimensions.width,
            height=dimensions.lines,
            color_mode=self.settings.color_mode,
        )
        if self.settings.mode is ScanMode.SINGLE:
            self.close()
        return page

    def close(self) -> None:
        # Clear ownership first so a failed/interrupted cancellation is never
        # issued a second time by the surrounding context manager.
        if self._closed:
            return
        active = self.job_active
        transfer_started = self._transfer_started
        self.job_active = False
        self._transfer_started = False
        self.acquisition_active = False
        self.initialized = False
        self._paper_ready = False
        self._closed = True
        if active:
            self.scanner.finish_job(cancel=transfer_started)
            self.report("scan batch ended")


def find_port() -> tuple[dict[str, object], str]:
    if os.name != "nt":
        raise RuntimeError("the usbscan.sys backend is available only on Windows")
    from usbscan_device import find_ix100_driver

    driver = find_ix100_driver()
    port = str(driver.get("port") or "")
    for _ in range(40):
        if port.startswith(r"\\.\Usbscan"):
            return driver, port
        time.sleep(0.25)
        driver = find_ix100_driver()
        port = str(driver.get("port") or "")
    raise RuntimeError("the ScanSnap driver did not publish a usbscan port")


def _open_usbscan(stack: ExitStack) -> CommandTransport:
    driver, port = find_port()
    from transport_usbscan import UsbscanTransport

    transport = stack.enter_context(UsbscanTransport(port=port))
    transport.description = (
        f"{driver['friendly_name']} via Windows usbscan.sys at {port}"
    )
    return transport


@contextmanager
def open_transport(backend: str) -> Iterator[CommandTransport]:
    """Open one transport; auto fallback happens only during opening."""
    with ExitStack() as stack:
        if backend in ("auto", "libusb"):
            try:
                from transport_libusb import LibusbDeviceUnavailable, LibusbTransport
            except ModuleNotFoundError as error:
                # Only missing PyUSB permits fallback; other import defects fail.
                if (backend != "auto" or os.name != "nt"
                        or error.name not in ("usb", "usb.core", "usb.util")):
                    raise
                transport = _open_usbscan(stack)
            else:
                try:
                    transport = stack.enter_context(LibusbTransport())
                except LibusbDeviceUnavailable:
                    if backend == "libusb" or os.name != "nt":
                        raise
                    # Failed __enter__ cleans up itself; the stack is still empty.
                    transport = _open_usbscan(stack)
        elif backend == "usbscan":
            transport = _open_usbscan(stack)
        else:
            raise ValueError(f"unknown transport backend: {backend}")
        yield transport


@contextmanager
def open_scan_batch(
    backend: str,
    settings: ScanSettings,
    reporter: Reporter | None = None,
) -> Iterator[ScanBatch]:
    """Open one USB connection and initialize one reusable scan batch."""
    report = reporter or _ignore
    with open_transport(backend) as transport:
        report(f"device: {transport.description}")
        scanner = Scanner(transport, reporter=report)
        batch = ScanBatch(scanner, settings, reporter=report)
        try:
            batch.initialize()
            yield batch
        except BaseException:
            # Preserve the scan/caller error if batch cleanup also fails.
            try:
                batch.close()
            except Exception as cleanup_error:
                report(f"batch cleanup failed: {cleanup_error}")
            raise
        else:
            batch.close()
        finally:
            scanner.close()


def stop_scanner(backend: str, reporter: Reporter | None = None) -> None:
    report = reporter or _ignore
    with open_transport(backend) as transport:
        report(f"device: {transport.description}")
        scanner = Scanner(transport, reporter=report)
        try:
            scanner.finish_job(cancel=True)
        finally:
            scanner.close()
