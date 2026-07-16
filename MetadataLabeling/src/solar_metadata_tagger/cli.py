from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from .camera import create_camera_source
from .config import TaggerConfig
from .errors import MetadataTaggerError
from .gnss import FixHistoryStore, SerialGnssReader
from .health import HealthReporter
from .logging_utils import configure_logging
from .mission import MissionStats, summarize_manifest
from .models import GnssFix, utc_iso
from .runner import CaptureService
from .service import MetadataTaggingService
from .storage import disk_usage, write_json_atomic
from .version import __version__

LOGGER = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    debug = bool(getattr(args, "debug", False))
    try:
        config = TaggerConfig.from_file(args.config)
        configure_logging(
            config.storage.root / "logs",
            config.log_level,
            console=args.command == "run-service",
        )

        if args.command == "validate-config":
            _print_json(_config_summary(config))
            return 0
        if args.command == "tag":
            return _tag_one(config, args)
        if args.command == "gnss-monitor":
            return _monitor_gnss(config, args.seconds)
        if args.command == "camera-test":
            return _camera_test(config, args)
        if args.command == "run-service":
            return CaptureService(config).run()
        if args.command == "health-check":
            return _health_check(config)
        if args.command == "mission-summary":
            manifest = config.storage.root / "manifests" / f"{config.mission_id}.jsonl"
            _print_json(summarize_manifest(manifest))
            return 0
        if args.command == "create-trigger":
            return _create_trigger(config, args)
        parser.error("Unknown command")
    except MetadataTaggerError as exc:
        LOGGER.error("Command failed", extra={"event": "command_failed", **exc.as_log_extra()})
        _print_json(exc.as_dict(), stream=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # stable CLI boundary for field operation
        LOGGER.exception("Unexpected command failure", extra={"event": "unexpected_command_failure"})
        payload = {
            "error_code": "UNEXPECTED_ERROR",
            "message": "An unexpected error occurred. See the structured log for details.",
            "context": {"exception_type": type(exc).__name__, "detail": str(exc)},
        }
        if debug:
            payload["traceback"] = traceback.format_exc()
        _print_json(payload, stream=sys.stderr)
        return 3
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="solar-tagger",
        description="Sunnybotics image capture, GNSS matching, and metadata service.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--debug", action="store_true", help="Include tracebacks for unexpected errors.")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-config", help="Validate and summarize a configuration file.")
    validate.add_argument("--config", required=True)

    tag = sub.add_parser("tag", help="Tag one existing image with manual or live GNSS metadata.")
    tag.add_argument("--config", required=True)
    tag.add_argument("--image", required=True)
    tag.add_argument("--captured-at", help="ISO-8601 timestamp; defaults to current UTC time.")
    tag.add_argument("--latitude", type=float)
    tag.add_argument("--longitude", type=float)
    tag.add_argument("--altitude-m", type=float)
    tag.add_argument("--satellites", type=int)
    tag.add_argument("--hdop", type=float)
    tag.add_argument("--fix-quality", type=int, default=1)
    tag.add_argument("--row")
    tag.add_argument("--panel")

    monitor = sub.add_parser("gnss-monitor", help="Read and print NaviSys USB GNSS fixes.")
    monitor.add_argument("--config", required=True)
    monitor.add_argument("--seconds", type=float, default=30.0)

    camera_test = sub.add_parser("camera-test", help="Open the configured camera and capture one test frame.")
    camera_test.add_argument("--config", required=True)
    camera_test.add_argument("--tag", action="store_true", help="Also pass the test frame through the tagger.")
    camera_test.add_argument("--latitude", type=float)
    camera_test.add_argument("--longitude", type=float)
    camera_test.add_argument("--altitude-m", type=float)
    camera_test.add_argument("--row")
    camera_test.add_argument("--panel")

    run = sub.add_parser("run-service", help="Run the unattended capture service.")
    run.add_argument("--config", required=True)

    health = sub.add_parser("health-check", help="Check configuration, storage, camera, and GNSS visibility.")
    health.add_argument("--config", required=True)

    summary = sub.add_parser("mission-summary", help="Summarize the current mission manifest.")
    summary.add_argument("--config", required=True)

    trigger = sub.add_parser("create-trigger", help="Create a mission-point trigger JSON for file-trigger mode.")
    trigger.add_argument("--config", required=True)
    trigger.add_argument("--trigger-id")
    trigger.add_argument("--mission-point-id")
    trigger.add_argument("--row")
    trigger.add_argument("--panel")
    return parser


def _tag_one(config: TaggerConfig, args: argparse.Namespace) -> int:
    service = MetadataTaggingService(config)
    captured = _parse_datetime(args.captured_at) if args.captured_at else datetime.now(timezone.utc)
    manual_fix = _manual_fix(args, captured)
    result = service.tag_image(
        args.image,
        captured_at_utc=captured,
        manual_fix=manual_fix,
        row=args.row,
        panel=args.panel,
        camera_metadata={"source": "manual-cli", "model": config.camera.model},
        trigger_metadata={"source": "manual-cli"},
    )
    _print_json(result.as_dict())
    return 0


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise MetadataTaggerError(
            "TIMESTAMP_INVALID", "Timestamp must be valid ISO-8601, for example 2026-07-16T12:00:00Z."
        ) from exc
    if parsed.tzinfo is None:
        raise MetadataTaggerError("TIMESTAMP_INVALID", "Timestamp must include a timezone.")
    return parsed.astimezone(timezone.utc)


def _manual_fix(args: argparse.Namespace, captured: datetime) -> GnssFix | None:
    latitude = getattr(args, "latitude", None)
    longitude = getattr(args, "longitude", None)
    if latitude is None and longitude is None:
        return None
    if latitude is None or longitude is None:
        raise MetadataTaggerError(
            "COORDINATES_INCOMPLETE", "Both --latitude and --longitude are required together."
        )
    return GnssFix(
        latitude=latitude,
        longitude=longitude,
        altitude_m=getattr(args, "altitude_m", None),
        received_at_utc=captured,
        fix_time_utc=captured,
        fix_quality=getattr(args, "fix_quality", 1),
        satellites=getattr(args, "satellites", None),
        hdop=getattr(args, "hdop", None),
        source_sentence="manual-cli",
    )


def _monitor_gnss(config: TaggerConfig, seconds: float) -> int:
    if seconds <= 0:
        raise MetadataTaggerError("ARGUMENT_INVALID", "--seconds must be positive.")
    if not config.gnss.enabled:
        raise MetadataTaggerError("GNSS_DISABLED", "GNSS is disabled in the configuration.")
    store = FixHistoryStore(config.gnss.history_size)
    reader = SerialGnssReader(
        store,
        port=config.gnss.port,
        baudrate=config.gnss.baudrate,
        timeout_s=config.gnss.timeout_s,
        reconnect_delay_s=config.gnss.reconnect_delay_s,
    )
    reader.start()
    deadline = time.monotonic() + seconds
    last_received = None
    try:
        while time.monotonic() < deadline:
            fix = store.snapshot()
            if fix and fix.received_at_utc != last_received:
                last_received = fix.received_at_utc
                _print_json(
                    {
                        "latitude": fix.latitude,
                        "longitude": fix.longitude,
                        "altitude_m": fix.altitude_m,
                        "fix_quality": fix.fix_quality,
                        "satellites": fix.satellites,
                        "hdop": fix.hdop,
                        "coordinates_valid": fix.coordinates_valid,
                        "received_at_utc": utc_iso(fix.received_at_utc),
                        "port": reader.resolved_port,
                    },
                    compact=True,
                )
            time.sleep(0.1)
    finally:
        reader.stop()
    if store.snapshot() is None:
        raise reader.last_error or MetadataTaggerError(
            "GNSS_NO_FIX", "No valid GNSS fix was received during the monitoring period."
        )
    return 0


def _camera_test(config: TaggerConfig, args: argparse.Namespace) -> int:
    camera = create_camera_source(config.camera)
    try:
        camera.open()
        frame = camera.capture(config.storage.effective_spool_dir)
        payload: dict[str, object] = {
            "captured": True,
            "image_path": str(frame.image_path),
            "captured_at_utc": utc_iso(frame.captured_at_utc),
            "camera": frame.camera_metadata,
            "health": camera.health(),
        }
        if args.tag:
            fix = _manual_fix(args, frame.captured_at_utc)
            result = MetadataTaggingService(config).tag_image(
                frame.image_path,
                captured_at_utc=frame.captured_at_utc,
                captured_monotonic_ns=frame.monotonic_ns,
                manual_fix=fix,
                row=args.row,
                panel=args.panel,
                camera_metadata=frame.camera_metadata,
                trigger_metadata={"source": "camera-test"},
            )
            payload["tag_result"] = result.as_dict()
        _print_json(payload)
        return 0
    finally:
        camera.close()


def _health_check(config: TaggerConfig) -> int:
    checks: dict[str, object] = {
        "timestamp_utc": utc_iso(datetime.now(timezone.utc)),
        "configuration": "valid",
        "storage": disk_usage(config.storage.root),
        "camera": {"status": "not-tested"},
        "gnss": {"enabled": config.gnss.enabled, "status": "not-tested"},
    }
    camera = create_camera_source(config.camera)
    try:
        camera.open()
        checks["camera"] = {"status": "ok", **camera.health()}
    except MetadataTaggerError as exc:
        checks["camera"] = {"status": "error", **exc.as_dict()}
    finally:
        camera.close()
    if config.gnss.enabled:
        from .gnss import discover_serial_port

        try:
            checks["gnss"] = {"enabled": True, "status": "device-visible", "port": discover_serial_port(config.gnss.port)}
        except MetadataTaggerError as exc:
            checks["gnss"] = {"enabled": True, "status": "error", **exc.as_dict()}
    destination = config.storage.root / "health" / "preflight.json"
    write_json_atomic(destination, checks)
    checks["report_path"] = str(destination)
    _print_json(checks)
    camera_ok = isinstance(checks["camera"], dict) and checks["camera"].get("status") == "ok"  # type: ignore[union-attr]
    gnss_ok = not config.gnss.enabled or (isinstance(checks["gnss"], dict) and checks["gnss"].get("status") == "device-visible")  # type: ignore[union-attr]
    return 0 if camera_ok and gnss_ok else 4


def _create_trigger(config: TaggerConfig, args: argparse.Namespace) -> int:
    import uuid

    if config.capture.trigger_mode != "file" or config.capture.trigger_directory is None:
        raise MetadataTaggerError(
            "TRIGGER_CONFIG_INVALID", "The configuration must use capture.trigger_mode='file'."
        )
    trigger_id = args.trigger_id or f"mission-point-{uuid.uuid4().hex[:12]}"
    payload = {
        "trigger_id": trigger_id,
        "requested_at_utc": utc_iso(datetime.now(timezone.utc)),
        "mission_point_id": args.mission_point_id,
        "row": args.row,
        "panel": args.panel,
    }
    destination = config.capture.trigger_directory / "incoming" / f"{trigger_id}.json"
    write_json_atomic(destination, payload)
    _print_json({"created": str(destination), "trigger": payload})
    return 0


def _config_summary(config: TaggerConfig) -> dict[str, object]:
    return {
        "valid": True,
        "software_version": __version__,
        "robot_id": config.robot_id,
        "mission_id": config.mission_id,
        "storage": {
            "root": str(config.storage.root),
            "spool_dir": str(config.storage.effective_spool_dir),
            "validate_images": config.storage.validate_images,
            "min_free_gb": config.storage.min_free_gb,
        },
        "camera": {
            "source": config.camera.source,
            "model": config.camera.model,
            "serial_number": config.camera.serial_number,
            "output_format": config.camera.output_format,
        },
        "capture": {
            "trigger_mode": config.capture.trigger_mode,
            "trigger_directory": str(config.capture.trigger_directory)
            if config.capture.trigger_directory
            else None,
            "max_images": config.capture.max_images,
        },
        "gnss": {
            "enabled": config.gnss.enabled,
            "port": config.gnss.port,
            "baudrate": config.gnss.baudrate,
            "max_fix_age_s": config.gnss.max_fix_age_s,
            "future_tolerance_s": config.gnss.future_tolerance_s,
        },
        "layout_file": str(config.layout_file) if config.layout_file else None,
        "required_fields": list(config.required_fields),
        "hardware": config.hardware.as_dict(),
    }


def _print_json(payload: object, *, stream: object = sys.stdout, compact: bool = False) -> None:
    print(
        json.dumps(payload, ensure_ascii=False, indent=None if compact else 2, default=str),
        file=stream,
        flush=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
