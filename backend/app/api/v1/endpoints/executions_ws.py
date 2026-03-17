"""
WebSocket streaming endpoint for execution events
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession
from app.services.execution_orchestrator import execution_orchestrator
from app.services.queue_client import queue_client

router = APIRouter()
logger = get_logger(__name__)

WEBSOCKET_IDLE_TIMEOUT = 30 * 60   # 30 minutes
HEARTBEAT_INTERVAL = 60             # 1 minute


@router.websocket("/ws/sessions/{session_id}")
async def stream_execution_events(websocket: WebSocket, session_id: int):
    """WebSocket stream for execution events (optional authentication for demo)."""
    token = (
        websocket.query_params.get("token")
        or websocket.headers.get("Authorization", "").replace("Bearer ", "")
    )
    user_id = None

    if token:
        db = None
        try:
            from app.models.user import User
            from jose import JWTError, jwt
            db = SessionLocal()
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                email: str = payload.get("sub")
                if email:
                    user = db.query(User).filter(User.email == email).first()
                    if user:
                        user_id = user.id
                        logger.debug(f"WebSocket authenticated user: {email}")
            except (JWTError, Exception) as e:
                logger.debug(f"WebSocket authentication optional, token invalid: {e}")
            finally:
                db.close()
        except Exception as e:
            logger.debug(f"WebSocket authentication optional, error: {e}")

    await websocket.accept()

    session = None
    initial_events: List[Dict[str, Any]] = []
    db = SessionLocal()
    try:
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if session:
            initial_events = execution_orchestrator.list_events(db, session_id, limit=50)
    finally:
        db.close()

    if not session:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    last_id = "0-0"
    if initial_events:
        last_id = initial_events[-1].get("stream_id") or "0-0"
        await websocket.send_json({"events": initial_events})

    last_activity = datetime.now(timezone.utc)

    try:
        while True:
            try:
                messages = await asyncio.wait_for(
                    queue_client.read_stream(
                        settings.REDIS_STREAM_EVENTS,
                        last_id=last_id,
                        count=25,
                        block=5_000,
                    ),
                    timeout=HEARTBEAT_INTERVAL,
                )

                batch: List[Dict[str, Any]] = []
                for message_id, payload in messages:
                    last_id = message_id
                    if payload.get("session_id") == session_id:
                        payload["stream_id"] = message_id
                        batch.append(payload)

                if batch:
                    await websocket.send_json({"events": batch})
                    last_activity = datetime.now(timezone.utc)
                else:
                    await asyncio.sleep(0.1)

                idle_time = (datetime.now(timezone.utc) - last_activity).total_seconds()
                if idle_time > WEBSOCKET_IDLE_TIMEOUT:
                    logger.info(f"Closing idle WebSocket for session {session_id} (idle {idle_time:.0f}s)")
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Connection timeout")
                    break

            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                    last_activity = datetime.now(timezone.utc)
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info("Execution event stream disconnected session=%s", session_id)
    except Exception as exc:
        logger.exception("WebSocket error session=%s: %s", session_id, exc)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
