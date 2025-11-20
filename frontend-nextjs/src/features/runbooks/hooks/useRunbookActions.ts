'use client';

import { useState, useCallback } from 'react';
import type { Runbook } from '../types';

export function useRunbookActions(onRefresh: () => void) {
  const [approving, setApproving] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForceApprove, setShowForceApprove] = useState(false);

  const handleDelete = useCallback(async (id: number, onSuccess?: () => void) => {
    if (!confirm('Are you sure you want to delete this runbook?')) return;

    try {
      const response = await fetch(`/api/v1/runbooks/demo/${id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete runbook');
      }

      await onRefresh();
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete runbook');
    }
  }, [onRefresh]);

  const handleApprove = useCallback(async (id: number, forceApprove: boolean = false) => {
    setApproving(id);
    setError(null);
    setShowForceApprove(false);

    try {
      const url = `/api/v1/runbooks/demo/${id}/approve${forceApprove ? '?force_approval=true' : ''}`;
      const response = await fetch(url, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json();
        if (errorData.detail && typeof errorData.detail === 'object' && errorData.detail.error === 'duplicate_detected') {
          const dupCount = errorData.detail.similar_runbooks?.length || 0;
          setShowForceApprove(true);
          setError(`Duplicate detected: ${dupCount} similar runbook(s) found. Review them or force approve.`);
          setApproving(null);
          return;
        }
        throw new Error(errorData.detail?.message || errorData.detail || 'Failed to approve runbook');
      }

      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve runbook');
    } finally {
      setApproving(null);
    }
  }, [onRefresh]);

  return {
    approving,
    error,
    showForceApprove,
    setError,
    handleDelete,
    handleApprove,
  };
}



