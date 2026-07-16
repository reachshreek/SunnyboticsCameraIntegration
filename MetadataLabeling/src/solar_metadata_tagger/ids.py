from __future__ import annotations

import uuid
from datetime import datetime, timezone


def generate_image_id(robot_id: str, mission_id: str, captured_at: datetime) -> str:
    """Create a sortable, collision-resistant image identifier.

    The timestamp makes IDs easy to inspect and sort. The UUID suffix prevents
    collisions when multiple images have the same timestamp or after a restart.
    """
    if captured_at.tzinfo is None:
        raise ValueError("captured_at must be timezone-aware")
    stamp = captured_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    return f"{robot_id}--{mission_id}--{stamp}--{uuid.uuid4().hex[:12]}"
