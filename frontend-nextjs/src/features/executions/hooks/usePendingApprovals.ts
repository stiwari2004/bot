'use client';

import { useCallback, useEffect, useState } from 'react';
import apiConfig from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';

export type PendingApproval = {
  session_id: number;
  runbook_id: number;
  runbook_title: string;
  step_number: number;
  step_type: string;
  command: string;
  issue_description?: string;
  created_at: string;
};

type PendingApprovalsHook = {
  approvals: PendingApproval[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

export function usePendingApprovals(): PendingApprovalsHook {
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchApprovals = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await authFetch(apiConfig.endpoints.agent.pendingApprovals());
      if (!response.ok) {
        const errorText = await response.text().catch(() => '');
        throw new Error(`Failed to fetch pending approvals: ${response.status} ${errorText || ''}`);
      }
      const data = await response.json();
      setApprovals(data.pending_approvals || []);
    } catch (err) {
      console.error('[usePendingApprovals] Failed to fetch approvals:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch approvals');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  return {
    approvals,
    loading,
    error,
    refresh: fetchApprovals,
  };
}





