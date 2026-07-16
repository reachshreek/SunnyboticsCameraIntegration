from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import TagResult, utc_iso
from .storage import write_json_atomic


@dataclass
class MissionStats:
    mission_id: str
    started_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    capture_attempts: int = 0
    completed: int = 0
    quarantined: int = 0
    partial: int = 0
    capture_failures: int = 0
    tagging_failures: int = 0
    last_image_id: str | None = None
    last_error: dict[str, Any] | None = None

    def record_result(self, result: TagResult) -> None:
        self.capture_attempts += 1
        self.last_image_id = result.image_id
        if result.status == "complete":
            self.completed += 1
        elif result.status == "quarantined":
            self.quarantined += 1
        else:
            self.partial += 1

    def record_capture_failure(self, error: dict[str, Any]) -> None:
        self.capture_attempts += 1
        self.capture_failures += 1
        self.last_error = error

    def record_tagging_failure(self, error: dict[str, Any]) -> None:
        self.capture_attempts += 1
        self.tagging_failures += 1
        self.last_error = error

    @property
    def metadata_complete_percent(self) -> float:
        successful_files = self.completed + self.quarantined + self.partial
        if successful_files == 0:
            return 0.0
        return round(100.0 * self.completed / successful_files, 2)

    def as_dict(self, *, final: bool = False) -> dict[str, Any]:
        ended = datetime.now(timezone.utc)
        return {
            "mission_id": self.mission_id,
            "started_at_utc": utc_iso(self.started_at_utc),
            "updated_at_utc": utc_iso(ended),
            "final": final,
            "capture_attempts": self.capture_attempts,
            "images_written": self.completed + self.quarantined + self.partial,
            "complete_metadata_images": self.completed,
            "quarantined_images": self.quarantined,
            "partial_images": self.partial,
            "capture_failures": self.capture_failures,
            "tagging_failures": self.tagging_failures,
            "metadata_complete_percent": self.metadata_complete_percent,
            "meets_95_percent_metadata_goal": self.metadata_complete_percent >= 95.0,
            "last_image_id": self.last_image_id,
            "last_error": self.last_error,
        }

    def write(self, root: Path, *, final: bool = False) -> Path:
        destination = root / "reports" / f"{self.mission_id}-summary.json"
        write_json_atomic(destination, self.as_dict(final=final))
        return destination


def summarize_manifest(manifest: Path) -> dict[str, Any]:
    counts = {"complete": 0, "quarantined": 0, "partial": 0, "other": 0}
    total = 0
    if manifest.is_file():
        for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                counts["other"] += 1
                continue
            total += 1
            status = payload.get("status")
            if status in counts:
                counts[status] += 1
            else:
                counts["other"] += 1
    complete_percent = round(100.0 * counts["complete"] / total, 2) if total else 0.0
    return {
        "manifest": str(manifest),
        "total": total,
        **counts,
        "metadata_complete_percent": complete_percent,
        "meets_95_percent_metadata_goal": complete_percent >= 95.0,
    }
