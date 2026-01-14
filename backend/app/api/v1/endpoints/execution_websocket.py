"""
WebSocket endpoints for execution session real-time updates
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Depends
from fastapi.exceptions import WebSocketException
from sqlalchemy.orm import Session
from typing import Optional
import asyncio
from jose import JWTError, jwt

from app.core.database import get_db, SessionLocal
from app.core.config import settings
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession
from app.models.user import User
from app.services.execution.websocket_manager import (
    WebSocketManager,
    WEBSOCKET_HEARTBEAT_INTERVAL,
    WEBSOCKET_MAX_CONNECTIONS_PER_SESSION
)

router = APIRouter()
logger = get_logger(__name__)


@router.websocket("/ws/approvals/{session_id}")
async def websocket_approvals(websocket: WebSocket, session_id: int):
    """WebSocket endpoint for real-time approval updates"""
    # Security: Authenticate WebSocket connection
    token = websocket.query_params.get("token") or websocket.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return
    
    db = None
    user_id = None
    
    try:
        # Authenticate user
        db = SessionLocal()
        try:
            # Validate token and get user
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                email: str = payload.get("sub")
                if not email:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                    return
                user = db.query(User).filter(User.email == email).first()
                if not user:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
                    return
                user_id = user.id
            except (JWTError, Exception) as e:
                logger.warning(f"WebSocket authentication failed: {e}")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                return
        finally:
            db.close()
            db = None
        
        # Check connection limit
        if not WebSocketManager.add_connection(session_id, websocket, user_id):
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=f"Maximum connections ({WEBSOCKET_MAX_CONNECTIONS_PER_SESSION}) reached for this session"
            )
            return
        
        await websocket.accept()
        
        # Send initial status
        db = SessionLocal()
        try:
            session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
            if session:
                await websocket.send_json({
                    "type": "status",
                    "session_id": session_id,
                    "status": session.status,
                    "waiting_for_approval": session.waiting_for_approval
                })
        finally:
            db.close()
            db = None
        
        # Listen for messages with timeout
        while True:
            try:
                # Wait for message with timeout
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=WEBSOCKET_HEARTBEAT_INTERVAL
                )
                
                # Update last activity time
                WebSocketManager.update_activity(session_id, websocket)
                
                if data.get("type") == "approval":
                    # Handle approval
                    approve = data.get("approve", False)
                    step_number = data.get("step_number")
                    
                    # Process approval (this would call the approval endpoint logic)
                    await websocket.send_json({
                        "type": "approval_received",
                        "approved": approve,
                        "step_number": step_number
                    })
                elif data.get("type") == "pong":
                    # Heartbeat response
                    pass
                    
            except asyncio.TimeoutError:
                # Send ping to check if connection is alive
                try:
                    await websocket.send_json({"type": "ping"})
                    # Update last activity
                    WebSocketManager.update_activity(session_id, websocket)
                except Exception:
                    # Connection is dead, break the loop
                    break
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
        WebSocketManager.cleanup_connection(session_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}", exc_info=True)
        WebSocketManager.cleanup_connection(session_id, websocket)
        try:
            await websocket.close()
        except Exception:
            pass  # Connection may already be closed
    finally:
        # Ensure database session is closed
        if db is not None:
            try:
                db.close()
            except Exception as e:
                logger.debug(f"Error closing database session: {e}")
        # Final cleanup
        WebSocketManager.cleanup_connection(session_id, websocket)

