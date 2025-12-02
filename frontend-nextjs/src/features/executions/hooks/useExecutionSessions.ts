'use client';

import { useCallback, useEffect, useState } from 'react';
import apiConfig from '@/lib/api-config';

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
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(
        apiConfig.buildUrl(`/api/v1/executions/demo/executions?limit=${limit}`)
      );
      if (!response.ok) {
        throw new Error('Failed to load execution sessions');
      }
      const data = await response.json();
      setSessions(data.sessions || []);
    } catch (err) {
      console.error('[useExecutionSessions] Failed to fetch sessions:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch execution sessions');
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





