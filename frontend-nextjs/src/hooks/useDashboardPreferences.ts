import { useState, useEffect, useCallback } from 'react';
import { apiConfig } from '@/lib/api-config';

interface DashboardPreferences {
  widgets: {
    [key: string]: {
      enabled: boolean;
      order: number;
    };
  };
  refresh_interval: number;
  auto_refresh: boolean;
}

const defaultPreferences: DashboardPreferences = {
  widgets: {
    summary_cards: { enabled: true, order: 0 },
    revenue: { enabled: true, order: 1 },
    usage_metrics: { enabled: true, order: 2 },
    alerts: { enabled: true, order: 3 },
    plan_distribution: { enabled: true, order: 4 },
  },
  refresh_interval: 30000,
  auto_refresh: true,
};

export function useDashboardPreferences(token: string | null) {
  const [preferences, setPreferences] = useState<DashboardPreferences>(defaultPreferences);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPreferences = useCallback(async () => {
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const response = await fetch(apiConfig.endpoints.superAdmin.dashboard.preferences(), {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch preferences: ${response.status}`);
      }

      const data = await response.json();
      setPreferences(data.preferences || defaultPreferences);
    } catch (err) {
      console.error('Error fetching preferences:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch preferences');
      // Use default preferences on error
      setPreferences(defaultPreferences);
    } finally {
      setLoading(false);
    }
  }, [token]);

  const savePreferences = useCallback(async (newPreferences: Partial<DashboardPreferences>) => {
    if (!token) {
      return false;
    }

    try {
      const updatedPreferences = { ...preferences, ...newPreferences };
      const response = await fetch(apiConfig.endpoints.superAdmin.dashboard.preferences(), {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatedPreferences),
      });

      if (!response.ok) {
        throw new Error(`Failed to save preferences: ${response.status}`);
      }

      const data = await response.json();
      setPreferences(data.preferences || updatedPreferences);
      return true;
    } catch (err) {
      console.error('Error saving preferences:', err);
      setError(err instanceof Error ? err.message : 'Failed to save preferences');
      return false;
    }
  }, [token, preferences]);

  useEffect(() => {
    fetchPreferences();
  }, [fetchPreferences]);

  return {
    preferences,
    loading,
    error,
    savePreferences,
    refetch: fetchPreferences,
  };
}
