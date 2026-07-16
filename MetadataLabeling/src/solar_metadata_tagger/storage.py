from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .errors import MetadataTaggerError


def copy_image_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with source.open("rb") as src, tempfile.NamedTemporaryFile(
            mode="wb", dir=destination.parent, prefix=f".{destination.name}.", delete=False
        ) as tmp:
            temp_path = Path(tmp.name)
            shutil.copyfileobj(src, tmp, length=1024 * 1024)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(temp_path, destination)
        _fsync_directory(destination.parent)
    except OSError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise MetadataTaggerError(
            "IMAGE_WRITE_FAILED",
            "Image could not be copied to storage.",
            source=str(source),
            destination=str(destination),
            detail=str(exc),
        ) from exc


def write_json_atomic(destination: Path, payload: dict[str, Any]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            temp_path = Path(tmp.name)
            json.dump(payload, tmp, ensure_ascii=False, indent=2, sort_keys=True)
            tmp.write("\n")
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(temp_path, destination)
        _fsync_directory(destination.parent)
    except OSError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise MetadataTaggerError(
            "METADATA_WRITE_FAILED",
            "Metadata sidecar could not be written.",
            destination=str(destination),
            detail=str(exc),
        ) from exc


def append_jsonl(destination: Path, payload: dict[str, Any]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    try:
        with destination.open("a", encoding="utf-8") as handle:
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            except ImportError:
                pass
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except ImportError:
                pass
    except OSError as exc:
        raise MetadataTaggerError(
            "MANIFEST_WRITE_FAILED",
            "Mission manifest could not be updated.",
            destination=str(destination),
            detail=str(exc),
        ) from exc


def write_bytes_atomic(destination: Path, data: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=destination.parent, prefix=f".{destination.name}.", delete=False
        ) as tmp:
            temp_path = Path(tmp.name)
            tmp.write(data)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(temp_path, destination)
        _fsync_directory(destination.parent)
    except OSError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise MetadataTaggerError(
            "FILE_WRITE_FAILED", "File could not be written atomically.", path=str(destination), detail=str(exc)
        ) from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise MetadataTaggerError(
            "HASH_FAILED", "Image hash could not be calculated.", path=str(path), detail=str(exc)
        ) from exc
    return digest.hexdigest()


def disk_usage(path: Path) -> dict[str, int]:
    path.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(path)
    return {"total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free}


def ensure_free_space(path: Path, *, min_free_gb: float, emergency_free_gb: float) -> dict[str, int]:
    usage = disk_usage(path)
    free_gb = usage["free_bytes"] / (1024**3)
    if free_gb < emergency_free_gb:
        raise MetadataTaggerError(
            "STORAGE_EMERGENCY_LOW",
            "Storage is below the emergency free-space threshold; capture has stopped.",
            path=str(path),
            free_gb=round(free_gb, 3),
            emergency_free_gb=emergency_free_gb,
        )
    if free_gb < min_free_gb:
        raise MetadataTaggerError(
            "STORAGE_LOW",
            "Storage is below the configured free-space threshold.",
            path=str(path),
            free_gb=round(free_gb, 3),
            min_free_gb=min_free_gb,
        )
    return usage


def _fsync_directory(directory: Path) -> None:
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
