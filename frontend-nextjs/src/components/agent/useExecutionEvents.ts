'use client';

import { useEffect, useRef, useState } from 'react';
import apiConfig from '@/lib/api-config';

export interface ExecutionEventRecord {
  stream_id?: string;
  event: string;
  payload: any;
  step_number?: number;
  created_at?: string;
}

const toWebSocketUrl = (baseUrl: string) => {
  if (baseUrl.startsWith('https://')) {
    return `wss://${baseUrl.slice('https://'.length)}`;
  }
  if (baseUrl.startsWith('http://')) {
    return `ws://${baseUrl.slice('http://'.length)}`;
  }
  return baseUrl;
};

const normalizeBatch = (rawEvents: any[]): ExecutionEventRecord[] => {
  return rawEvents
    .map((evt) => {
      if (!evt) return null;
      const created =
        evt.created_at ||
        evt.timestamp ||
        evt.payload?.timestamp ||
        (typeof evt.payload?.created_at === 'string'
          ? evt.payload.created_at
          : undefined);
      return {
        stream_id: evt.stream_id,
        event: evt.event || evt.event_type || 'event',
        payload: evt.payload ?? {},
        step_number: evt.step_number,
        created_at: created,
      } as ExecutionEventRecord;
    })
    .filter(Boolean) as ExecutionEventRecord[];
};

export function useExecutionEvents(
  sessionId: number | null,
  enabled: boolean
): { events: ExecutionEventRecord[]; connected: boolean } {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<ExecutionEventRecord[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    setEvents([]);
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId || !enabled) {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setConnected(false);
      return;
    }

    const wsUrl = `${toWebSocketUrl(apiConfig.baseUrl)}/api/v1/executions/ws/sessions/${sessionId}`;
    const socket = new WebSocket(wsUrl);
    wsRef.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onerror = () => setConnected(false);
    socket.onmessage = (message) => {
      try {
        const parsed = JSON.parse(message.data);
        if (Array.isArray(parsed.events) && parsed.events.length > 0) {
          setEvents(normalizeBatch(parsed.events));
        }
      } catch (error) {
        console.warn('Failed to parse execution event message', error);
      }
    };

    return () => {
      socket.close();
      wsRef.current = null;
    };
  }, [sessionId, enabled]);

  return { events, connected };
}



