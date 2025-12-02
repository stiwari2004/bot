'use client';

import { useState, useEffect, useCallback } from 'react';
import type { Alert, AlertDetail } from '../types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

interface UseAlertsDataProps {
  // No props needed for now
}

export function useAlertsData({}: UseAlertsDataProps = {}) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<number | null>(null);
  const [alertDetail, setAlertDetail] = useState<AlertDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterSource, setFilterSource] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const fetchAlerts = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (filterStatus !== 'all') {
        params.append('status', filterStatus);
      }
      if (filterSource !== 'all') {
        params.append('source', filterSource);
      }
      params.append('limit', '100');

      const response = await fetch(
        `${API_BASE_URL}/api/v1/alerts/alerts?${params.toString()}`
      );
      if (!response.ok) {
        let errorMessage = `Failed to fetch alerts: ${response.status}`;
        try {
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            const errorData = await response.json();
            errorMessage = errorData?.detail || errorData?.message || errorMessage;
          } else {
            const errorText = await response.text();
            console.error('Non-JSON error response:', errorText.substring(0, 200));
            errorMessage = `Server error: ${response.status}`;
          }
        } catch (parseErr) {
          console.error('Error parsing error response:', parseErr);
        }
        throw new Error(errorMessage);
      }
      
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        console.error('Non-JSON response received:', text.substring(0, 200));
        throw new Error('Server returned non-JSON response');
      }
      
      const data = await response.json();
      setAlerts(data.alerts || []);
      setError(null);
    } catch (err) {
      console.error('Error fetching alerts:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch alerts');
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterSource]);

  const fetchAlertDetail = useCallback(async (alertId: number) => {
    setLoadingDetail(true);
    setAlertDetail(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/alerts/alerts/${alertId}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch alert detail: ${response.status}`);
      }
      const data = await response.json();
      setAlertDetail(data);
    } catch (err) {
      console.error('Error fetching alert detail:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch alert detail');
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
    // Poll for updates every 10 seconds
    const interval = setInterval(fetchAlerts, 10000);
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  useEffect(() => {
    if (selectedAlert) {
      fetchAlertDetail(selectedAlert);
    } else {
      setAlertDetail(null);
    }
  }, [selectedAlert, fetchAlertDetail]);

  const filteredAlerts = alerts.filter((alert: Alert) => {
    if (filterStatus !== 'all' && alert.status !== filterStatus) {
      return false;
    }
    if (filterSeverity !== 'all' && alert.severity !== filterSeverity) {
      return false;
    }
    if (filterSource !== 'all' && alert.source !== filterSource) {
      return false;
    }
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        alert.title.toLowerCase().includes(query) ||
        (alert.description && alert.description.toLowerCase().includes(query)) ||
        (alert.service && alert.service.toLowerCase().includes(query)) ||
        (alert.external_id && alert.external_id.toLowerCase().includes(query))
      );
    }
    return true;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'firing':
        return 'bg-red-100 text-red-800';
      case 'resolved':
        return 'bg-green-100 text-green-800';
      case 'acknowledged':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSourceColor = (source: string) => {
    switch (source) {
      case 'prometheus':
        return 'bg-orange-100 text-orange-800';
      case 'datadog':
        return 'bg-purple-100 text-purple-800';
      case 'azure_monitor':
        return 'bg-blue-100 text-blue-800';
      case 'splunk':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const updateAlert = useCallback(async (
    alertId: number,
    status: string,
    notes?: string
  ) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/alerts/alerts/${alertId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status, notes }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData?.detail || `Failed to update alert: ${response.status}`);
      }

      const updatedAlert = await response.json();
      
      // Update local state
      setAlerts((prev) =>
        prev.map((alert) => (alert.id === alertId ? updatedAlert : alert))
      );

      // Refresh detail if this alert is selected
      if (selectedAlert === alertId) {
        setAlertDetail(updatedAlert);
      }

      return updatedAlert;
    } catch (err) {
      console.error('Error updating alert:', err);
      throw err;
    }
  }, [selectedAlert]);

  return {
    alerts,
    loading,
    error,
    selectedAlert,
    setSelectedAlert,
    alertDetail,
    loadingDetail,
    filterStatus,
    setFilterStatus,
    filterSeverity,
    setFilterSeverity,
    filterSource,
    setFilterSource,
    searchQuery,
    setSearchQuery,
    fetchAlerts,
    fetchAlertDetail,
    updateAlert,
    getStatusColor,
    getSeverityColor,
    getSourceColor,
    filteredAlerts,
  };
}

