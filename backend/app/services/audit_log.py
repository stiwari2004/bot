"""
Append-only audit log sink with hash chaining for tamper detection.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_lock = asyncio.Lock()
_last_hash: Optional[str] = None


async def record_event(
    *,
    session_id: int,
    event_type: str,
    payload: Dict[str, Any],
) -> None:
    """Persist an immutable audit record for the given event."""
    if not settings.AUDIT_LOG_ENABLED:
        return

    envelope = {
        "ts": time.time(),
        "session_id": session_id,
        "event_type": event_type,
        "payload": payload,
    }

    async with _lock:
        global _last_hash
        if _last_hash is None:
            _last_hash = await _load_last_hash()

        prev_hash = _last_hash or ""
        serialized = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        digest = _compute_hash(prev_hash, serialized)

        envelope["prev_hash"] = prev_hash
        envelope["hash"] = digest

        line = json.dumps(envelope, sort_keys=True)
        await asyncio.to_thread(_append_line, line)
        await _replicate_async(line, digest)

        _last_hash = digest


def _compute_hash(prev_hash: str, body: str) -> str:
    import hashlib

    sha = hashlib.sha256()
    sha.update(prev_hash.encode())
    sha.update(body.encode())
    return sha.hexdigest()


async def _load_last_hash() -> Optional[str]:
    path = Path(settings.AUDIT_LOG_PATH)
    if not path.exists():
        return None

    try:
        async with asyncio.Lock():
            last_line = await asyncio.to_thread(_read_last_line, path)
    except Exception as exc:
        logger.warning("Unable to read last audit log hash: %s", exc)
        return None

    if not last_line:
        return None
    try:
        parsed = json.loads(last_line)
    except json.JSONDecodeError:
        logger.warning("Audit log trailing line malformed; continuing without hash chain.")
        return None
    return parsed.get("hash")


def _append_line(line: str) -> None:
    path = Path(settings.AUDIT_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new_file = not path.exists()
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
        f.write("\n")
    if is_new_file:
        os.chmod(path, 0o600)


async def _replicate_async(line: str, digest: str) -> None:
    if not settings.AUDIT_LOG_S3_BUCKET:
        return
    try:
        await asyncio.to_thread(_replicate_to_object_store, line, digest)
    except Exception as exc:
        logger.warning("Failed to replicate audit log to object storage: %s", exc)


def _replicate_to_object_store(line: str, digest: str) -> None:
    if not settings.AUDIT_LOG_S3_BUCKET:
        return
    try:
        import boto3
    except ImportError:
        logger.warning("boto3 not installed; skipping audit log replication.")
        return

    client = boto3.client("s3")
    prefix = settings.AUDIT_LOG_S3_PREFIX.rstrip("/")
    timestamp_segment = time.strftime("%Y/%m/%d", time.gmtime())
    key = f"{prefix}/{timestamp_segment}/{digest}.json"
    body = (line + "\n").encode("utf-8")
    put_kwargs = {
        "Bucket": settings.AUDIT_LOG_S3_BUCKET,
        "Key": key,
        "Body": body,
        "ContentType": "application/json",
    }
    try:
        put_kwargs["ServerSideEncryption"] = "AES256"
    except Exception:
        pass
    client.put_object(**put_kwargs)


def _read_last_line(path: Path) -> Optional[str]:
    with path.open("rb") as f:
        f.seek(0, os.SEEK_END)
        if f.tell() == 0:
            return None
        buffer = bytearray()
        pointer = f.tell() - 1
        while pointer >= 0:
            f.seek(pointer)
            char = f.read(1)
            if char == b"\n" and buffer:
                break
            buffer.extend(char)
            pointer -= 1
        line_bytes = bytes(reversed(buffer))
    try:
        return line_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        logger.warning("Failed to decode last line of audit log.")
        return None

