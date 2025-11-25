'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { apiConfig } from '@/lib/api-config';

export interface StepExecutionState {
  step_number: number;
  step_type: string;
  command: string;
  description: string;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  output: string;
  error: string;
  duration_ms?: number;
  started_at?: string;
  completed_at?: string;
}

export interface ExecutionSession {
  id: number;
  status: string;
  runbook_title?: string;
  issue_description?: string;
  current_step?: number;
  started_at?: string;
  completed_at?: string;
  total_duration_minutes?: number;
  steps?: any[];
}

export function useActiveSession(sessionId: number | null) {
  const [execution, setExecution] = useState<ExecutionSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stepStates, setStepStates] = useState<Map<number, StepExecutionState>>(new Map());
  const [wsConnected, setWsConnected] = useState(false);
  const [eventLog, setEventLog] = useState<any[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const outputRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // Fetch initial execution status
  const fetchExecutionStatus = useCallback(async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(apiConfig.endpoints.agent.execution(sessionId));
      if (response.ok) {
        const data = await response.json();
        setExecution(data);
        
        // Initialize step states from execution data
        if (data.steps) {
          const initialStates = new Map<number, StepExecutionState>();
          data.steps.forEach((step: any) => {
            const isCurrentStep = step.step_number === data.current_step;
            const status = step.completed 
              ? (step.success ? 'completed' : 'failed')
              : (isCurrentStep ? 'executing' : 'pending');
            
            console.log(`[fetchExecutionStatus] Initializing step ${step.step_number}:`, {
              status,
              hasOutput: !!step.output,
              outputLength: step.output?.length || 0,
              command: step.command?.substring(0, 50),
            });
            
            initialStates.set(step.step_number, {
              step_number: step.step_number,
              step_type: step.step_type || 'main',
              command: step.command || '',
              description: step.notes || '',
              status,
              output: step.output || '',
              error: step.error || '',
              duration_ms: undefined,
              started_at: step.completed_at ? step.completed_at : undefined,
              completed_at: step.completed_at || undefined,
            });
          });
          setStepStates(initialStates);
          console.log(`[fetchExecutionStatus] Initialized ${initialStates.size} step states`);
        }
        setError(null);
      } else {
        setError('Failed to fetch execution status');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load execution');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (sessionId) {
      setLoading(true);
      fetchExecutionStatus();
    }
  }, [sessionId, fetchExecutionStatus]);

  // Define handleExecutionEvent before WebSocket useEffect
  const handleExecutionEvent = useCallback((event: any) => {
    const stepNumber = event.step_number || event.payload?.step_number;
    console.log('[handleExecutionEvent] Processing event:', event.event || event.event_type, 'step:', stepNumber, event);
    if (!stepNumber) {
      console.warn('[handleExecutionEvent] No step_number found in event:', event);
      return;
    }

    setStepStates((prev) => {
      const newMap = new Map(prev);
      const current: StepExecutionState = newMap.get(stepNumber) || {
        step_number: stepNumber,
        step_type: event.payload?.step_type || 'main',
        command: event.payload?.command || '',
        description: event.payload?.description || '',
        status: 'pending' as const,
        output: '',
        error: '',
        duration_ms: undefined,
        started_at: undefined,
        completed_at: undefined,
      };

      switch (event.event || event.event_type) {
        case 'execution.step.started':
          newMap.set(stepNumber, {
            ...current,
            command: event.payload?.command || current.command,
            description: event.payload?.description || current.description,
            status: 'executing',
            started_at: event.timestamp || new Date().toISOString(),
          });
          break;
        case 'execution.step.output':
          const newOutput = current.output + (event.payload?.output || '');
          console.log(`[handleExecutionEvent] Step ${stepNumber} output chunk:`, event.payload?.output?.substring(0, 100));
          newMap.set(stepNumber, {
            ...current,
            output: newOutput,
            status: current.status === 'pending' ? 'executing' : current.status, // Ensure status is executing if we get output
          });
          // Auto-scroll output
          setTimeout(() => {
            const outputEl = outputRefs.current.get(stepNumber);
            if (outputEl) {
              outputEl.scrollTop = outputEl.scrollHeight;
            }
          }, 10);
          break;
        case 'execution.step.completed':
          newMap.set(stepNumber, {
            ...current,
            status: 'completed',
            output: event.payload?.output || current.output,
            duration_ms: event.payload?.duration_ms,
            completed_at: event.timestamp || new Date().toISOString(),
          });
          break;
        case 'execution.step.failed':
          newMap.set(stepNumber, {
            ...current,
            status: 'failed',
            output: event.payload?.output || current.output,
            error: event.payload?.error || '',
            duration_ms: event.payload?.duration_ms,
            completed_at: event.timestamp || new Date().toISOString(),
          });
          break;
      }

      return newMap;
    });
  }, []);

  // WebSocket connection for real-time events
  useEffect(() => {
    if (!sessionId) return;

    const toWebSocketUrl = (baseUrl: string) => {
      if (baseUrl.startsWith('https://')) {
        return `wss://${baseUrl.slice('https://'.length)}`;
      }
      if (baseUrl.startsWith('http://')) {
        return `ws://${baseUrl.slice('http://'.length)}`;
      }
      return baseUrl;
    };

    const wsUrl = `${toWebSocketUrl(apiConfig.baseUrl)}/api/v1/executions/ws/sessions/${sessionId}`;
    const socket = new WebSocket(wsUrl);
    wsRef.current = socket;

    socket.onopen = () => {
      setWsConnected(true);
      console.log('WebSocket connected for session', sessionId);
    };

    socket.onclose = () => {
      setWsConnected(false);
      console.log('WebSocket disconnected for session', sessionId);
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setWsConnected(false);
    };

    socket.onmessage = (message) => {
      try {
        const data = JSON.parse(message.data);
        console.log('[WebSocket] Received message:', data);
        
        // Add to event log for debugging
        setEventLog((prev) => [...prev.slice(-49), { timestamp: new Date().toISOString(), data }]);
        
        if (Array.isArray(data.events)) {
          console.log(`[WebSocket] Processing ${data.events.length} events`);
          data.events.forEach((event: any) => {
            console.log('[WebSocket] Event:', event.event || event.event_type, 'step:', event.step_number, event);
            handleExecutionEvent(event);
          });
        } else if (data.event) {
          // Single event
          console.log('[WebSocket] Single event:', data.event, 'step:', data.step_number, data);
          handleExecutionEvent(data);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err, message.data);
      }
    };

    return () => {
      socket.close();
      wsRef.current = null;
    };
  }, [sessionId, handleExecutionEvent]);

  // Polling fallback - refresh every 2 seconds if WebSocket is not connected
  useEffect(() => {
    if (!sessionId || wsConnected) return; // Only poll if WebSocket is not connected
    
    const interval = setInterval(() => {
      console.log('[useActiveSession] Polling for updates (WebSocket not connected)');
      fetchExecutionStatus();
    }, 2000);
    
    return () => clearInterval(interval);
  }, [sessionId, wsConnected, fetchExecutionStatus]);

  const formatDuration = (ms?: number) => {
    if (!ms) return '';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return {
    execution,
    loading,
    error,
    stepStates,
    wsConnected,
    eventLog,
    outputRefs,
    formatDuration,
    refresh: fetchExecutionStatus,
  };
}

