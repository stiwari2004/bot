"""
WebSocket connection manager for execution sessions
Handles connection lifecycle, cleanup, and notifications
"""
from fastapi import WebSocket, status
from fastapi.exceptions import WebSocketException
from typing import Dict, List, Tuple
from datetime import datetime, timezone
import asyncio
from app.core.logging import get_logger

try:
    from websockets.exceptions import ConnectionClosed
except ImportError:
    ConnectionClosed = Exception  # Fallback if websockets not installed

logger = get_logger(__name__)

# WebSocket configuration constants
WEBSOCKET_IDLE_TIMEOUT = 30 * 60  # 30 minutes in seconds
WEBSOCKET_MAX_CONNECTIONS_PER_SESSION = 10
WEBSOCKET_HEARTBEAT_INTERVAL = 60  # 1 minute

# Store active WebSocket connections with metadata
# Format: {session_id: [(websocket, last_activity_time, user_id), ...]}
active_connections: Dict[int, List[Tuple[WebSocket, datetime, int]]] = {}


class WebSocketManager:
    """Manages WebSocket connections for execution sessions"""
    
    @staticmethod
    def add_connection(session_id: int, websocket: WebSocket, user_id: int) -> bool:
        """
        Add a WebSocket connection for a session
        
        Returns:
            bool: True if connection was added, False if limit reached
        """
        if session_id in active_connections:
            current_connections = len(active_connections[session_id])
            if current_connections >= WEBSOCKET_MAX_CONNECTIONS_PER_SESSION:
                return False
        else:
            active_connections[session_id] = []
        
        current_time = datetime.now(timezone.utc)
        active_connections[session_id].append((websocket, current_time, user_id))
        logger.info(
            f"WebSocket connection established for session {session_id} "
            f"(user {user_id}, total connections: {len(active_connections[session_id])})"
        )
        return True
    
    @staticmethod
    def cleanup_connection(session_id: int, websocket: WebSocket):
        """Remove a WebSocket connection from the active connections"""
        if session_id in active_connections:
            # Remove this specific websocket from the list
            active_connections[session_id] = [
                (ws, last_activity, user_id) 
                for ws, last_activity, user_id in active_connections[session_id]
                if ws != websocket
            ]
            # Remove empty session entries
            if not active_connections[session_id]:
                del active_connections[session_id]
                logger.debug(f"Removed empty connection list for session {session_id}")
    
    @staticmethod
    def update_activity(session_id: int, websocket: WebSocket):
        """Update the last activity time for a WebSocket connection"""
        current_time = datetime.now(timezone.utc)
        if session_id in active_connections:
            for i, (ws, last_activity, uid) in enumerate(active_connections[session_id]):
                if ws == websocket:
                    active_connections[session_id][i] = (ws, current_time, uid)
                    break
    
    @staticmethod
    async def notify_approval_needed(session_id: int, step_number: int):
        """Notify all WebSocket clients that approval is needed for a step"""
        if session_id not in active_connections:
            return
        
        message = {
            "type": "approval_needed",
            "session_id": session_id,
            "step_number": step_number
        }
        
        # Send to all connected clients and clean up dead connections
        current_time = datetime.now(timezone.utc)
        active_conns = []
        
        for ws, last_activity, user_id in active_connections[session_id]:
            try:
                await ws.send_json(message)
                # Update last activity
                active_conns.append((ws, current_time, user_id))
            except (WebSocketException, ConnectionClosed, Exception) as e:
                logger.debug(f"Failed to send message to WebSocket client: {e}")
                # Don't add dead connection back
        
        # Update active connections
        if active_conns:
            active_connections[session_id] = active_conns
        else:
            # No active connections, remove the session
            del active_connections[session_id]
    
    @staticmethod
    async def send_to_session(session_id: int, message: dict):
        """Send a message to all WebSocket clients for a session"""
        if session_id not in active_connections:
            return
        
        current_time = datetime.now(timezone.utc)
        active_conns = []
        
        for ws, last_activity, user_id in active_connections[session_id]:
            try:
                await ws.send_json(message)
                active_conns.append((ws, current_time, user_id))
            except (WebSocketException, ConnectionClosed, Exception) as e:
                logger.debug(f"Failed to send message to WebSocket client: {e}")
        
        if active_conns:
            active_connections[session_id] = active_conns
        else:
            del active_connections[session_id]
    
    @staticmethod
    async def cleanup_idle_connections():
        """Background task to clean up idle WebSocket connections"""
        while True:
            try:
                await asyncio.sleep(WEBSOCKET_HEARTBEAT_INTERVAL)
                current_time = datetime.now(timezone.utc)
                sessions_to_remove = []
                
                for session_id, connections in list(active_connections.items()):
                    active_conns = []
                    for ws, last_activity, user_id in connections:
                        # Check if connection is idle
                        idle_time = (current_time - last_activity).total_seconds()
                        if idle_time > WEBSOCKET_IDLE_TIMEOUT:
                            logger.info(
                                f"Closing idle WebSocket connection for session {session_id} "
                                f"(idle for {idle_time:.0f}s)"
                            )
                            try:
                                await ws.close(
                                    code=status.WS_1008_POLICY_VIOLATION,
                                    reason="Connection timeout"
                                )
                            except Exception:
                                pass  # Connection may already be closed
                        else:
                            # Check if connection is still alive
                            try:
                                # Try to ping the connection
                                await ws.send_json({"type": "ping"})
                                active_conns.append((ws, last_activity, user_id))
                            except Exception:
                                logger.debug(f"Removing dead connection for session {session_id}")
                                # Connection is dead, don't add it back
                    
                    if active_conns:
                        active_connections[session_id] = active_conns
                    else:
                        sessions_to_remove.append(session_id)
                
                # Remove empty sessions
                for session_id in sessions_to_remove:
                    del active_connections[session_id]
                    logger.debug(f"Removed empty connection list for session {session_id}")
                    
            except Exception as e:
                logger.error(f"Error in cleanup_idle_connections: {e}", exc_info=True)

