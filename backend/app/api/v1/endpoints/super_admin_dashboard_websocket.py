"""
WebSocket endpoints for super admin dashboard real-time updates
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.exceptions import WebSocketException
from sqlalchemy.orm import Session
from typing import Dict, Set
import asyncio
import json
from jose import JWTError, jwt
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.core.config import settings
from app.core.logging import get_logger
from app.models.super_admin import SuperAdmin
from app.services.dashboard.super_admin_dashboard_service import SuperAdminDashboardService

router = APIRouter()
logger = get_logger(__name__)

# Store active WebSocket connections
class DashboardWebSocketManager:
    """Manages WebSocket connections for dashboard updates"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.admin_connections: Dict[int, Set[WebSocket]] = {}  # admin_id -> set of websockets
    
    async def connect(self, websocket: WebSocket, admin_id: int):
        """Add a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        if admin_id not in self.admin_connections:
            self.admin_connections[admin_id] = set()
        self.admin_connections[admin_id].add(websocket)
        logger.info(f"Dashboard WebSocket connected for admin {admin_id}. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket, admin_id: int):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        if admin_id in self.admin_connections:
            self.admin_connections[admin_id].discard(websocket)
            if not self.admin_connections[admin_id]:
                del self.admin_connections[admin_id]
        logger.info(f"Dashboard WebSocket disconnected for admin {admin_id}. Total connections: {len(self.active_connections)}")
    
    async def broadcast_update(self, admin_id: int, data: dict):
        """Send update to all connections for a specific admin"""
        if admin_id in self.admin_connections:
            disconnected = set()
            for websocket in self.admin_connections[admin_id]:
                try:
                    await websocket.send_json(data)
                except Exception as e:
                    logger.warning(f"Failed to send update to WebSocket: {e}")
                    disconnected.add(websocket)
            
            # Clean up disconnected websockets
            for ws in disconnected:
                self.disconnect(ws, admin_id)
    
    async def broadcast_to_all(self, data: dict):
        """Broadcast update to all connected admins"""
        disconnected = set()
        for websocket in self.active_connections:
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.warning(f"Failed to broadcast update: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            # Find admin_id for this websocket
            for admin_id, connections in list(self.admin_connections.items()):
                if ws in connections:
                    self.disconnect(ws, admin_id)
                    break


# Global WebSocket manager instance
websocket_manager = DashboardWebSocketManager()


@router.websocket("/dashboard/ws")
async def websocket_dashboard(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    # Authenticate WebSocket connection
    token = websocket.query_params.get("token") or websocket.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return
    
    db = None
    admin_id = None
    
    try:
        # Authenticate super admin
        db = SessionLocal()
        try:
            # Validate token and get super admin
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                email: str = payload.get("sub")
                if not email:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                    return
                
                # Check if it's a super admin token (super admin tokens have 'super_admin' in scope or we check SuperAdmin table)
                admin = db.query(SuperAdmin).filter(SuperAdmin.email == email).first()
                if not admin or not admin.is_active:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Super admin not found or inactive")
                    return
                admin_id = admin.id
            except (JWTError, Exception) as e:
                logger.warning(f"Dashboard WebSocket authentication failed: {e}")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                return
        finally:
            db.close()
            db = None
        
        # Connect WebSocket
        await websocket_manager.connect(websocket, admin_id)
        
        # Send initial dashboard data
        db = SessionLocal()
        try:
            service = SuperAdminDashboardService(db)
            overview = service.get_overview()
            await websocket.send_json({
                "type": "dashboard_update",
                "data": overview,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        finally:
            db.close()
            db = None
        
        # Listen for messages (heartbeat/ping)
        while True:
            try:
                # Wait for message with timeout (heartbeat)
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0  # 30 second timeout
                )
                
                # Handle ping/pong
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
                elif data.get("type") == "refresh":
                    # Client requested refresh
                    db = SessionLocal()
                    try:
                        service = SuperAdminDashboardService(db)
                        overview = service.get_overview()
                        await websocket.send_json({
                            "type": "dashboard_update",
                            "data": overview,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    finally:
                        db.close()
                        db = None
                        
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except Exception:
                    break  # Connection closed
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in dashboard WebSocket: {e}", exc_info=True)
                break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Dashboard WebSocket error: {e}", exc_info=True)
    finally:
        if admin_id is not None:
            websocket_manager.disconnect(websocket, admin_id)
        if db:
            db.close()


# Background task to periodically broadcast updates
async def broadcast_dashboard_updates():
    """Background task to periodically send dashboard updates to all connected clients"""
    while True:
        try:
            await asyncio.sleep(30)  # Update every 30 seconds
            
            if websocket_manager.active_connections:
                db = SessionLocal()
                try:
                    service = SuperAdminDashboardService(db)
                    overview = service.get_overview()
                    
                    # Broadcast to all connected admins
                    await websocket_manager.broadcast_to_all({
                        "type": "dashboard_update",
                        "data": overview,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                finally:
                    db.close()
        except Exception as e:
            logger.error(f"Error in dashboard broadcast task: {e}", exc_info=True)
            await asyncio.sleep(60)  # Wait longer on error
