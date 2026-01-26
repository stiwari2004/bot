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
  const maxReconnectAttempts = 3; // Reduced from 5 to fail faster
  const wsDisabledRef = useRef(false); // Circuit breaker - disable WS after repeated failures

  const connect = useCallback(() => {
    if (!token || !enabled || wsDisabledRef.current) {
      // WebSocket is disabled due to repeated failures
      return;
    }

    try {
      // Get WebSocket URL - WebSocket connections need to go directly to backend
      // Check if we have a backend URL configured, otherwise try to infer it
      let wsUrl = apiConfig.endpoints.superAdmin.dashboard.websocket();
      
      // If baseUrl is empty, try to use backend URL from env or infer from API calls
      if (!apiConfig.baseUrl || apiConfig.baseUrl === '') {
        // Try to get backend URL from environment or use current host
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || '';
        if (backendUrl) {
          const protocol = backendUrl.startsWith('https') ? 'wss:' : 'ws:';
          const host = backendUrl.replace(/^https?:\/\//, '').replace(/\/$/, '');
          wsUrl = `${protocol}//${host}${wsUrl}`;
        } else {
          // Fallback: try to connect through current host (may not work in dev)
          const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
          const host = window.location.host;
          // In development, backend might be on a different port
          // Try to detect if we're in dev mode and use appropriate port
          const isDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
          if (isDev) {
            // In dev, backend is typically on port 8000
            const backendPort = process.env.NEXT_PUBLIC_BACKEND_PORT || '8000';
            const hostname = window.location.hostname;
            wsUrl = `${protocol}//${hostname}:${backendPort}${wsUrl}`;
          } else {
            // In production, try same host
            const host = window.location.host;
            wsUrl = `${protocol}//${host}${wsUrl}`;
          }
        }
      } else {
        // baseUrl is set, convert http/https to ws/wss
        const protocol = apiConfig.baseUrl.startsWith('https') ? 'wss:' : 'ws:';
        const host = apiConfig.baseUrl.replace(/^https?:\/\//, '').replace(/\/$/, '');
        wsUrl = `${protocol}//${host}${wsUrl}`;
      }
      
      wsUrl = `${wsUrl}?token=${encodeURIComponent(token)}`;
      if (process.env.NODE_ENV === 'development') {
        console.debug('Connecting to WebSocket:', wsUrl.replace(/token=[^&]+/, 'token=***'));
      }
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (process.env.NODE_ENV === 'development') {
          console.debug('Dashboard WebSocket connected');
        }
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
        // WebSocket errors are expected if backend is not accessible
        // Log at debug level since we have polling fallback
        if (process.env.NODE_ENV === 'development') {
          console.debug('Dashboard WebSocket connection error (falling back to polling):', error);
        }
        setIsConnected(false);
        // Don't call onError for connection errors - they're expected if backend is not accessible
        // Only call onError for actual application errors
      };

      ws.onclose = (event) => {
        if (process.env.NODE_ENV === 'development') {
          console.debug('Dashboard WebSocket closed', { code: event.code, reason: event.reason, wasClean: event.wasClean });
        }
        setIsConnected(false);
        
        // Codes 1005 (No Status) and 1006 (Abnormal Closure) usually mean connection failed
        // Don't try to reconnect for these - they indicate the backend isn't accessible
        const isConnectionFailure = event.code === 1005 || event.code === 1006 || event.code === 1000;
        
        if (isConnectionFailure || reconnectAttempts.current >= maxReconnectAttempts) {
          // Disable WebSocket after max attempts or connection failures
          wsDisabledRef.current = true;
          reconnectAttempts.current = 0; // Reset for future attempts
          if (process.env.NODE_ENV === 'development') {
            console.debug('WebSocket disabled - using polling fallback');
          }
          // Don't call onError - this is expected behavior when backend isn't directly accessible
          return;
        }
        
        // Only attempt to reconnect for other error codes and if we haven't exceeded max attempts
        if (!event.wasClean && reconnectAttempts.current < maxReconnectAttempts && enabled) {
          reconnectAttempts.current += 1;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000); // Max 10s delay
          if (process.env.NODE_ENV === 'development') {
            console.debug(`Reconnecting WebSocket in ${delay}ms (attempt ${reconnectAttempts.current}/${maxReconnectAttempts})`);
          }
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
    // Don't reset wsDisabledRef here - let it persist so we don't keep trying
  }, []);

  const sendRefresh = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'refresh' }));
    }
  }, []);

  useEffect(() => {
    // Reset disabled flag when token or enabled changes (user might have fixed connection)
    if (enabled && token) {
      wsDisabledRef.current = false;
      reconnectAttempts.current = 0;
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
