'use client';

import { useCallback, useEffect, useState } from 'react';
import apiConfig from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';

export type ExecutionSession = {
  id: number;
  runbook_id: number;
  runbook_title?: string;
  ticket_id?: number | null;
  issue_description?: string;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  total_duration_minutes?: number | null;
};

type ExecutionSessionsHook = {
  sessions: ExecutionSession[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

export function useExecutionSessions(limit = 100): ExecutionSessionsHook {
  const [sessions, setSessions] = useState<ExecutionSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    // Check if user is authenticated before fetching
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    if (!token) {
      setSessions([]);
      setError(null);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const response = await authFetch(
        apiConfig.buildUrl(`/api/v1/executions/demo/executions?limit=${limit}`)
      );
      if (!response.ok) {
        // Handle 401 gracefully
        if (response.status === 401) {
          setSessions([]);
          setError(null);
          setLoading(false);
          return;
        }
        throw new Error('Failed to load execution sessions');
      }
      const data = await response.json();
      setSessions(data.sessions || []);
    } catch (err) {
      console.error('[useExecutionSessions] Failed to fetch sessions:', err);
      // Don't set error for 401
      if (!(err instanceof Error && err.message.includes('401'))) {
        setError(err instanceof Error ? err.message : 'Failed to fetch execution sessions');
      } else {
        setSessions([]);
        setError(null);
      }
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  return {
    sessions,
    loading,
    error,
    refresh: fetchSessions,
  };
}





