from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from .errors import MetadataTaggerError

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_ALLOWED_REQUIRED_FIELDS = {"latitude", "longitude", "row", "panel"}
_ALLOWED_CAMERA_SOURCES = {"directory", "opencv", "lucid"}
_ALLOWED_TRIGGER_MODES = {"once", "interval", "file"}
_ALLOWED_OUTPUT_FORMATS = {"png", "jpg", "jpeg", "tif", "tiff", "bmp"}


@dataclass(frozen=True)
class GnssConfig:
    enabled: bool = True
    port: str = "auto"
    baudrate: int = 9600
    timeout_s: float = 1.0
    reconnect_delay_s: float = 2.0
    max_fix_age_s: float = 2.5
    future_tolerance_s: float = 0.25
    history_size: int = 256
    min_satellites: int = 4
    max_hdop: float = 5.0
    require_fix_quality: bool = True


@dataclass(frozen=True)
class StorageConfig:
    root: Path
    spool_dir: Path | None = None
    quarantine_on_missing_required: bool = True
    compute_sha256: bool = True
    validate_images: bool = True
    preserve_source: bool = True
    min_free_gb: float = 2.0
    emergency_free_gb: float = 0.5

    @property
    def effective_spool_dir(self) -> Path:
        return self.spool_dir or (self.root / "spool")


@dataclass(frozen=True)
class CameraConfig:
    source: Literal["directory", "opencv", "lucid"] = "directory"
    model: str = "LUCID Triton TRI050S-CC"
    serial_number: str | None = None
    output_format: str = "png"
    frame_timeout_ms: int = 5000
    reconnect_delay_s: float = 2.0

    # Simulated/directory source
    source_directory: Path | None = None
    directory_loop: bool = False

    # USB webcam/OpenCV source
    opencv_device: int | str = 0
    width: int | None = None
    height: int | None = None

    # LUCID Arena settings
    pixel_format: str = "BayerRG8"
    conversion_pixel_format: str = "BGR8"
    exposure_auto: str = "Continuous"
    exposure_us: float | None = None
    gain_auto: str = "Continuous"
    gain_db: float | None = None
    stream_packet_resend: bool = True
    stream_auto_packet_size: bool = True
    stream_buffer_count: int = 8
    device_link_throughput_reserve_percent: float = 10.0
    trigger_source: str = "Software"
    ptp_enable: bool = False
    chunk_mode_active: bool = True


@dataclass(frozen=True)
class CaptureConfig:
    trigger_mode: Literal["once", "interval", "file"] = "once"
    interval_s: float = 1.0
    max_images: int | None = None
    startup_delay_s: float = 0.0
    trigger_directory: Path | None = None
    trigger_poll_s: float = 0.2
    continue_on_error: bool = True
    health_interval_s: float = 5.0


@dataclass(frozen=True)
class HardwareConfig:
    edge_computer: str = "RUBIK Pi 3"
    storage_device: str = "WD Blue SN5000 500GB NVMe M.2 2280 SSD"
    lens: str = "LUCID / Universe UC080-5M / BL080C 8mm C-Mount 5MP 2/3-inch Lens"
    optical_filter: str = "Edmund Optics M22.5 x 0.50 Linear Glass Polarizing Filter"
    camera_enclosure: str = "LUCID IPTC-D355L399 IP67 C-Mount Lens Tube"
    gnss_receiver: str = "NaviSys GR-U01U USB GNSS Receiver"
    poe_injector: str = "Tycon Power TP-DCDC-1248GD-M"
    power_converter: str = "Coolgear ChargeIT Mini 82W CG-PD82HVV"
    camera_cable: str = "LUCID CAB-MR-2M M12 X-coded to RJ45 Cat6a"
    rubik_pi_ethernet_cable: str = "Short Shielded Cat6a RJ45 Patch Cable"
    fused_distribution_block: str = "Blue Sea Systems 5025 ST Blade Fuse Block (optional)"
    fuses: str = "Littelfuse ATO / ATOF Blade Fuses"
    robot_power_connector: str = "TE Connectivity / DEUTSCH DT 2-Pin Connector Set"
    main_power_wire: str = "18 AWG Stranded Red/Black Wire"
    branch_power_wire: str = "20-22 AWG Stranded Red/Black Wire"
    wiring_hardware: str = "Ferrules, Crimp Terminals, Heat Shrink, Labels, Strain Relief, and Wire Loom"

    def as_dict(self) -> dict[str, str]:
        return {
            "edge_computer": self.edge_computer,
            "storage_device": self.storage_device,
            "lens": self.lens,
            "optical_filter": self.optical_filter,
            "camera_enclosure": self.camera_enclosure,
            "gnss_receiver": self.gnss_receiver,
            "poe_injector": self.poe_injector,
            "power_converter": self.power_converter,
            "camera_cable": self.camera_cable,
            "rubik_pi_ethernet_cable": self.rubik_pi_ethernet_cable,
            "fused_distribution_block": self.fused_distribution_block,
            "fuses": self.fuses,
            "robot_power_connector": self.robot_power_connector,
            "main_power_wire": self.main_power_wire,
            "branch_power_wire": self.branch_power_wire,
            "wiring_hardware": self.wiring_hardware,
        }


@dataclass(frozen=True)
class TaggerConfig:
    robot_id: str
    mission_id: str
    storage: StorageConfig
    gnss: GnssConfig = field(default_factory=GnssConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    layout_file: Path | None = None
    required_fields: tuple[str, ...] = ("latitude", "longitude", "row", "panel")
    log_level: str = "INFO"
    config_path: Path | None = None

    @property
    def camera_model(self) -> str:
        return self.camera.model

    @classmethod
    def from_file(cls, path: str | Path) -> "TaggerConfig":
        config_path = Path(path).expanduser().resolve()
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise MetadataTaggerError(
                "CONFIG_NOT_FOUND", "Configuration file was not found.", path=str(config_path)
            ) from exc
        except json.JSONDecodeError as exc:
            raise MetadataTaggerError(
                "CONFIG_INVALID_JSON",
                "Configuration file is not valid JSON.",
                path=str(config_path),
                line=exc.lineno,
                column=exc.colno,
            ) from exc

        if not isinstance(raw, dict):
            raise MetadataTaggerError("CONFIG_INVALID", "Configuration root must be an object.")

        robot_id = _validated_id(raw.get("robot_id"), "robot_id")
        mission_id = _validated_id(raw.get("mission_id"), "mission_id")

        storage_raw = _object(raw.get("storage", {}), "storage")
        storage_root_value = storage_raw.get("root")
        if not storage_root_value:
            raise MetadataTaggerError("CONFIG_INVALID", "storage.root is required.")
        storage_root = _resolve_relative(config_path, storage_root_value)
        spool_value = storage_raw.get("spool_dir", str(storage_root / "spool"))
        spool_dir = _resolve_relative(config_path, spool_value)
        storage = StorageConfig(
            root=storage_root,
            spool_dir=spool_dir,
            quarantine_on_missing_required=_bool(
                storage_raw.get("quarantine_on_missing_required", True),
                "storage.quarantine_on_missing_required",
            ),
            compute_sha256=_bool(storage_raw.get("compute_sha256", True), "storage.compute_sha256"),
            validate_images=_bool(storage_raw.get("validate_images", True), "storage.validate_images"),
            preserve_source=_bool(storage_raw.get("preserve_source", True), "storage.preserve_source"),
            min_free_gb=float(storage_raw.get("min_free_gb", 2.0)),
            emergency_free_gb=float(storage_raw.get("emergency_free_gb", 0.5)),
        )
        if storage.min_free_gb < 0 or storage.emergency_free_gb < 0:
            raise MetadataTaggerError("CONFIG_INVALID", "Storage free-space limits cannot be negative.")
        if storage.emergency_free_gb > storage.min_free_gb:
            raise MetadataTaggerError(
                "CONFIG_INVALID", "storage.emergency_free_gb cannot exceed storage.min_free_gb."
            )

        gnss_raw = _object(raw.get("gnss", {}), "gnss")
        gnss = GnssConfig(
            enabled=_bool(gnss_raw.get("enabled", True), "gnss.enabled"),
            port=str(gnss_raw.get("port", "auto")),
            baudrate=int(gnss_raw.get("baudrate", 9600)),
            timeout_s=float(gnss_raw.get("timeout_s", 1.0)),
            reconnect_delay_s=float(gnss_raw.get("reconnect_delay_s", 2.0)),
            max_fix_age_s=float(gnss_raw.get("max_fix_age_s", 2.5)),
            future_tolerance_s=float(gnss_raw.get("future_tolerance_s", 0.25)),
            history_size=int(gnss_raw.get("history_size", 256)),
            min_satellites=int(gnss_raw.get("min_satellites", 4)),
            max_hdop=float(gnss_raw.get("max_hdop", 5.0)),
            require_fix_quality=_bool(
                gnss_raw.get("require_fix_quality", True), "gnss.require_fix_quality"
            ),
        )
        if (
            gnss.baudrate <= 0
            or gnss.timeout_s <= 0
            or gnss.reconnect_delay_s < 0
            or gnss.max_fix_age_s <= 0
            or gnss.future_tolerance_s < 0
            or gnss.history_size < 1
            or gnss.min_satellites < 0
            or gnss.max_hdop <= 0
        ):
            raise MetadataTaggerError("CONFIG_INVALID", "One or more GNSS settings are invalid.")

        camera_raw = _object(raw.get("camera", {}), "camera")
        # Backward compatibility with the original config.
        legacy_camera_model = raw.get("camera_model")
        source = str(camera_raw.get("source", "directory")).lower()
        if source not in _ALLOWED_CAMERA_SOURCES:
            raise MetadataTaggerError(
                "CONFIG_INVALID", "camera.source is unsupported.", supported=sorted(_ALLOWED_CAMERA_SOURCES)
            )
        output_format = str(camera_raw.get("output_format", "png")).lower().lstrip(".")
        if output_format not in _ALLOWED_OUTPUT_FORMATS:
            raise MetadataTaggerError(
                "CONFIG_INVALID",
                "camera.output_format is unsupported.",
                supported=sorted(_ALLOWED_OUTPUT_FORMATS),
            )
        source_directory = (
            _resolve_relative(config_path, camera_raw["source_directory"])
            if camera_raw.get("source_directory")
            else None
        )
        opencv_device: int | str = camera_raw.get("opencv_device", 0)
        if isinstance(opencv_device, str) and opencv_device.isdigit():
            opencv_device = int(opencv_device)
        camera = CameraConfig(
            source=source,  # type: ignore[arg-type]
            model=str(camera_raw.get("model", legacy_camera_model or "LUCID Triton TRI050S-CC")),
            serial_number=_optional_str(camera_raw.get("serial_number")),
            output_format=output_format,
            frame_timeout_ms=int(camera_raw.get("frame_timeout_ms", 5000)),
            reconnect_delay_s=float(camera_raw.get("reconnect_delay_s", 2.0)),
            source_directory=source_directory,
            directory_loop=_bool(camera_raw.get("directory_loop", False), "camera.directory_loop"),
            opencv_device=opencv_device,
            width=_optional_positive_int(camera_raw.get("width"), "camera.width"),
            height=_optional_positive_int(camera_raw.get("height"), "camera.height"),
            pixel_format=str(camera_raw.get("pixel_format", "BayerRG8")),
            conversion_pixel_format=str(camera_raw.get("conversion_pixel_format", "BGR8")),
            exposure_auto=str(camera_raw.get("exposure_auto", "Continuous")),
            exposure_us=_optional_float(camera_raw.get("exposure_us"), "camera.exposure_us"),
            gain_auto=str(camera_raw.get("gain_auto", "Continuous")),
            gain_db=_optional_float(camera_raw.get("gain_db"), "camera.gain_db"),
            stream_packet_resend=_bool(
                camera_raw.get("stream_packet_resend", True), "camera.stream_packet_resend"
            ),
            stream_auto_packet_size=_bool(
                camera_raw.get("stream_auto_packet_size", True), "camera.stream_auto_packet_size"
            ),
            stream_buffer_count=int(camera_raw.get("stream_buffer_count", 8)),
            device_link_throughput_reserve_percent=float(
                camera_raw.get("device_link_throughput_reserve_percent", 10.0)
            ),
            trigger_source=str(camera_raw.get("trigger_source", "Software")),
            ptp_enable=_bool(camera_raw.get("ptp_enable", False), "camera.ptp_enable"),
            chunk_mode_active=_bool(camera_raw.get("chunk_mode_active", True), "camera.chunk_mode_active"),
        )
        if camera.frame_timeout_ms <= 0 or camera.reconnect_delay_s < 0 or camera.stream_buffer_count < 2:
            raise MetadataTaggerError("CONFIG_INVALID", "One or more camera timing/buffer settings are invalid.")
        if not 0 <= camera.device_link_throughput_reserve_percent <= 100:
            raise MetadataTaggerError(
                "CONFIG_INVALID", "camera.device_link_throughput_reserve_percent must be 0-100."
            )
        if camera.source == "directory" and camera.source_directory is None:
            raise MetadataTaggerError(
                "CONFIG_INVALID", "camera.source_directory is required for the directory source."
            )

        capture_raw = _object(raw.get("capture", {}), "capture")
        trigger_mode = str(capture_raw.get("trigger_mode", "once")).lower()
        if trigger_mode not in _ALLOWED_TRIGGER_MODES:
            raise MetadataTaggerError(
                "CONFIG_INVALID",
                "capture.trigger_mode is unsupported.",
                supported=sorted(_ALLOWED_TRIGGER_MODES),
            )
        trigger_directory = (
            _resolve_relative(config_path, capture_raw["trigger_directory"])
            if capture_raw.get("trigger_directory")
            else storage_root / "triggers"
        )
        capture = CaptureConfig(
            trigger_mode=trigger_mode,  # type: ignore[arg-type]
            interval_s=float(capture_raw.get("interval_s", 1.0)),
            max_images=_optional_positive_int(capture_raw.get("max_images"), "capture.max_images"),
            startup_delay_s=float(capture_raw.get("startup_delay_s", 0.0)),
            trigger_directory=trigger_directory,
            trigger_poll_s=float(capture_raw.get("trigger_poll_s", 0.2)),
            continue_on_error=_bool(
                capture_raw.get("continue_on_error", True), "capture.continue_on_error"
            ),
            health_interval_s=float(capture_raw.get("health_interval_s", 5.0)),
        )
        if (
            capture.interval_s <= 0
            or capture.startup_delay_s < 0
            or capture.trigger_poll_s <= 0
            or capture.health_interval_s <= 0
        ):
            raise MetadataTaggerError("CONFIG_INVALID", "One or more capture timing settings are invalid.")

        hardware_raw = _object(raw.get("hardware", {}), "hardware")
        defaults = HardwareConfig()
        hardware = HardwareConfig(
            edge_computer=str(hardware_raw.get("edge_computer", defaults.edge_computer)),
            storage_device=str(hardware_raw.get("storage_device", defaults.storage_device)),
            lens=str(hardware_raw.get("lens", defaults.lens)),
            optical_filter=str(hardware_raw.get("optical_filter", defaults.optical_filter)),
            camera_enclosure=str(hardware_raw.get("camera_enclosure", defaults.camera_enclosure)),
            gnss_receiver=str(hardware_raw.get("gnss_receiver", defaults.gnss_receiver)),
            poe_injector=str(hardware_raw.get("poe_injector", defaults.poe_injector)),
            power_converter=str(hardware_raw.get("power_converter", defaults.power_converter)),
            camera_cable=str(hardware_raw.get("camera_cable", defaults.camera_cable)),
            rubik_pi_ethernet_cable=str(hardware_raw.get("rubik_pi_ethernet_cable", defaults.rubik_pi_ethernet_cable)),
            fused_distribution_block=str(hardware_raw.get("fused_distribution_block", defaults.fused_distribution_block)),
            fuses=str(hardware_raw.get("fuses", defaults.fuses)),
            robot_power_connector=str(hardware_raw.get("robot_power_connector", defaults.robot_power_connector)),
            main_power_wire=str(hardware_raw.get("main_power_wire", defaults.main_power_wire)),
            branch_power_wire=str(hardware_raw.get("branch_power_wire", defaults.branch_power_wire)),
            wiring_hardware=str(hardware_raw.get("wiring_hardware", defaults.wiring_hardware)),
        )

        layout_value = raw.get("layout_file")
        layout_file = _resolve_relative(config_path, layout_value) if layout_value else None
        if layout_file is not None and not layout_file.is_file():
            raise MetadataTaggerError(
                "LAYOUT_NOT_FOUND", "Configured layout file was not found.", path=str(layout_file)
            )

        required_raw = raw.get("required_fields", ["latitude", "longitude", "row", "panel"])
        if not isinstance(required_raw, list) or not all(isinstance(x, str) for x in required_raw):
            raise MetadataTaggerError("CONFIG_INVALID", "required_fields must be a list of strings.")
        unknown = set(required_raw) - _ALLOWED_REQUIRED_FIELDS
        if unknown:
            raise MetadataTaggerError(
                "CONFIG_INVALID",
                "required_fields contains unsupported values.",
                unsupported=sorted(unknown),
            )

        log_level = str(raw.get("log_level", "INFO")).upper()
        if log_level not in logging._nameToLevel:  # noqa: SLF001 - validation only
            raise MetadataTaggerError("CONFIG_INVALID", "log_level is not a valid Python log level.")

        return cls(
            robot_id=robot_id,
            mission_id=mission_id,
            storage=storage,
            gnss=gnss,
            camera=camera,
            capture=capture,
            hardware=hardware,
            layout_file=layout_file,
            required_fields=tuple(required_raw),
            log_level=log_level,
            config_path=config_path,
        )


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MetadataTaggerError("CONFIG_INVALID", f"{name} must be an object.")
    return value


def _validated_id(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise MetadataTaggerError(
            "CONFIG_INVALID",
            f"{field_name} must be 1-64 characters using letters, numbers, '.', '_' or '-'.",
        )
    return value


def _resolve_relative(config_path: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise MetadataTaggerError("CONFIG_INVALID", "Path values must be non-empty strings.")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = config_path.parent / path
    return path.resolve()


def _bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise MetadataTaggerError("CONFIG_INVALID", f"{field_name} must be true or false.")
    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise MetadataTaggerError("CONFIG_INVALID", "Optional string values must be non-empty.")
    return value.strip()


def _optional_float(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    result = float(value)
    if result < 0:
        raise MetadataTaggerError("CONFIG_INVALID", f"{field_name} cannot be negative.")
    return result


def _optional_positive_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    result = int(value)
    if result <= 0:
        raise MetadataTaggerError("CONFIG_INVALID", f"{field_name} must be positive.")
    return result
