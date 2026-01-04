'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';
import type {
  ExecutionMode,
  TicketingConnection,
  TicketingTool,
  InfrastructureConnection,
  Credential,
  MonitoringConnection,
} from '../types';

export function useSettings() {
  const { token } = useAuth();
  const [executionMode, setExecutionMode] = useState<ExecutionMode | null>(null);
  const [ticketingConnections, setTicketingConnections] = useState<TicketingConnection[]>([]);
  const [availableTools, setAvailableTools] = useState<TicketingTool[]>([]);
  const [infrastructureConnections, setInfrastructureConnections] = useState<InfrastructureConnection[]>([]);
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [monitoringConnections, setMonitoringConnections] = useState<MonitoringConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchExecutionMode = useCallback(async () => {
    try {
      const response = await authFetch(apiConfig.endpoints.settings.executionMode());
      if (!response.ok) {
        throw new Error('Failed to fetch execution mode');
      }
      const data = await response.json();
      setExecutionMode(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch execution mode');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchTicketingConnections = useCallback(async () => {
    if (!token) return;
    try {
      const response = await authFetch(apiConfig.endpoints.settings.ticketingConnections());
      if (!response.ok) {
        throw new Error('Failed to fetch ticketing connections');
      }
      const data = await response.json();
      setTicketingConnections(data.connections || []);
    } catch (err) {
      console.error('Failed to fetch ticketing connections:', err);
    }
  }, [token]);

  const fetchInfrastructureConnections = useCallback(async () => {
    if (!token) return;
    try {
      const response = await authFetch(apiConfig.endpoints.connectors.infrastructureConnections());
      if (!response.ok) {
        throw new Error('Failed to fetch infrastructure connections');
      }
      const data = await response.json();
      setInfrastructureConnections(data.connections || []);
    } catch (err) {
      console.error('Failed to fetch infrastructure connections:', err);
    }
  }, [token]);

  const fetchMonitoringConnections = useCallback(async () => {
    if (!token) return;
    try {
      const response = await authFetch(apiConfig.endpoints.connectors.monitoringConnections());
      if (!response.ok) {
        // Get error details for debugging
        let errorMessage = `Failed to fetch monitoring connections (${response.status})`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (e) {
          errorMessage = `${errorMessage}: ${response.statusText}`;
        }
        console.error('Monitoring connections error:', errorMessage, 'URL:', apiConfig.endpoints.connectors.monitoringConnections());
        throw new Error(errorMessage);
      }
      const data = await response.json();
      setMonitoringConnections(data.connections || []);
    } catch (err) {
      console.error('Failed to fetch monitoring connections:', err);
      // Set empty array on error to prevent UI issues
      setMonitoringConnections([]);
    }
  }, [token]);

  const fetchCredentials = useCallback(async () => {
    if (!token) return;
    try {
      const response = await authFetch(apiConfig.endpoints.connectors.credentials());
      if (!response.ok) {
        throw new Error('Failed to fetch credentials');
      }
      const data = await response.json();
      setCredentials(data.credentials || []);
    } catch (err) {
      console.error('Failed to fetch credentials:', err);
    }
  }, [token]);

  const fetchAvailableTools = useCallback(async () => {
    try {
      const response = await authFetch(apiConfig.endpoints.settings.ticketingTools());
      if (!response.ok) {
        throw new Error('Failed to fetch available tools');
      }
      const data = await response.json();
      setAvailableTools(data.tools || []);
    } catch (err) {
      console.error('Failed to fetch available tools:', err);
    }
  }, []);

  const handleModeChange = useCallback(async (mode: 'hil' | 'auto') => {
    if (executionMode?.mode === mode) return;

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await authFetch(apiConfig.endpoints.settings.executionMode(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mode }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update execution mode');
      }

      const data = await response.json();
      setExecutionMode(data);
      setSuccess(`Execution mode updated to ${mode === 'hil' ? 'Human-in-the-Loop' : 'Auto'}`);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update execution mode');
      console.error('Mode change error:', err);
    } finally {
      setSaving(false);
    }
  }, [executionMode]);

  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return;
    
    fetchExecutionMode();
    fetchTicketingConnections();
    fetchAvailableTools();
    fetchInfrastructureConnections();
    fetchMonitoringConnections();
    fetchCredentials();
    
    // Check for OAuth success/error in URL params and refresh connections
    const params = new URLSearchParams(window.location.search);
    if (params.has('oauth_success') || params.has('oauth_error')) {
      fetchTicketingConnections();
    }
  }, [fetchExecutionMode, fetchTicketingConnections, fetchAvailableTools, fetchInfrastructureConnections, fetchCredentials, fetchMonitoringConnections]);

  return {
    // Data
    executionMode,
    ticketingConnections,
    availableTools,
    infrastructureConnections,
    credentials,
    monitoringConnections,
    
    // State
    loading,
    saving,
    error,
    success,
    
    // Setters
    setError,
    setSuccess,
    setTicketingConnections,
    setInfrastructureConnections,
    setCredentials,
    setMonitoringConnections,
    
    // Actions
    fetchExecutionMode,
    fetchTicketingConnections,
    fetchInfrastructureConnections,
    fetchCredentials,
    fetchMonitoringConnections,
    fetchAvailableTools,
    handleModeChange,
  };
}



