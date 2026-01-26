/**
 * Hook for managing scheduled reports
 */
import { useState, useEffect, useCallback } from 'react';
import { apiConfig } from '@/lib/api-config';

export interface ScheduledReport {
  id: number;
  name: string;
  description?: string;
  report_type: string;
  format: string;
  frequency: string;
  schedule_config: Record<string, any>;
  recipients: string[];
  filters: Record<string, any>;
  is_active: boolean;
  last_run_at?: string;
  next_run_at?: string;
  created_by_id: number;
  created_at: string;
  updated_at?: string;
}

interface UseScheduledReportsOptions {
  token: string | null;
  autoFetch?: boolean;
}

export function useScheduledReports({ token, autoFetch = true }: UseScheduledReportsOptions) {
  const [reports, setReports] = useState<ScheduledReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReports = useCallback(async () => {
    if (!token) return;

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.reporting.scheduledReports(), {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch scheduled reports: ${response.status}`);
      }

      const data = await response.json();
      setReports(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch scheduled reports';
      setError(errorMessage);
      console.error('Error fetching scheduled reports:', err);
    } finally {
      setLoading(false);
    }
  }, [token]);

  const createReport = useCallback(async (reportData: {
    name: string;
    description?: string;
    report_type: string;
    format: string;
    frequency: string;
    schedule_config: Record<string, any>;
    recipients: string[];
    filters?: Record<string, any>;
  }) => {
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(apiConfig.endpoints.superAdmin.reporting.createScheduled(), {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(reportData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create scheduled report');
    }

    const newReport = await response.json();
    setReports(prev => [newReport, ...prev]);
    return newReport;
  }, [token]);

  const updateReport = useCallback(async (reportId: number, updates: Partial<{
    name: string;
    description?: string;
    report_type: string;
    format: string;
    frequency: string;
    schedule_config: Record<string, any>;
    recipients: string[];
    filters?: Record<string, any>;
    is_active: boolean;
  }>) => {
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(apiConfig.endpoints.superAdmin.reporting.updateScheduled(reportId), {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update scheduled report');
    }

    const updatedReport = await response.json();
    setReports(prev => prev.map(r => r.id === reportId ? updatedReport : r));
    return updatedReport;
  }, [token]);

  const deleteReport = useCallback(async (reportId: number) => {
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(apiConfig.endpoints.superAdmin.reporting.deleteScheduled(reportId), {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete scheduled report');
    }

    setReports(prev => prev.filter(r => r.id !== reportId));
  }, [token]);

  const executeReport = useCallback(async (reportId: number) => {
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(apiConfig.endpoints.superAdmin.reporting.executeScheduled(reportId), {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to execute scheduled report');
    }

    // Refresh reports to get updated last_run_at
    await fetchReports();
  }, [token, fetchReports]);

  useEffect(() => {
    if (autoFetch && token) {
      fetchReports();
    }
  }, [autoFetch, token, fetchReports]);

  return {
    reports,
    loading,
    error,
    fetchReports,
    createReport,
    updateReport,
    deleteReport,
    executeReport,
  };
}
