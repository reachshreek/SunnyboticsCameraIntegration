from __future__ import annotations

from typing import Any


class MetadataTaggerError(Exception):
    """Base exception with a stable machine-readable error code."""

    def __init__(self, code: str, message: str, **context: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = context

    def as_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.code,
            "message": self.message,
            "context": self.context,
        }

    def as_log_extra(self) -> dict[str, Any]:
        """Logging-safe fields that do not collide with LogRecord attributes."""
        return {
            "error_code": self.code,
            "error_message": self.message,
            "error_context": self.context,
        }
