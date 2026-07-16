from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..models import CapturedFrame


class CameraSource(Protocol):
    def open(self) -> None: ...

    def capture(self, spool_dir: Path) -> CapturedFrame: ...

    def close(self) -> None: ...

    def health(self) -> dict[str, object]: ...
