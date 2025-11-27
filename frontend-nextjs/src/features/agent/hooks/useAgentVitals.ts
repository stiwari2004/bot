'use client';

import { useCallback, useEffect, useState } from 'react';
import apiConfig from '@/lib/api-config';

export type AgentVitals = {
  totalDocuments: number;
  totalChunks: number;
  totalRunbooks: number;
  activeTickets: number;
  pendingApprovals: number;
  executionsToday: number;
  successRate: number;
};

type AgentVitalsHook = {
  vitals: AgentVitals | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const API_BASE = apiConfig.baseUrl;

export function useAgentVitals(): AgentVitalsHook {
  const [vitals, setVitals] = useState<AgentVitals | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchVitals = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [statsRes, ticketsRes, approvalsRes, executionsRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/demo/stats`),
        fetch(`${API_BASE}/api/v1/tickets/demo/tickets?limit=100&status=open,in_progress,analyzing`),
        fetch(`${API_BASE}/api/v1/agent/pending-approvals`),
        fetch(`${API_BASE}/api/v1/executions/demo/executions?limit=100`),
      ]);

      if (!statsRes.ok || !ticketsRes.ok || !approvalsRes.ok || !executionsRes.ok) {
        throw new Error('Failed to fetch vitals');
      }

      const statsData = await statsRes.json();
      const ticketsData = await ticketsRes.json();
      const approvalsData = await approvalsRes.json();
      const executionsData = await executionsRes.json();

      const sessions = Array.isArray(executionsData.sessions) ? executionsData.sessions : [];
      const todayString = new Date().toDateString();

      const executionsToday = sessions.filter((session: any) => {
        if (!session?.started_at) return false;
        return new Date(session.started_at).toDateString() === todayString;
      }).length;

      const completedSessions = sessions.filter((session: any) => {
        const status = (session?.status || '').toLowerCase();
        return status === 'completed' || status === 'failed' || status === 'completed_with_errors';
      });

      const successfulSessions = sessions.filter(
        (session: any) => (session?.status || '').toLowerCase() === 'completed'
      );

      const successRate =
        completedSessions.length > 0
          ? Math.round((successfulSessions.length / completedSessions.length) * 100)
          : 0;

      setVitals({
        totalDocuments: statsData.total_documents || 0,
        totalChunks: statsData.total_chunks || 0,
        totalRunbooks: statsData.total_runbooks || 0,
        activeTickets: ticketsData.tickets?.length || 0,
        pendingApprovals: approvalsData.pending_approvals?.length || 0,
        executionsToday,
        successRate,
      });
    } catch (err) {
      console.error('[useAgentVitals] Failed to fetch vitals:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch vitals');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchVitals();
  }, [fetchVitals]);

  return {
    vitals,
    loading,
    error,
    refresh: fetchVitals,
  };
}


