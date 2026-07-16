from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path


class JsonFormatter(logging.Formatter):
    _reserved = set(logging.makeLogRecord({}).__dict__.keys())

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in self._reserved and key not in {"message", "asctime"}:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def configure_logging(log_dir: Path, level: str = "INFO", *, console: bool = True) -> None:
    """Configure durable JSONL logging and optional human-readable console output."""
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    target = (log_dir / "tagger.jsonl").resolve()

    if not any(
        getattr(handler, "_solar_file", None) == str(target) for handler in root.handlers
    ):
        file_handler = RotatingFileHandler(
            target,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(JsonFormatter())
        file_handler._solar_file = str(target)  # type: ignore[attr-defined]
        root.addHandler(file_handler)

    solar_console_handlers = [
        handler for handler in root.handlers if getattr(handler, "_solar_console", False)
    ]
    if not console:
        for handler in solar_console_handlers:
            root.removeHandler(handler)
            handler.close()
        return
    has_console = bool(solar_console_handlers)
    if not has_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        console_handler._solar_console = True  # type: ignore[attr-defined]
        root.addHandler(console_handler)
