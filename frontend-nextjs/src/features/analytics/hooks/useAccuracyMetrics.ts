'use client';

import { useCallback, useEffect, useState } from 'react';
import apiConfig from '@/lib/api-config';

export type AccuracySnapshot = {
  overall: number;
  componentScores: {
    retrieval: number;
    generation: number;
    execution: number;
    resolution: number;
  };
  trend: Array<{ date: string; score: number }>;
  alerts: Array<{ id: string; message: string; severity: 'info' | 'warn' | 'critical' }>;
  runbookPerformance: Array<{
    runbook: string;
    successRate: number;
    executions: number;
    category: string;
  }>;
};

type AccuracyHook = {
  snapshot: AccuracySnapshot | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const fallbackSnapshot: AccuracySnapshot = {
  overall: 87.5,
  componentScores: {
    retrieval: 89,
    generation: 86,
    execution: 91,
    resolution: 85,
  },
  trend: [
    { date: 'Day -4', score: 84 },
    { date: 'Day -3', score: 85 },
    { date: 'Day -2', score: 86 },
    { date: 'Day -1', score: 87 },
    { date: 'Today', score: 87.5 },
  ],
  alerts: [
    { id: 'fp-drift', message: 'False positive detection dropped to 82% on CPU tickets', severity: 'warn' },
    { id: 'exec-spike', message: 'Execution retries increased by 12% today', severity: 'info' },
  ],
  runbookPerformance: [
    { runbook: 'Fix High CPU Utilization', successRate: 94, executions: 128, category: 'Compute' },
    { runbook: 'Restore VPN Connectivity', successRate: 91, executions: 94, category: 'Network' },
    { runbook: 'Cleanup Disk Space', successRate: 88, executions: 76, category: 'Storage' },
    { runbook: 'Restart IIS App Pools', successRate: 79, executions: 52, category: 'Web' },
  ],
};

export function useAccuracyMetrics(): AccuracyHook {
  const [snapshot, setSnapshot] = useState<AccuracySnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(apiConfig.buildUrl('/api/v1/analytics/demo/accuracy'));
      if (!response.ok) {
        throw new Error('Accuracy endpoint unavailable');
      }
      const data = await response.json();
      setSnapshot(data);
    } catch (err) {
      console.warn('[useAccuracyMetrics] Falling back to sample data:', err);
      setSnapshot(fallbackSnapshot);
      setError('Using cached metrics. Live accuracy endpoint unavailable.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  return {
    snapshot,
    loading,
    error,
    refresh: fetchMetrics,
  };
}


