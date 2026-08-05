from __future__ import annotations

import argparse
import csv
import hashlib
import http.client
import json
import logging
import os
import platform
import shutil
import socket
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import quote, unquote, urlsplit


HERE = Path(__file__).resolve().parent
VALIDATION_ID = "P2-09"
LOGGER = logging.getLogger(VALIDATION_ID)
READ_CHUNK_BYTES = 1024 * 1024


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(
            lambda: file.read(READ_CHUNK_BYTES),
            b"",
        ):
            digest.update(block)
    return digest.hexdigest()


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, indent=2, sort_keys=True)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary, path)


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def durable_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with source.open("rb") as input_file, temporary.open("wb") as output_file:
        shutil.copyfileobj(input_file, output_file, READ_CHUNK_BYTES)
        output_file.flush()
        os.fsync(output_file.fileno())
    os.replace(temporary, destination)


def create_synthetic_source(path: Path, size_bytes: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    block = hashlib.sha256(b"SUNNYBOTICS-P2-09").digest() * 2048
    remaining = size_bytes
    with path.open("wb") as file:
        header = (
            b"SUNNYBOTICS P2-09 SYNTHETIC UPLOAD PAYLOAD\n"
            b"This file validates interruption, retry, and integrity.\n"
        )
        file.write(header[:remaining])
        remaining -= min(len(header), remaining)
        while remaining > 0:
            chunk = block[: min(len(block), remaining)]
            file.write(chunk)
            remaining -= len(chunk)
        file.flush()
        os.fsync(file.fileno())


def safe_name(value: str) -> str:
    name = Path(value).name
    if not name or name in {".", ".."}:
        raise ValueError("Invalid filename")
    return name


@dataclass(frozen=True)
class QueueItem:
    image_id: str
    image_path: Path
    metadata_path: Path
    image_sha256: str
    metadata_sha256: str
    image_filename: str
    metadata_filename: str
    attempt_count: int


class PersistentUploadQueue:
    """SQLite queue that survives process and power interruptions."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(
            database_path,
            timeout=30.0,
            isolation_level=None,
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA busy_timeout=30000")
        self._create_schema()
        self.recover_interrupted()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS upload_queue (
                image_id TEXT PRIMARY KEY,
                image_path TEXT NOT NULL,
                metadata_path TEXT NOT NULL,
                image_filename TEXT NOT NULL,
                metadata_filename TEXT NOT NULL,
                image_sha256 TEXT NOT NULL,
                metadata_sha256 TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending', 'in_progress', 'uploaded')),
                attempt_count INTEGER NOT NULL DEFAULT 0,
                created_at_utc TEXT NOT NULL,
                last_attempt_utc TEXT,
                next_attempt_epoch REAL NOT NULL DEFAULT 0,
                uploaded_at_utc TEXT,
                last_error TEXT,
                receipt_json TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_upload_queue_ready
            ON upload_queue(status, next_attempt_epoch, created_at_utc);
            """
        )

    def close(self) -> None:
        self.connection.close()

    def recover_interrupted(self) -> int:
        cursor = self.connection.execute(
            """
            UPDATE upload_queue
            SET status = 'pending',
                next_attempt_epoch = 0,
                last_error = CASE
                    WHEN last_error IS NULL OR last_error = ''
                    THEN 'Recovered after uploader restart'
                    ELSE last_error || '; recovered after uploader restart'
                END
            WHERE status = 'in_progress'
            """
        )
        return int(cursor.rowcount)

    def enqueue(
        self,
        image_id: str,
        image_path: Path,
        metadata_path: Path,
    ) -> None:
        image_path = image_path.resolve()
        metadata_path = metadata_path.resolve()
        if not image_path.is_file():
            raise FileNotFoundError(image_path)
        if not metadata_path.is_file():
            raise FileNotFoundError(metadata_path)

        image_hash = sha256_file(image_path)
        metadata_hash = sha256_file(metadata_path)

        existing = self.connection.execute(
            "SELECT * FROM upload_queue WHERE image_id = ?",
            (image_id,),
        ).fetchone()

        if existing is not None:
            same = (
                existing["image_sha256"] == image_hash
                and existing["metadata_sha256"] == metadata_hash
            )
            if same:
                return
            raise ValueError(
                f"Queue conflict: image_id {image_id!r} already exists "
                "with different content."
            )

        self.connection.execute(
            """
            INSERT INTO upload_queue (
                image_id,
                image_path,
                metadata_path,
                image_filename,
                metadata_filename,
                image_sha256,
                metadata_sha256,
                status,
                attempt_count,
                created_at_utc,
                next_attempt_epoch
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0, ?, 0)
            """,
            (
                image_id,
                str(image_path),
                str(metadata_path),
                image_path.name,
                metadata_path.name,
                image_hash,
                metadata_hash,
                utc_now(),
            ),
        )

    def claim_next(self) -> QueueItem | None:
        now_epoch = time.time()
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self.connection.execute(
                """
                SELECT *
                FROM upload_queue
                WHERE status = 'pending'
                  AND next_attempt_epoch <= ?
                ORDER BY created_at_utc, image_id
                LIMIT 1
                """,
                (now_epoch,),
            ).fetchone()

            if row is None:
                self.connection.execute("COMMIT")
                return None

            attempt_count = int(row["attempt_count"]) + 1
            self.connection.execute(
                """
                UPDATE upload_queue
                SET status = 'in_progress',
                    attempt_count = ?,
                    last_attempt_utc = ?,
                    last_error = NULL
                WHERE image_id = ?
                """,
                (attempt_count, utc_now(), row["image_id"]),
            )
            self.connection.execute("COMMIT")
        except Exception:
            self.connection.execute("ROLLBACK")
            raise

        return QueueItem(
            image_id=str(row["image_id"]),
            image_path=Path(str(row["image_path"])),
            metadata_path=Path(str(row["metadata_path"])),
            image_sha256=str(row["image_sha256"]),
            metadata_sha256=str(row["metadata_sha256"]),
            image_filename=str(row["image_filename"]),
            metadata_filename=str(row["metadata_filename"]),
            attempt_count=attempt_count,
        )

    def mark_uploaded(self, image_id: str, receipt: dict[str, Any]) -> None:
        self.connection.execute(
            """
            UPDATE upload_queue
            SET status = 'uploaded',
                uploaded_at_utc = ?,
                next_attempt_epoch = 0,
                last_error = NULL,
                receipt_json = ?
            WHERE image_id = ?
            """,
            (utc_now(), json.dumps(receipt, sort_keys=True), image_id),
        )

    def mark_failed(
        self,
        item: QueueItem,
        error: str,
        base_delay_s: float,
        maximum_delay_s: float,
    ) -> float:
        delay = min(
            maximum_delay_s,
            base_delay_s * (2 ** max(item.attempt_count - 1, 0)),
        )
        self.connection.execute(
            """
            UPDATE upload_queue
            SET status = 'pending',
                next_attempt_epoch = ?,
                last_error = ?
            WHERE image_id = ?
            """,
            (time.time() + delay, error[:2000], item.image_id),
        )
        return delay

    def count(self, status: str | None = None) -> int:
        if status is None:
            row = self.connection.execute(
                "SELECT COUNT(*) AS count FROM upload_queue"
            ).fetchone()
        else:
            row = self.connection.execute(
                "SELECT COUNT(*) AS count FROM upload_queue WHERE status = ?",
                (status,),
            ).fetchone()
        return int(row["count"])

    def next_ready_delay(self) -> float:
        row = self.connection.execute(
            """
            SELECT MIN(next_attempt_epoch) AS next_epoch
            FROM upload_queue
            WHERE status = 'pending'
            """
        ).fetchone()
        value = row["next_epoch"]
        if value is None:
            return 0.0
        return max(0.0, float(value) - time.time())

    def snapshot(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM upload_queue ORDER BY created_at_utc, image_id"
        ).fetchall()
        output: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            if item.get("receipt_json"):
                item["receipt"] = json.loads(item.pop("receipt_json"))
            else:
                item.pop("receipt_json", None)
                item["receipt"] = None
            output.append(item)
        return output


class UploadProtocolError(RuntimeError):
    pass


class UploadClient:
    """Streams image and metadata files, then commits the upload atomically."""

    def __init__(self, endpoint: str, timeout_s: float = 3.0) -> None:
        parsed = urlsplit(endpoint)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Endpoint must use http:// or https://")
        if parsed.hostname is None:
            raise ValueError("Endpoint hostname is missing")
        self.scheme = parsed.scheme
        self.host = parsed.hostname
        self.port = parsed.port or (443 if parsed.scheme == "https" else 80)
        self.base_path = parsed.path.rstrip("/")
        self.timeout_s = timeout_s

    def _connection(self) -> http.client.HTTPConnection:
        if self.scheme == "https":
            return http.client.HTTPSConnection(
                self.host,
                self.port,
                timeout=self.timeout_s,
            )
        return http.client.HTTPConnection(
            self.host,
            self.port,
            timeout=self.timeout_s,
        )

    def _path(self, suffix: str) -> str:
        return f"{self.base_path}{suffix}" or "/"

    def _read_response(
        self,
        connection: http.client.HTTPConnection,
    ) -> dict[str, Any]:
        response = connection.getresponse()
        body = response.read()
        if not 200 <= response.status < 300:
            text = body.decode("utf-8", errors="replace")
            raise UploadProtocolError(
                f"HTTP {response.status} {response.reason}: {text[:500]}"
            )
        if not body:
            return {}
        return json.loads(body.decode("utf-8"))

    def _put_file(
        self,
        image_id: str,
        stage: str,
        path: Path,
        checksum: str,
    ) -> dict[str, Any]:
        connection = self._connection()
        request_path = self._path(
            f"/v1/uploads/{quote(image_id, safe='')}/{stage}"
        )
        size = path.stat().st_size
        try:
            connection.putrequest("PUT", request_path)
            connection.putheader("Content-Length", str(size))
            connection.putheader("Content-Type", "application/octet-stream")
            connection.putheader("X-File-Name", path.name)
            connection.putheader("X-SHA256", checksum)
            connection.endheaders()
            with path.open("rb") as file:
                for block in iter(
                    lambda: file.read(READ_CHUNK_BYTES),
                    b"",
                ):
                    connection.send(block)
            return self._read_response(connection)
        finally:
            connection.close()

    def _commit(self, item: QueueItem) -> dict[str, Any]:
        payload = json.dumps(
            {
                "image_id": item.image_id,
                "image_filename": item.image_filename,
                "metadata_filename": item.metadata_filename,
                "image_sha256": item.image_sha256,
                "metadata_sha256": item.metadata_sha256,
            },
            sort_keys=True,
        ).encode("utf-8")

        connection = self._connection()
        request_path = self._path(
            f"/v1/uploads/{quote(item.image_id, safe='')}/commit"
        )
        try:
            connection.request(
                "POST",
                request_path,
                body=payload,
                headers={
                    "Content-Type": "application/json",
                    "Content-Length": str(len(payload)),
                },
            )
            return self._read_response(connection)
        finally:
            connection.close()

    def upload(self, item: QueueItem) -> dict[str, Any]:
        if not item.image_path.is_file():
            raise FileNotFoundError(item.image_path)
        if not item.metadata_path.is_file():
            raise FileNotFoundError(item.metadata_path)

        if sha256_file(item.image_path) != item.image_sha256:
            raise UploadProtocolError("Local image checksum changed after enqueue")
        if sha256_file(item.metadata_path) != item.metadata_sha256:
            raise UploadProtocolError("Local metadata checksum changed after enqueue")

        self._put_file(
            item.image_id,
            "image",
            item.image_path,
            item.image_sha256,
        )
        self._put_file(
            item.image_id,
            "metadata",
            item.metadata_path,
            item.metadata_sha256,
        )
        return self._commit(item)


class UploadWorker:
    def __init__(
        self,
        queue: PersistentUploadQueue,
        client: UploadClient,
        base_delay_s: float = 0.2,
        maximum_delay_s: float = 1.0,
    ) -> None:
        self.queue = queue
        self.client = client
        self.base_delay_s = base_delay_s
        self.maximum_delay_s = maximum_delay_s
        self.attempt_rows: list[dict[str, Any]] = []

    def run_one(self) -> bool:
        item = self.queue.claim_next()
        if item is None:
            return False

        started_utc = utc_now()
        started = time.perf_counter()
        error_text: str | None = None
        receipt: dict[str, Any] | None = None
        success = False
        retry_delay_s = 0.0

        try:
            receipt = self.client.upload(item)
            self.queue.mark_uploaded(item.image_id, receipt)
            success = True
            LOGGER.info(
                "Upload completed",
                extra={"image_id": item.image_id, "attempt": item.attempt_count},
            )
        except Exception as exc:
            error_text = f"{type(exc).__name__}: {exc}"
            retry_delay_s = self.queue.mark_failed(
                item,
                error_text,
                self.base_delay_s,
                self.maximum_delay_s,
            )
            LOGGER.warning(
                "Upload failed; item remains queued",
                extra={
                    "image_id": item.image_id,
                    "attempt": item.attempt_count,
                    "error": error_text,
                    "retry_delay_s": retry_delay_s,
                },
            )

        self.attempt_rows.append(
            {
                "image_id": item.image_id,
                "attempt_number": item.attempt_count,
                "started_at_utc": started_utc,
                "completed_at_utc": utc_now(),
                "duration_ms": round(
                    (time.perf_counter() - started) * 1000,
                    3,
                ),
                "success": success,
                "retry_delay_s": round(retry_delay_s, 3),
                "error": error_text or "",
                "server_result": (
                    receipt.get("result", "")
                    if receipt
                    else ""
                ),
            }
        )
        return True

    def run_attempts(self, maximum_items: int) -> int:
        processed = 0
        for _ in range(maximum_items):
            if not self.run_one():
                break
            processed += 1
        return processed

    def drain(self, timeout_s: float) -> None:
        deadline = time.monotonic() + timeout_s
        while self.queue.count("pending") > 0 or self.queue.count("in_progress") > 0:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    "Uploader did not drain before the validation deadline"
                )
            if not self.run_one():
                time.sleep(min(max(self.queue.next_ready_delay(), 0.01), 0.1))


class MockServerState:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.request_rows: list[dict[str, Any]] = []
        self.transient_failures: dict[tuple[str, str], int] = {}
        self.drop_upload_once: set[tuple[str, str]] = set()
        self.dropped_uploads: set[tuple[str, str]] = set()
        self.lose_commit_response_once: set[str] = set()
        self.lost_commit_responses: set[str] = set()

    def log_request(
        self,
        method: str,
        image_id: str,
        stage: str,
        outcome: str,
        status_code: int | str,
        detail: str = "",
    ) -> None:
        with self.lock:
            self.request_rows.append(
                {
                    "recorded_at_utc": utc_now(),
                    "method": method,
                    "image_id": image_id,
                    "stage": stage,
                    "outcome": outcome,
                    "status_code": status_code,
                    "detail": detail,
                }
            )

    def consume_transient_failure(self, image_id: str, stage: str) -> bool:
        key = (image_id, stage)
        with self.lock:
            remaining = self.transient_failures.get(key, 0)
            if remaining <= 0:
                return False
            self.transient_failures[key] = remaining - 1
            return True

    def should_drop_upload(self, image_id: str, stage: str) -> bool:
        key = (image_id, stage)
        with self.lock:
            if key not in self.drop_upload_once or key in self.dropped_uploads:
                return False
            self.dropped_uploads.add(key)
            return True

    def should_lose_commit_response(self, image_id: str) -> bool:
        with self.lock:
            if (
                image_id not in self.lose_commit_response_once
                or image_id in self.lost_commit_responses
            ):
                return False
            self.lost_commit_responses.add(image_id)
            return True

    def object_root(self, image_id: str) -> Path:
        return self.root / "objects" / image_id

    def receipt_path(self, image_id: str) -> Path:
        return self.object_root(image_id) / "receipt.json"

    def receipts(self) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for path in sorted((self.root / "objects").glob("*/receipt.json")):
            output.append(json.loads(path.read_text(encoding="utf-8")))
        return output


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class MockUploadRequestHandler(BaseHTTPRequestHandler):
    server_version = "SunnyboticsP209Mock/1.0"
    protocol_version = "HTTP/1.1"

    @property
    def state(self) -> MockServerState:
        return self.server.state  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _route(self) -> tuple[str, str] | None:
        parts = [
            unquote(part)
            for part in urlsplit(self.path).path.strip("/").split("/")
        ]
        if len(parts) != 4 or parts[:2] != ["v1", "uploads"]:
            return None
        return parts[2], parts[3]

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def _drop_connection(self) -> None:
        self.close_connection = True
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.connection.close()
        except OSError:
            pass

    def do_PUT(self) -> None:
        route = self._route()
        if route is None:
            self._send_json(404, {"error": "not_found"})
            return
        image_id, stage = route
        if stage not in {"image", "metadata"}:
            self._send_json(404, {"error": "unknown_stage"})
            return

        if self.state.consume_transient_failure(image_id, stage):
            self.state.log_request("PUT", image_id, stage, "transient_failure", 500)
            self._send_json(500, {"error": "simulated_transient_failure"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        expected_hash = self.headers.get("X-SHA256", "")
        filename = safe_name(self.headers.get("X-File-Name", f"{stage}.bin"))

        if self.state.should_drop_upload(image_id, stage):
            partial_bytes = max(1, content_length // 2)
            self.rfile.read(partial_bytes)
            self.state.log_request(
                "PUT",
                image_id,
                stage,
                "connection_dropped_mid_upload",
                "connection_closed",
                f"read {partial_bytes} of {content_length} bytes",
            )
            self._drop_connection()
            return

        body = self.rfile.read(content_length)
        if len(body) != content_length:
            self.state.log_request(
                "PUT", image_id, stage, "short_body", 400,
                f"received {len(body)} of {content_length} bytes",
            )
            self._send_json(400, {"error": "short_body"})
            return

        actual_hash = hashlib.sha256(body).hexdigest()
        if not expected_hash or actual_hash != expected_hash:
            self.state.log_request(
                "PUT", image_id, stage, "checksum_mismatch", 422,
            )
            self._send_json(422, {"error": "checksum_mismatch"})
            return

        destination = self.state.object_root(image_id) / stage / filename
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            existing_hash = sha256_file(destination)
            if existing_hash != expected_hash:
                self.state.log_request(
                    "PUT", image_id, stage, "content_conflict", 409,
                )
                self._send_json(409, {"error": "content_conflict"})
                return
            result = "already_present"
        else:
            temporary = destination.with_suffix(destination.suffix + ".tmp")
            with temporary.open("wb") as file:
                file.write(body)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, destination)
            result = "stored"

        self.state.log_request("PUT", image_id, stage, result, 200)
        self._send_json(
            200,
            {
                "image_id": image_id,
                "stage": stage,
                "result": result,
                "sha256": actual_hash,
                "byte_size": len(body),
            },
        )

    def do_POST(self) -> None:
        route = self._route()
        if route is None:
            self._send_json(404, {"error": "not_found"})
            return
        image_id, stage = route
        if stage != "commit":
            self._send_json(404, {"error": "unknown_stage"})
            return

        if self.state.consume_transient_failure(image_id, stage):
            self.state.log_request("POST", image_id, stage, "transient_failure", 500)
            self._send_json(500, {"error": "simulated_transient_failure"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body.decode("utf-8"))
            image_filename = safe_name(str(payload["image_filename"]))
            metadata_filename = safe_name(str(payload["metadata_filename"]))
            image_hash = str(payload["image_sha256"])
            metadata_hash = str(payload["metadata_sha256"])
        except Exception as exc:
            self.state.log_request(
                "POST", image_id, stage, "invalid_json", 400, str(exc),
            )
            self._send_json(400, {"error": "invalid_commit_payload"})
            return

        object_root = self.state.object_root(image_id)
        image_path = object_root / "image" / image_filename
        metadata_path = object_root / "metadata" / metadata_filename
        if not image_path.is_file() or not metadata_path.is_file():
            self.state.log_request("POST", image_id, stage, "files_missing", 409)
            self._send_json(409, {"error": "files_missing"})
            return

        actual_image_hash = sha256_file(image_path)
        actual_metadata_hash = sha256_file(metadata_path)
        if actual_image_hash != image_hash or actual_metadata_hash != metadata_hash:
            self.state.log_request("POST", image_id, stage, "checksum_mismatch", 422)
            self._send_json(422, {"error": "checksum_mismatch"})
            return

        receipt_path = self.state.receipt_path(image_id)
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if (
                receipt["image_sha256"] != image_hash
                or receipt["metadata_sha256"] != metadata_hash
            ):
                self.state.log_request("POST", image_id, stage, "receipt_conflict", 409)
                self._send_json(409, {"error": "receipt_conflict"})
                return
            receipt = dict(receipt)
            receipt["result"] = "already_committed"
        else:
            receipt = {
                "image_id": image_id,
                "image_filename": image_filename,
                "metadata_filename": metadata_filename,
                "image_sha256": image_hash,
                "metadata_sha256": metadata_hash,
                "committed_at_utc": utc_now(),
                "result": "stored",
            }
            write_json_atomic(receipt_path, receipt)

        if self.state.should_lose_commit_response(image_id):
            self.state.log_request(
                "POST",
                image_id,
                stage,
                "commit_stored_response_lost",
                "connection_closed",
            )
            self._drop_connection()
            return

        self.state.log_request(
            "POST", image_id, stage, str(receipt["result"]), 200,
        )
        self._send_json(200, receipt)


class MockUploadServer:
    def __init__(self, state: MockServerState, port: int = 0) -> None:
        self.state = state
        self.port = port
        self.httpd: ReusableThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    @property
    def endpoint(self) -> str:
        if self.port <= 0:
            raise RuntimeError("Server has not been started")
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> None:
        if self.httpd is not None:
            return
        self.httpd = ReusableThreadingHTTPServer(
            ("127.0.0.1", self.port),
            MockUploadRequestHandler,
        )
        self.httpd.state = self.state  # type: ignore[attr-defined]
        self.port = int(self.httpd.server_address[1])
        self.thread = threading.Thread(
            target=self.httpd.serve_forever,
            name="p2-09-mock-server",
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        if self.httpd is None:
            return
        self.httpd.shutdown()
        self.httpd.server_close()
        if self.thread is not None:
            self.thread.join(timeout=5.0)
        self.httpd = None
        self.thread = None
        time.sleep(0.05)


def configure_logging(log_path: Path, verbose: bool) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter(
        "%(asctime)sZ %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)


def capture_bundle(
    index: int,
    phase: str,
    sample_source: Path,
    local_root: Path,
    queue: PersistentUploadQueue,
    server_available: bool,
) -> dict[str, Any]:
    image_id = f"sunnybot-01_p2-09_{index:06d}"
    suffix = sample_source.suffix.lower() or ".bin"
    image_path = local_root / "images" / f"{image_id}{suffix}"
    metadata_path = local_root / "metadata" / f"{image_id}.json"

    captured_at = utc_now()
    durable_copy(sample_source, image_path)
    metadata = {
        "schema_version": "2.0.0",
        "image_id": image_id,
        "captured_at_utc": captured_at,
        "robot_id": "sunnybot-01",
        "mission_id": "p2-09-upload-interruption-retry",
        "status": "complete",
        "image": {
            "filename": image_path.name,
            "relative_path": str(image_path.relative_to(local_root)),
            "byte_size": image_path.stat().st_size,
            "sha256": sha256_file(image_path),
        },
        "coordinates": {
            "latitude": 34.420830,
            "longitude": -119.698190,
            "valid": True,
        },
        "site": {"row": None, "panel": None},
        "validation": {
            "id": VALIDATION_ID,
            "phase": phase,
            "server_available_at_capture": server_available,
        },
    }
    write_json_atomic(metadata_path, metadata)
    queue.enqueue(image_id, image_path, metadata_path)

    return {
        "index": index,
        "phase": phase,
        "captured_at_utc": captured_at,
        "server_available": server_available,
        "image_id": image_id,
        "image_path": str(image_path),
        "metadata_path": str(metadata_path),
        "image_bytes": image_path.stat().st_size,
        "image_sha256": sha256_file(image_path),
        "metadata_sha256": sha256_file(metadata_path),
        "queue_status_after_capture": "pending",
    }


def inventory_local_files(queue_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in queue_rows:
        for kind in ("image", "metadata"):
            path = Path(str(row[f"{kind}_path"]))
            expected_hash = str(row[f"{kind}_sha256"])
            exists = path.is_file()
            actual_hash = sha256_file(path) if exists else ""
            output.append(
                {
                    "image_id": row["image_id"],
                    "kind": kind,
                    "path": str(path),
                    "exists": exists,
                    "byte_size": path.stat().st_size if exists else 0,
                    "expected_sha256": expected_hash,
                    "actual_sha256": actual_hash,
                    "checksum_match": exists and actual_hash == expected_hash,
                }
            )
    return output


def compare_server_checksums(
    queue_rows: list[dict[str, Any]],
    state: MockServerState,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in queue_rows:
        image_id = str(row["image_id"])
        object_root = state.object_root(image_id)
        image_path = object_root / "image" / str(row["image_filename"])
        metadata_path = object_root / "metadata" / str(row["metadata_filename"])
        receipt_path = state.receipt_path(image_id)
        for kind, path in (("image", image_path), ("metadata", metadata_path)):
            expected_hash = str(row[f"{kind}_sha256"])
            exists = path.is_file()
            actual_hash = sha256_file(path) if exists else ""
            output.append(
                {
                    "image_id": image_id,
                    "kind": kind,
                    "server_path": str(path),
                    "exists": exists,
                    "expected_sha256": expected_hash,
                    "actual_sha256": actual_hash,
                    "checksum_match": exists and actual_hash == expected_hash,
                    "receipt_exists": receipt_path.is_file(),
                }
            )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "P2-09 upload interruption, persistent queue, retry, restart, "
            "integrity, and idempotency validation."
        )
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=HERE.parent / "ValidationEvidence" / VALIDATION_ID,
        help="Directory where reports, queue database, and logs are saved.",
    )
    parser.add_argument(
        "--sample-image",
        type=Path,
        default=None,
        help=(
            "Representative image to copy for each bundle. By default the "
            "script tries MetadataLabeling/sample_images/Sample1.jpg."
        ),
    )
    parser.add_argument(
        "--synthetic-size-kb",
        type=int,
        default=256,
        help="Fallback payload size when no sample image is available.",
    )
    parser.add_argument(
        "--normal-count",
        type=int,
        default=20,
        help="Bundles uploaded before the outage.",
    )
    parser.add_argument(
        "--offline-count",
        type=int,
        default=40,
        help="Bundles captured while the server is unavailable.",
    )
    parser.add_argument(
        "--recovered-count",
        type=int,
        default=40,
        help="Bundles captured after connectivity is restored.",
    )
    parser.add_argument(
        "--drain-timeout-s",
        type=float,
        default=120.0,
        help="Maximum time allowed for queue recovery and upload.",
    )
    parser.add_argument(
        "--keep-runtime",
        action="store_true",
        help="Keep copied local and mock-server payload files after validation.",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def run_validation(args: argparse.Namespace) -> dict[str, Any]:
    evidence_root = args.evidence_root.expanduser().resolve()
    if evidence_root.exists():
        shutil.rmtree(evidence_root)
    evidence_root.mkdir(parents=True, exist_ok=True)

    runtime_root = evidence_root / "runtime"
    local_root = runtime_root / "local-storage"
    server_root = runtime_root / "mock-server"
    database_path = evidence_root / "P2-09-upload-queue.sqlite3"
    log_path = evidence_root / "logs" / "p2-09.log"
    configure_logging(log_path, args.verbose)

    configured_sample = (
        args.sample_image.expanduser().resolve()
        if args.sample_image is not None
        else HERE / "sample_images" / "Sample1.jpg"
    )
    if configured_sample.is_file():
        sample_source = configured_sample
        sample_type = "representative_image"
    else:
        sample_source = runtime_root / "source" / "p2-09-synthetic.bin"
        create_synthetic_source(
            sample_source,
            max(1, int(args.synthetic_size_kb)) * 1024,
        )
        sample_type = "synthetic_fallback"
        LOGGER.warning(
            "Representative sample image was not found; using a synthetic payload",
            extra={"expected_sample": str(configured_sample)},
        )

    normal_count = max(1, int(args.normal_count))
    offline_count = max(1, int(args.offline_count))
    recovered_count = max(1, int(args.recovered_count))
    expected_total = normal_count + offline_count + recovered_count

    state = MockServerState(server_root)
    server = MockUploadServer(state)
    server.start()
    endpoint = server.endpoint

    queue = PersistentUploadQueue(database_path)
    worker = UploadWorker(queue, UploadClient(endpoint, timeout_s=2.0))
    capture_rows: list[dict[str, Any]] = []

    LOGGER.info("Starting normal online phase")
    for index in range(1, normal_count + 1):
        capture_rows.append(
            capture_bundle(
                index,
                "normal-online",
                sample_source,
                local_root,
                queue,
                server_available=True,
            )
        )
    write_json_atomic(
        evidence_root / "P2-09-queue-before-outage.json",
        queue.snapshot(),
    )
    worker.drain(args.drain_timeout_s)

    LOGGER.info("Stopping server to simulate unavailable internet")
    server.stop()
    offline_start = normal_count + 1
    offline_end = normal_count + offline_count
    for index in range(offline_start, offline_end + 1):
        capture_rows.append(
            capture_bundle(
                index,
                "server-unavailable",
                sample_source,
                local_root,
                queue,
                server_available=False,
            )
        )

    offline_pending_before_attempts = queue.count("pending")
    offline_attempts_requested = min(5, offline_count)
    worker.run_attempts(offline_attempts_requested)
    during_outage_snapshot = queue.snapshot()
    write_json_atomic(
        evidence_root / "P2-09-queue-during-outage.json",
        during_outage_snapshot,
    )
    local_during_outage = inventory_local_files(during_outage_snapshot)
    write_csv(
        evidence_root / "P2-09-local-files-during-outage.csv",
        local_during_outage,
        [
            "image_id",
            "kind",
            "path",
            "exists",
            "byte_size",
            "expected_sha256",
            "actual_sha256",
            "checksum_match",
        ],
    )

    LOGGER.info("Closing and reopening queue to prove restart persistence")
    attempt_rows = list(worker.attempt_rows)
    queue.close()
    queue = PersistentUploadQueue(database_path)
    pending_after_restart = queue.count("pending")

    server = MockUploadServer(state, port=server.port)
    server.start()
    endpoint_after_restart = server.endpoint
    client = UploadClient(endpoint_after_restart, timeout_s=2.0)
    worker = UploadWorker(queue, client)

    special_ids = [
        f"sunnybot-01_p2-09_{offline_start:06d}",
        f"sunnybot-01_p2-09_{offline_start + 1:06d}",
        f"sunnybot-01_p2-09_{offline_start + 2:06d}",
    ]
    state.transient_failures[(special_ids[0], "image")] = 2
    state.drop_upload_once.add((special_ids[1], "image"))
    state.lose_commit_response_once.add(special_ids[2])

    LOGGER.info("Connectivity restored; draining persistent queue")
    worker.drain(args.drain_timeout_s)

    recovery_start = offline_end + 1
    for index in range(recovery_start, expected_total + 1):
        capture_rows.append(
            capture_bundle(
                index,
                "online-after-recovery",
                sample_source,
                local_root,
                queue,
                server_available=True,
            )
        )
    worker.drain(args.drain_timeout_s)
    attempt_rows.extend(worker.attempt_rows)

    final_snapshot = queue.snapshot()
    write_json_atomic(
        evidence_root / "P2-09-queue-after-recovery.json",
        final_snapshot,
    )

    local_final = inventory_local_files(final_snapshot)
    server_checksums = compare_server_checksums(final_snapshot, state)
    receipts = state.receipts()

    write_csv(
        evidence_root / "P2-09-capture-log.csv",
        capture_rows,
        [
            "index",
            "phase",
            "captured_at_utc",
            "server_available",
            "image_id",
            "image_path",
            "metadata_path",
            "image_bytes",
            "image_sha256",
            "metadata_sha256",
            "queue_status_after_capture",
        ],
    )
    write_csv(
        evidence_root / "P2-09-upload-attempts.csv",
        attempt_rows,
        [
            "image_id",
            "attempt_number",
            "started_at_utc",
            "completed_at_utc",
            "duration_ms",
            "success",
            "retry_delay_s",
            "error",
            "server_result",
        ],
    )
    write_csv(
        evidence_root / "P2-09-local-file-inventory.csv",
        local_final,
        [
            "image_id",
            "kind",
            "path",
            "exists",
            "byte_size",
            "expected_sha256",
            "actual_sha256",
            "checksum_match",
        ],
    )
    write_csv(
        evidence_root / "P2-09-checksum-comparison.csv",
        server_checksums,
        [
            "image_id",
            "kind",
            "server_path",
            "exists",
            "expected_sha256",
            "actual_sha256",
            "checksum_match",
            "receipt_exists",
        ],
    )
    write_csv(
        evidence_root / "P2-09-server-request-log.csv",
        state.request_rows,
        [
            "recorded_at_utc",
            "method",
            "image_id",
            "stage",
            "outcome",
            "status_code",
            "detail",
        ],
    )
    write_json_atomic(
        evidence_root / "P2-09-server-receipts.json",
        receipts,
    )

    failed_attempts = [row for row in attempt_rows if not row["success"]]
    missing_local = [row for row in local_final if not row["exists"]]
    bad_local_checksums = [
        row for row in local_final if not row["checksum_match"]
    ]
    bad_server_checksums = [
        row for row in server_checksums if not row["checksum_match"]
    ]
    missing_receipts = [
        row for row in server_checksums if not row["receipt_exists"]
    ]
    receipt_ids = [str(receipt["image_id"]) for receipt in receipts]
    duplicate_receipt_ids = sorted(
        image_id
        for image_id in set(receipt_ids)
        if receipt_ids.count(image_id) > 1
    )
    offline_capture_rows = [
        row for row in capture_rows if row["phase"] == "server-unavailable"
    ]
    offline_attempt_failures = [
        row
        for row in attempt_rows
        if (
            not row["success"]
            and int(str(row["image_id"]).rsplit("_", 1)[-1])
            <= offline_end
            and int(str(row["image_id"]).rsplit("_", 1)[-1])
            >= offline_start
        )
    ]
    duplicate_retry_observed = any(
        row["image_id"] == special_ids[2]
        and row["outcome"] == "already_committed"
        for row in state.request_rows
    )

    checks = {
        "all_expected_bundles_generated": len(capture_rows) == expected_total,
        "capture_continued_during_outage": len(offline_capture_rows) == offline_count,
        "all_offline_bundles_entered_queue": (
            offline_pending_before_attempts == offline_count
        ),
        "offline_failures_were_logged": len(offline_attempt_failures) > 0,
        "local_files_survived_outage": all(
            row["exists"] and row["checksum_match"]
            for row in local_during_outage
        ),
        "queue_survived_restart": pending_after_restart == offline_count,
        "queue_drained_after_recovery": queue.count("pending") == 0,
        "no_in_progress_items_remain": queue.count("in_progress") == 0,
        "all_items_marked_uploaded": queue.count("uploaded") == expected_total,
        "all_local_files_still_exist": len(missing_local) == 0,
        "all_local_checksums_match": len(bad_local_checksums) == 0,
        "server_has_one_receipt_per_bundle": len(receipts) == expected_total,
        "no_duplicate_final_receipts": len(duplicate_receipt_ids) == 0,
        "all_server_checksums_match": len(bad_server_checksums) == 0,
        "all_server_receipts_exist": len(missing_receipts) == 0,
        "transient_500_retry_recovered": (
            state.transient_failures.get((special_ids[0], "image"), -1) == 0
        ),
        "mid_upload_disconnect_recovered": (
            (special_ids[1], "image") in state.dropped_uploads
        ),
        "lost_commit_response_recovered_idempotently": (
            special_ids[2] in state.lost_commit_responses
            and duplicate_retry_observed
        ),
    }

    passed = all(checks.values())
    report = {
        "validation_id": VALIDATION_ID,
        "title": "Upload Interruption and Retry Validation",
        "completed_at_utc": utc_now(),
        "result": "PASS" if passed else "FAIL",
        "configuration": {
            "normal_count": normal_count,
            "offline_count": offline_count,
            "recovered_count": recovered_count,
            "expected_total": expected_total,
            "endpoint": endpoint,
            "endpoint_after_restart": endpoint_after_restart,
            "sample_source": str(sample_source),
            "sample_type": sample_type,
            "sample_bytes": sample_source.stat().st_size,
            "sample_sha256": sha256_file(sample_source),
            "keep_runtime": bool(args.keep_runtime),
        },
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "machine": platform.machine(),
            "hostname": socket.gethostname(),
        },
        "counts": {
            "generated_bundles": len(capture_rows),
            "captured_during_outage": len(offline_capture_rows),
            "pending_before_offline_attempts": offline_pending_before_attempts,
            "pending_after_restart": pending_after_restart,
            "upload_attempts": len(attempt_rows),
            "failed_upload_attempts": len(failed_attempts),
            "uploaded_queue_items": queue.count("uploaded"),
            "pending_queue_items": queue.count("pending"),
            "server_receipts": len(receipts),
            "server_files_checked": len(server_checksums),
            "server_checksum_mismatches": len(bad_server_checksums),
            "local_checksum_mismatches": len(bad_local_checksums),
            "duplicate_final_receipts": len(duplicate_receipt_ids),
        },
        "special_scenarios": {
            "transient_500_image_id": special_ids[0],
            "mid_upload_disconnect_image_id": special_ids[1],
            "lost_commit_response_image_id": special_ids[2],
        },
        "checks": checks,
        "failures": {
            "missing_local_files": missing_local,
            "bad_local_checksums": bad_local_checksums,
            "bad_server_checksums": bad_server_checksums,
            "missing_receipts": missing_receipts,
            "duplicate_receipt_ids": duplicate_receipt_ids,
        },
        "evidence": [
            "P2-09-upload-queue.sqlite3",
            "P2-09-queue-before-outage.json",
            "P2-09-queue-during-outage.json",
            "P2-09-queue-after-recovery.json",
            "P2-09-capture-log.csv",
            "P2-09-upload-attempts.csv",
            "P2-09-local-files-during-outage.csv",
            "P2-09-local-file-inventory.csv",
            "P2-09-checksum-comparison.csv",
            "P2-09-server-request-log.csv",
            "P2-09-server-receipts.json",
            "logs/p2-09.log",
        ],
    }
    write_json_atomic(
        evidence_root / "P2-09-final-report.json",
        report,
    )

    queue.close()
    server.stop()

    if not args.keep_runtime:
        shutil.rmtree(runtime_root, ignore_errors=True)

    return report


def main() -> int:
    args = parse_args()
    report = run_validation(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())