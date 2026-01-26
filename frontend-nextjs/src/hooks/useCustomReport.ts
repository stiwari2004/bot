/**
 * Hook for generating custom reports
 */
import { useState, useCallback } from 'react';
import { apiConfig } from '@/lib/api-config';

export interface CustomReportFilters {
  reportType: string;
  format: 'csv' | 'pdf';
  dateRange: { start: string; end: string };
  tenantIds: number[];
  plan?: string;
  status?: string;
}

interface UseCustomReportOptions {
  token: string | null;
  onExport?: (type: 'overview' | 'tenants' | 'revenue', format: 'csv' | 'pdf') => Promise<void>;
}

export function useCustomReport({ token, onExport }: UseCustomReportOptions) {
  const [filters, setFilters] = useState<CustomReportFilters>({
    reportType: 'overview',
    format: 'pdf',
    dateRange: { start: '', end: '' },
    tenantIds: [],
  });
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateReport = useCallback(async () => {
    if (!token) {
      setError('Not authenticated');
      return;
    }

    setGenerating(true);
    setError(null);

    try {
      // Build filters object
      const filterData: Record<string, any> = {};
      if (filters.dateRange.start) {
        filterData.date_range = filters.dateRange;
      }
      if (filters.tenantIds.length > 0) {
        filterData.tenant_ids = filters.tenantIds;
      }
      if (filters.plan) {
        filterData.plan = filters.plan;
      }
      if (filters.status) {
        filterData.status = filters.status;
      }

      // Generate report via API
      const response = await fetch(apiConfig.endpoints.superAdmin.reporting.generateCustom(), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          report_type: filters.reportType,
          format: filters.format,
          filters: Object.keys(filterData).length > 0 ? filterData : undefined,
        }),
      });

      if (!response.ok) {
        throw new Error(`Report generation failed: ${response.status}`);
      }

      // If onExport callback is provided, use it to trigger the actual export
      if (onExport && ['overview', 'tenants', 'revenue'].includes(filters.reportType)) {
        await onExport(filters.reportType as 'overview' | 'tenants' | 'revenue', filters.format);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate report';
      setError(errorMessage);
      console.error('Custom report error:', err);
    } finally {
      setGenerating(false);
    }
  }, [token, filters, onExport]);

  return {
    filters,
    setFilters,
    generateReport,
    generating,
    error,
  };
}
