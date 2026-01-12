import { useState, useEffect, useCallback } from 'react';
import { authFetch } from '@/lib/auth-fetch';

interface Prediction {
  id: number;
  prediction_type: string;
  predicted_incident_type?: string;
  confidence_score: number;
  risk_level: string;
  time_horizon_minutes: number;
  predicted_at?: string;
  occurred?: boolean;
  occurred_at?: string;
  false_positive?: boolean;
}

export function usePredictions() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPredictions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await authFetch('/api/v1/predictions/current');
      if (!response.ok) {
        throw new Error('Failed to fetch predictions');
      }
      const data = await response.json();
      setPredictions(data.predictions || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setPredictions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPredictions();
  }, [fetchPredictions]);

  return {
    predictions,
    loading,
    error,
    refresh: fetchPredictions,
  };
}

