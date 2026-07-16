from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import CameraConfig
from ..errors import MetadataTaggerError
from ..models import CapturedFrame

LOGGER = logging.getLogger(__name__)


class LucidArenaCameraSource:
    """LUCID Triton TRI050S-CC adapter using Arena SDK's Python package.

    The SDK itself is installed separately because LUCID distributes it outside PyPI.
    This adapter uses software-triggered single frames so robot mission logic can decide
    exactly when an image is captured.
    """

    def __init__(self, config: CameraConfig) -> None:
        self.config = config
        self._system: Any = None
        self._device: Any = None
        self._buffer_factory: Any = None
        self._writer_cls: Any = None
        self._pixel_format_enum: Any = None
        self._sequence = 0
        self._device_metadata: dict[str, Any] = {}

    def open(self) -> None:
        try:
            from arena_api.__future__.save import Writer
            from arena_api.buffer import BufferFactory
            from arena_api.enums import PixelFormat
            from arena_api.system import system
        except ImportError as exc:
            raise MetadataTaggerError(
                "ARENA_SDK_MISSING",
                "LUCID Arena SDK and arena_api Python package are required for camera.source='lucid'.",
                detail=str(exc),
            ) from exc

        devices = system.create_device()
        if not devices:
            raise MetadataTaggerError(
                "CAMERA_NOT_FOUND",
                "Arena SDK did not discover a LUCID camera. Check PoE, Ethernet, IP addressing, and firewall settings.",
            )
        try:
            device = self._select_device(devices)
        except Exception:
            try:
                system.destroy_device()
            except Exception:
                pass
            raise
        try:
            self._configure_device(device)
            device.start_stream()
        except Exception as exc:
            try:
                system.destroy_device(device)
            except Exception:
                pass
            raise MetadataTaggerError(
                "CAMERA_CONFIGURE_FAILED",
                "LUCID camera could not be configured or streamed.",
                detail=str(exc),
                exception_type=type(exc).__name__,
            ) from exc

        self._system = system
        self._device = device
        self._buffer_factory = BufferFactory
        self._writer_cls = Writer
        self._pixel_format_enum = PixelFormat
        self._device_metadata = self._read_device_metadata(device)
        LOGGER.info(
            "LUCID camera opened",
            extra={"event": "camera_open", **self._device_metadata},
        )

    def capture(self, spool_dir: Path) -> CapturedFrame:
        if self._device is None:
            raise MetadataTaggerError("CAMERA_NOT_OPEN", "LUCID camera is not open.")
        device = self._device
        buffer = None
        converted = None
        try:
            command_at = datetime.now(timezone.utc)
            command_monotonic_ns = time.monotonic_ns()
            if self.config.trigger_source == "Software":
                _wait_until_trigger_armed(device.nodemap, self.config.frame_timeout_ms)
                command_at = datetime.now(timezone.utc)
                command_monotonic_ns = time.monotonic_ns()
                _execute_node(device.nodemap, "TriggerSoftware")
            buffer = device.get_buffer(self.config.frame_timeout_ms)
            buffer_received_at = datetime.now(timezone.utc)
            buffer_received_monotonic_ns = time.monotonic_ns()
            captured_at = command_at if self.config.trigger_source == "Software" else buffer_received_at
            monotonic_ns = command_monotonic_ns if self.config.trigger_source == "Software" else buffer_received_monotonic_ns
            converted_format = getattr(
                self._pixel_format_enum, self.config.conversion_pixel_format, None
            )
            if converted_format is None:
                raise MetadataTaggerError(
                    "CAMERA_PIXEL_FORMAT_INVALID",
                    "Configured Arena conversion pixel format does not exist.",
                    pixel_format=self.config.conversion_pixel_format,
                )
            converted = self._buffer_factory.convert(buffer, converted_format)
            extension = _extension(self.config.output_format)
            spool_dir.mkdir(parents=True, exist_ok=True)
            path = spool_dir / (
                f"lucid-{captured_at.strftime('%Y%m%dT%H%M%S.%fZ')}-{self._sequence:06d}{extension}"
            )
            writer = self._writer_cls()
            writer.pattern = str(path)
            writer.save(converted)
            metadata = {
                **self._device_metadata,
                "source": "lucid-arena-sdk",
                "sequence_index": self._sequence,
                "width_px": int(getattr(buffer, "width", 0) or 0),
                "height_px": int(getattr(buffer, "height", 0) or 0),
                "frame_id": _optional_int(getattr(buffer, "frame_id", None)),
                "camera_timestamp_ns": _optional_int(
                    getattr(buffer, "timestamp_ns", getattr(buffer, "timestamp", None))
                ),
                "pixel_format": _node_value(device.nodemap, "PixelFormat"),
                "exposure_us": _optional_float(_node_value(device.nodemap, "ExposureTime")),
                "gain_db": _optional_float(_node_value(device.nodemap, "Gain")),
                "ptp_enabled": _node_value(device.nodemap, "PtpEnable"),
                "ptp_status": _node_value(device.nodemap, "PtpStatus"),
                "chunk_mode_active": _node_value(device.nodemap, "ChunkModeActive"),
                "capture_command_at_utc": command_at.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "buffer_received_at_utc": buffer_received_at.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "trigger_to_buffer_ms": round((buffer_received_monotonic_ns - command_monotonic_ns) / 1_000_000, 3),
                "arena_capture_timeout_ms": self.config.frame_timeout_ms,
            }
            self._sequence += 1
            return CapturedFrame(
                image_path=path,
                captured_at_utc=captured_at,
                monotonic_ns=monotonic_ns,
                camera_metadata=metadata,
            )
        except MetadataTaggerError:
            raise
        except Exception as exc:
            raise MetadataTaggerError(
                "CAMERA_CAPTURE_FAILED",
                "LUCID Arena capture failed.",
                detail=str(exc),
                exception_type=type(exc).__name__,
            ) from exc
        finally:
            if converted is not None:
                try:
                    self._buffer_factory.destroy(converted)
                except Exception:
                    LOGGER.exception("Failed to destroy converted Arena buffer")
            if buffer is not None:
                try:
                    device.requeue_buffer(buffer)
                except Exception:
                    LOGGER.exception("Failed to requeue Arena buffer")

    def close(self) -> None:
        if self._device is None:
            return
        try:
            self._device.stop_stream()
        except Exception:
            LOGGER.exception("Failed to stop LUCID stream", extra={"event": "camera_stop_failed"})
        try:
            self._system.destroy_device(self._device)
        except Exception:
            LOGGER.exception("Failed to destroy LUCID device", extra={"event": "camera_destroy_failed"})
        finally:
            self._device = None
            self._system = None

    def health(self) -> dict[str, object]:
        return {
            "source": "lucid",
            "open": self._device is not None,
            "frames_captured": self._sequence,
            **self._device_metadata,
        }

    def _select_device(self, devices: list[Any]) -> Any:
        if not self.config.serial_number:
            if len(devices) > 1:
                LOGGER.warning(
                    "Multiple LUCID cameras found; selecting the first because no serial_number is configured",
                    extra={"event": "camera_multiple_devices", "count": len(devices)},
                )
            return devices[0]
        for device in devices:
            serial = str(_node_value(device.nodemap, "DeviceSerialNumber") or "")
            if serial == self.config.serial_number:
                return device
        raise MetadataTaggerError(
            "CAMERA_SERIAL_NOT_FOUND",
            "Configured LUCID camera serial number was not discovered.",
            serial_number=self.config.serial_number,
        )

    def _configure_device(self, device: Any) -> None:
        nodemap = device.nodemap
        stream = device.tl_stream_nodemap
        _set_node(stream, "StreamAutoNegotiatePacketSize", self.config.stream_auto_packet_size)
        _set_node(stream, "StreamPacketResendEnable", self.config.stream_packet_resend)
        _set_node(stream, "StreamBufferHandlingMode", "NewestOnly")
        _set_node(stream, "StreamBufferCountMode", "Manual")
        _set_node(stream, "StreamBufferCountManual", self.config.stream_buffer_count)

        _set_node(nodemap, "AcquisitionMode", "Continuous")
        _set_node(nodemap, "PtpEnable", self.config.ptp_enable)
        _set_node(nodemap, "ChunkModeActive", self.config.chunk_mode_active)
        _set_node(nodemap, "PixelFormat", self.config.pixel_format)
        _set_node(
            nodemap,
            "DeviceLinkThroughputReserve",
            self.config.device_link_throughput_reserve_percent,
        )
        _set_node(nodemap, "TriggerSelector", "FrameStart")
        _set_node(nodemap, "TriggerMode", "On")
        _set_node(nodemap, "TriggerSource", self.config.trigger_source)

        if self.config.exposure_us is not None:
            _set_node(nodemap, "ExposureAuto", "Off")
            _set_numeric_clamped(nodemap, "ExposureTime", self.config.exposure_us)
        else:
            _set_node(nodemap, "ExposureAuto", self.config.exposure_auto)
        if self.config.gain_db is not None:
            _set_node(nodemap, "GainAuto", "Off")
            _set_numeric_clamped(nodemap, "Gain", self.config.gain_db)
        else:
            _set_node(nodemap, "GainAuto", self.config.gain_auto)

    def _read_device_metadata(self, device: Any) -> dict[str, Any]:
        nodemap = device.nodemap
        return {
            "vendor": _node_value(nodemap, "DeviceVendorName") or "LUCID Vision Labs",
            "model": _node_value(nodemap, "DeviceModelName") or self.config.model,
            "serial_number": _node_value(nodemap, "DeviceSerialNumber"),
            "firmware_version": _node_value(nodemap, "DeviceFirmwareVersion"),
            "device_version": _node_value(nodemap, "DeviceVersion"),
            "transport": "GigE Vision",
            "power": "PoE through Tycon TP-DCDC-1248GD-M",
        }


def _node(nodemap: Any, name: str) -> Any | None:
    try:
        return nodemap[name]
    except Exception:
        return None


def _node_value(nodemap: Any, name: str) -> Any:
    node = _node(nodemap, name)
    if node is None:
        return None
    try:
        return node.value
    except Exception:
        return None


def _set_node(nodemap: Any, name: str, value: Any) -> bool:
    node = _node(nodemap, name)
    if node is None:
        return False
    try:
        node.value = value
        return True
    except Exception:
        LOGGER.debug("Arena node could not be set", extra={"event": "camera_node_skipped", "node": name})
        return False


def _set_numeric_clamped(nodemap: Any, name: str, value: float) -> bool:
    node = _node(nodemap, name)
    if node is None:
        return False
    try:
        minimum = float(getattr(node, "min", value))
        maximum = float(getattr(node, "max", value))
        node.value = min(max(float(value), minimum), maximum)
        return True
    except Exception:
        LOGGER.debug("Arena numeric node could not be set", extra={"event": "camera_node_skipped", "node": name})
        return False



def _wait_until_trigger_armed(nodemap: Any, timeout_ms: int) -> None:
    node = _node(nodemap, "TriggerArmed")
    if node is None:
        return
    deadline = time.monotonic() + max(timeout_ms / 1000.0, 0.1)
    while time.monotonic() < deadline:
        try:
            if bool(node.value):
                return
        except Exception:
            return
        time.sleep(0.001)
    raise MetadataTaggerError(
        "CAMERA_TRIGGER_NOT_ARMED",
        "LUCID camera did not become trigger-ready before the timeout.",
        timeout_ms=timeout_ms,
    )

def _execute_node(nodemap: Any, name: str) -> None:
    node = _node(nodemap, name)
    if node is None:
        raise MetadataTaggerError("CAMERA_TRIGGER_UNAVAILABLE", f"Arena node {name} is unavailable.")
    try:
        node.execute()
    except Exception as exc:
        raise MetadataTaggerError(
            "CAMERA_TRIGGER_FAILED", "LUCID software trigger failed.", detail=str(exc)
        ) from exc


def _extension(output_format: str) -> str:
    normalized = output_format.lower().lstrip(".")
    return ".jpg" if normalized == "jpeg" else f".{normalized}"


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
