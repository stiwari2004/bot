import { useEffect, useRef, useState, useCallback } from 'react';
import { apiConfig } from '@/lib/api-config';

interface DashboardUpdate {
  type: 'dashboard_update' | 'heartbeat' | 'pong';
  data?: any;
  timestamp: string;
}

interface UseDashboardWebSocketOptions {
  token: string | null;
  enabled?: boolean;
  onUpdate?: (data: any) => void;
  onError?: (error: Error) => void;
}

export function useDashboardWebSocket({
  token,
  enabled = true,
  onUpdate,
  onError,
}: UseDashboardWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (!token || !enabled) {
      return;
    }

    try {
      // Get WebSocket URL - handle both relative and absolute URLs
      let wsUrl = apiConfig.endpoints.superAdmin.dashboard.websocket();
      
      // If baseUrl is empty (relative), use current origin
      if (!apiConfig.baseUrl || apiConfig.baseUrl === '') {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        wsUrl = `${protocol}//${host}${wsUrl}`;
      }
      
      wsUrl = `${wsUrl}?token=${encodeURIComponent(token)}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('Dashboard WebSocket connected');
        setIsConnected(true);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const message: DashboardUpdate = JSON.parse(event.data);
          
          if (message.type === 'dashboard_update' && message.data) {
            setLastUpdate(new Date());
            onUpdate?.(message.data);
          } else if (message.type === 'heartbeat' || message.type === 'pong') {
            // Heartbeat received, connection is alive
            setLastUpdate(new Date());
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          onError?.(error as Error);
        }
      };

      ws.onerror = (error) => {
        console.error('Dashboard WebSocket error:', error);
        setIsConnected(false);
        onError?.(new Error('WebSocket connection error'));
      };

      ws.onclose = () => {
        console.log('Dashboard WebSocket closed');
        setIsConnected(false);
        
        // Attempt to reconnect
        if (reconnectAttempts.current < maxReconnectAttempts && enabled) {
          reconnectAttempts.current += 1;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      onError?.(error as Error);
    }
  }, [token, enabled, onUpdate, onError]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const sendRefresh = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'refresh' }));
    }
  }, []);

  useEffect(() => {
    if (enabled && token) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, token, connect, disconnect]);

  return {
    isConnected,
    lastUpdate,
    sendRefresh,
    reconnect: connect,
  };
}
