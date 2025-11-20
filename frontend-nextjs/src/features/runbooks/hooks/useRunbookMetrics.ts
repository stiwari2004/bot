'use client';

import { useState, useEffect, useCallback } from 'react';
import type { RunbookMetricsData } from '../types/metrics';

export function useRunbookMetrics(runbookId: number, days: number = 30) {
  const [data, setData] = useState<RunbookMetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/v1/analytics/demo/runbook-quality/${runbookId}?days=${days}`);
      if (!response.ok) {
        throw new Error('Failed to fetch metrics');
      }
      const metricsData = await response.json();
      setData(metricsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [runbookId, days]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  return {
    data,
    loading,
    error,
    refetch: fetchMetrics,
  };
}

