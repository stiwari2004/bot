'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiConfig } from '@/lib/api-config';
import type {
  ExecutionMode,
  TicketingConnection,
  TicketingTool,
  InfrastructureConnection,
  Credential,
} from '../types';

export function useSettings() {
  const [executionMode, setExecutionMode] = useState<ExecutionMode | null>(null);
  const [ticketingConnections, setTicketingConnections] = useState<TicketingConnection[]>([]);
  const [availableTools, setAvailableTools] = useState<TicketingTool[]>([]);
  const [infrastructureConnections, setInfrastructureConnections] = useState<InfrastructureConnection[]>([]);
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchExecutionMode = useCallback(async () => {
    try {
      const response = await fetch(apiConfig.endpoints.settings.executionMode());
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
    try {
      const response = await fetch(apiConfig.endpoints.settings.ticketingConnections());
      if (!response.ok) {
        throw new Error('Failed to fetch ticketing connections');
      }
      const data = await response.json();
      setTicketingConnections(data.connections || []);
    } catch (err) {
      console.error('Failed to fetch ticketing connections:', err);
    }
  }, []);

  const fetchInfrastructureConnections = useCallback(async () => {
    try {
      const response = await fetch(apiConfig.endpoints.connectors.infrastructureConnections());
      if (!response.ok) {
        throw new Error('Failed to fetch infrastructure connections');
      }
      const data = await response.json();
      setInfrastructureConnections(data.connections || []);
    } catch (err) {
      console.error('Failed to fetch infrastructure connections:', err);
    }
  }, []);

  const fetchCredentials = useCallback(async () => {
    try {
      const response = await fetch(apiConfig.endpoints.connectors.credentials());
      if (!response.ok) {
        throw new Error('Failed to fetch credentials');
      }
      const data = await response.json();
      setCredentials(data.credentials || []);
    } catch (err) {
      console.error('Failed to fetch credentials:', err);
    }
  }, []);

  const fetchAvailableTools = useCallback(async () => {
    try {
      const response = await fetch(apiConfig.endpoints.settings.ticketingTools());
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
      const response = await fetch(apiConfig.endpoints.settings.executionMode(), {
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
    fetchExecutionMode();
    fetchTicketingConnections();
    fetchAvailableTools();
    fetchInfrastructureConnections();
    fetchCredentials();
    
    // Check for OAuth success/error in URL params and refresh connections
    const params = new URLSearchParams(window.location.search);
    if (params.has('oauth_success') || params.has('oauth_error')) {
      fetchTicketingConnections();
    }
  }, [fetchExecutionMode, fetchTicketingConnections, fetchAvailableTools, fetchInfrastructureConnections, fetchCredentials]);

  return {
    // Data
    executionMode,
    ticketingConnections,
    availableTools,
    infrastructureConnections,
    credentials,
    
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
    
    // Actions
    fetchExecutionMode,
    fetchTicketingConnections,
    fetchInfrastructureConnections,
    fetchCredentials,
    fetchAvailableTools,
    handleModeChange,
  };
}

