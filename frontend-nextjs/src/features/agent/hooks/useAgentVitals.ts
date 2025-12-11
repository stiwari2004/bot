'use client';

import { useCallback, useEffect, useState } from 'react';
import apiConfig from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';

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
    // Check if user is authenticated before fetching
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    if (!token) {
      // Not authenticated - set empty state
      setVitals({
        totalDocuments: 0,
        totalChunks: 0,
        totalRunbooks: 0,
        activeTickets: 0,
        pendingApprovals: 0,
        executionsToday: 0,
        successRate: 0,
      });
      setLoading(false);
      setError(null);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Fetch all endpoints, but handle failures gracefully
      const [statsRes, ticketsRes, approvalsRes, executionsRes] = await Promise.allSettled([
        authFetch(`${API_BASE}/api/v1/demo/stats`),
        authFetch(`${API_BASE}/api/v1/tickets/demo/tickets?limit=100&status=open,in_progress,analyzing`),
        authFetch(`${API_BASE}/api/v1/agent/pending-approvals`),
        authFetch(`${API_BASE}/api/v1/executions/demo/executions?limit=100`),
      ]);

      // Parse responses with error handling
      let statsData = { total_documents: 0, total_chunks: 0, total_runbooks: 0 };
      let ticketsData = { tickets: [] };
      let approvalsData = { pending_approvals: [] };
      let executionsData = { sessions: [] };

      try {
        if (statsRes.status === 'fulfilled' && statsRes.value.ok) {
          statsData = await statsRes.value.json();
        }
      } catch (e) {
        console.warn('[useAgentVitals] Failed to parse stats:', e);
      }

      try {
        if (ticketsRes.status === 'fulfilled' && ticketsRes.value.ok) {
          ticketsData = await ticketsRes.value.json();
        }
      } catch (e) {
        console.warn('[useAgentVitals] Failed to parse tickets:', e);
      }

      try {
        if (approvalsRes.status === 'fulfilled' && approvalsRes.value.ok) {
          approvalsData = await approvalsRes.value.json();
        }
      } catch (e) {
        console.warn('[useAgentVitals] Failed to parse pending approvals:', e);
      }

      try {
        if (executionsRes.status === 'fulfilled' && executionsRes.value.ok) {
          executionsData = await executionsRes.value.json();
        }
      } catch (e) {
        console.warn('[useAgentVitals] Failed to parse executions:', e);
      }

      // Log any failures for debugging (but only if not 401 - 401 is expected when not authenticated)
      if (statsRes.status === 'rejected' || (statsRes.status === 'fulfilled' && !statsRes.value.ok && statsRes.value.status !== 401)) {
        console.warn('[useAgentVitals] Failed to fetch stats:', statsRes.status === 'rejected' ? statsRes.reason : statsRes.value.status);
      }
      if (ticketsRes.status === 'rejected' || (ticketsRes.status === 'fulfilled' && !ticketsRes.value.ok && ticketsRes.value.status !== 401)) {
        console.warn('[useAgentVitals] Failed to fetch tickets:', ticketsRes.status === 'rejected' ? ticketsRes.reason : ticketsRes.value.status);
      }
      if (approvalsRes.status === 'rejected' || (approvalsRes.status === 'fulfilled' && !approvalsRes.value.ok && approvalsRes.value.status !== 401)) {
        console.warn('[useAgentVitals] Failed to fetch pending approvals:', approvalsRes.status === 'rejected' ? approvalsRes.reason : approvalsRes.value.status);
      }
      if (executionsRes.status === 'rejected' || (executionsRes.status === 'fulfilled' && !executionsRes.value.ok && executionsRes.value.status !== 401)) {
        console.warn('[useAgentVitals] Failed to fetch executions:', executionsRes.status === 'rejected' ? executionsRes.reason : executionsRes.value.status);
      }

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





