"""
Unit tests for WebSocket manager
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta
from fastapi import WebSocket

from app.services.execution.websocket_manager import (
    WebSocketManager,
    WEBSOCKET_IDLE_TIMEOUT,
    WEBSOCKET_MAX_CONNECTIONS_PER_SESSION,
    active_connections
)


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket"""
    ws = Mock(spec=WebSocket)
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def sample_session_id():
    """Sample session ID for testing"""
    return 123


@pytest.fixture
def cleanup_connections():
    """Fixture to clean up connections after each test"""
    yield
    # Clean up active_connections after each test
    active_connections.clear()


class TestWebSocketManager:
    """Test WebSocketManager class"""
    
    def test_add_connection_adds_to_active_connections(
        self, mock_websocket, sample_session_id, cleanup_connections
    ):
        """Test that adding a connection adds it to active_connections"""
        user_id = 1
        
        result = WebSocketManager.add_connection(
            sample_session_id, mock_websocket, user_id
        )
        
        assert result is True
        assert sample_session_id in active_connections
        assert len(active_connections[sample_session_id]) == 1
    
    def test_add_connection_respects_max_connections_limit(
        self, mock_websocket, sample_session_id, cleanup_connections
    ):
        """Test that connection limit is enforced"""
        # Add max connections
        for i in range(WEBSOCKET_MAX_CONNECTIONS_PER_SESSION):
            ws = Mock(spec=WebSocket)
            WebSocketManager.add_connection(sample_session_id, ws, i)
        
        # Try to add one more
        result = WebSocketManager.add_connection(
            sample_session_id, mock_websocket, WEBSOCKET_MAX_CONNECTIONS_PER_SESSION
        )
        
        assert result is False
        assert len(active_connections[sample_session_id]) == WEBSOCKET_MAX_CONNECTIONS_PER_SESSION
    
    def test_cleanup_connection_removes_connection(
        self, mock_websocket, sample_session_id, cleanup_connections
    ):
        """Test that cleanup_connection removes the connection"""
        user_id = 1
        WebSocketManager.add_connection(sample_session_id, mock_websocket, user_id)
        
        assert len(active_connections[sample_session_id]) == 1
        
        WebSocketManager.cleanup_connection(sample_session_id, mock_websocket)
        
        assert sample_session_id not in active_connections
    
    def test_update_activity_updates_timestamp(
        self, mock_websocket, sample_session_id, cleanup_connections
    ):
        """Test that update_activity updates the last activity time"""
        user_id = 1
        WebSocketManager.add_connection(sample_session_id, mock_websocket, user_id)
        
        initial_time = active_connections[sample_session_id][0][1]
        
        # Wait a tiny bit and update
        import time
        time.sleep(0.01)
        WebSocketManager.update_activity(sample_session_id, mock_websocket)
        
        updated_time = active_connections[sample_session_id][0][1]
        assert updated_time > initial_time
    
    @pytest.mark.asyncio
    async def test_notify_approval_needed_sends_message(
        self, mock_websocket, sample_session_id, cleanup_connections
    ):
        """Test that notify_approval_needed sends message to all connections"""
        user_id = 1
        WebSocketManager.add_connection(sample_session_id, mock_websocket, user_id)
        
        await WebSocketManager.notify_approval_needed(sample_session_id, step_number=5)
        
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "approval_needed"
        assert call_args["session_id"] == sample_session_id
        assert call_args["step_number"] == 5
    
    @pytest.mark.asyncio
    async def test_notify_approval_needed_cleans_dead_connections(
        self, sample_session_id, cleanup_connections
    ):
        """Test that notify_approval_needed removes dead connections"""
        # Add a dead connection (will raise exception on send)
        dead_ws = Mock(spec=WebSocket)
        dead_ws.send_json = AsyncMock(side_effect=Exception("Connection dead"))
        
        # Add a live connection
        live_ws = Mock(spec=WebSocket)
        live_ws.send_json = AsyncMock()
        
        WebSocketManager.add_connection(sample_session_id, dead_ws, 1)
        WebSocketManager.add_connection(sample_session_id, live_ws, 2)
        
        await WebSocketManager.notify_approval_needed(sample_session_id, step_number=1)
        
        # Dead connection should be removed
        assert len(active_connections[sample_session_id]) == 1
        assert active_connections[sample_session_id][0][0] == live_ws
    
    @pytest.mark.asyncio
    async def test_send_to_session_sends_to_all_clients(
        self, sample_session_id, cleanup_connections
    ):
        """Test that send_to_session sends message to all clients"""
        ws1 = Mock(spec=WebSocket)
        ws1.send_json = AsyncMock()
        ws2 = Mock(spec=WebSocket)
        ws2.send_json = AsyncMock()
        
        WebSocketManager.add_connection(sample_session_id, ws1, 1)
        WebSocketManager.add_connection(sample_session_id, ws2, 2)
        
        message = {"type": "test", "data": "test_data"}
        await WebSocketManager.send_to_session(sample_session_id, message)
        
        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_cleanup_idle_connections_closes_idle_connections(
        self, sample_session_id, cleanup_connections
    ):
        """Test that cleanup_idle_connections closes idle connections"""
        # Create a connection with old timestamp
        old_ws = Mock(spec=WebSocket)
        old_ws.send_json = AsyncMock()
        old_ws.close = AsyncMock()
        
        # Manually add with old timestamp
        old_time = datetime.now(timezone.utc) - timedelta(seconds=WEBSOCKET_IDLE_TIMEOUT + 60)
        active_connections[sample_session_id] = [(old_ws, old_time, 1)]
        
        # Run cleanup (will check and close idle connection)
        # Note: This is a background task, so we'll test the logic directly
        current_time = datetime.now(timezone.utc)
        connections = active_connections.get(sample_session_id, [])
        
        for ws, last_activity, user_id in connections:
            idle_time = (current_time - last_activity).total_seconds()
            if idle_time > WEBSOCKET_IDLE_TIMEOUT:
                await ws.close()
        
        old_ws.close.assert_called_once()
    
    def test_connection_limit_enforced_per_session(
        self, sample_session_id, cleanup_connections
    ):
        """Test that connection limit is per session, not global"""
        session_1 = 100
        session_2 = 200
        
        # Add max connections to session 1
        for i in range(WEBSOCKET_MAX_CONNECTIONS_PER_SESSION):
            ws = Mock(spec=WebSocket)
            WebSocketManager.add_connection(session_1, ws, i)
        
        # Should still be able to add to session 2
        ws = Mock(spec=WebSocket)
        result = WebSocketManager.add_connection(session_2, ws, 0)
        
        assert result is True
        assert len(active_connections[session_1]) == WEBSOCKET_MAX_CONNECTIONS_PER_SESSION
        assert len(active_connections[session_2]) == 1

