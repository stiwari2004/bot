"""
Audit log read and export API.
Serves events from the append-only audit log file with tenant filtering.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession
from app.models.user import User
from app.services.auth import get_current_user

logger = get_logger(__name__)

router = APIRouter()

DEFAULT_LIMIT = 500
MAX_LIMIT = 2000


def _read_audit_log_lines(path: Path) -> List[Dict[str, Any]]:
    """Read audit log file and return list of parsed envelope dicts (oldest first)."""
    if not path.exists():
        return []
    events: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def _filter_events(
    events: List[Dict[str, Any]],
    tenant_id: int,
    from_ts: Optional[float],
    to_ts: Optional[float],
    session_id: Optional[int],
    event_type: Optional[str],
    limit: int,
    db: Session,
) -> List[Dict[str, Any]]:
    """Filter events by tenant and query params. Returns newest first, up to limit."""
    # Build set of session IDs belonging to this tenant (for legacy events without tenant_id)
    session_ids_for_tenant: Optional[set] = None

    filtered: List[Dict[str, Any]] = []
    for ev in events:
        ts = ev.get("ts")
        if ts is not None:
            if from_ts is not None and ts < from_ts:
                continue
            if to_ts is not None and ts > to_ts:
                continue
        if session_id is not None and ev.get("session_id") != session_id:
            continue
        if event_type is not None and ev.get("event_type") != event_type:
            continue

        # Tenant filter: envelope.tenant_id or payload.tenant_id, or legacy: session in tenant
        ev_tenant = ev.get("tenant_id") or (ev.get("payload") or {}).get("tenant_id")
        if ev_tenant is not None:
            if ev_tenant != tenant_id:
                continue
        else:
            sid = ev.get("session_id")
            if sid is not None and sid != 0:
                if session_ids_for_tenant is None:
                    session_ids_for_tenant = {
                        row[0]
                        for row in db.query(ExecutionSession.id).filter(
                            ExecutionSession.tenant_id == tenant_id
                        ).all()
                    }
                if sid not in session_ids_for_tenant:
                    continue

        filtered.append(ev)

    # Newest first, then cap
    filtered.sort(key=lambda e: e.get("ts") or 0, reverse=True)
    return filtered[:limit]


@router.get("", response_model=List[Dict[str, Any]])
async def list_audit_log(
    from_ts: Optional[float] = Query(None, description="Start timestamp (Unix)"),
    to_ts: Optional[float] = Query(None, description="End timestamp (Unix)"),
    session_id: Optional[int] = Query(None, description="Filter by execution session ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List audit log events for the current user's tenant. Newest first."""
    path = Path(settings.AUDIT_LOG_PATH)
    events = _read_audit_log_lines(path)
    filtered = _filter_events(
        events,
        tenant_id=current_user.tenant_id,
        from_ts=from_ts,
        to_ts=to_ts,
        session_id=session_id,
        event_type=event_type,
        limit=limit,
        db=db,
    )
    return filtered


@router.get("/export")
async def export_audit_log(
    from_ts: Optional[float] = Query(None),
    to_ts: Optional[float] = Query(None),
    session_id: Optional[int] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Export audit log as JSONL file download."""
    path = Path(settings.AUDIT_LOG_PATH)
    events = _read_audit_log_lines(path)
    filtered = _filter_events(
        events,
        tenant_id=current_user.tenant_id,
        from_ts=from_ts,
        to_ts=to_ts,
        session_id=session_id,
        event_type=event_type,
        limit=limit,
        db=db,
    )
    lines = [json.dumps(e, sort_keys=True) for e in filtered]
    body = "\n".join(lines)
    from datetime import datetime, timezone
    filename = f"audit-log-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.jsonl"
    return Response(
        content=body.encode("utf-8"),
        media_type="application/jsonl",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
