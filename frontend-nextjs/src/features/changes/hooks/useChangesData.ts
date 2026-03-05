'use client';

import { useState, useEffect, useCallback } from 'react';
import { authFetch } from '@/lib/auth-fetch';
import { apiConfig } from '@/lib/api-config';

export interface ChangeTicket {
  id: number;
  tenant_id: number;
  external_id: string;
  source: string;
  title: string;
  description?: string;
  change_type?: string;
  status: string;
  start_time: string;
  end_time: string;
  affected_services?: string[];
  affected_environments?: string[];
  suppression_enabled: boolean;
  created_at: string;
  updated_at?: string;
}

export interface SuppressedTicket {
  id: number;
  title: string;
  severity: string;
  environment: string;
  service?: string;
  suppressed_at: string;
  suppression_reason?: string;
  change_ticket?: ChangeTicket;
}

export function useChangesData() {
  const [changes, setChanges] = useState<ChangeTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedChange, setSelectedChange] = useState<number | null>(null);
  const [suppressedTickets, setSuppressedTickets] = useState<SuppressedTicket[]>([]);
  const [loadingSuppressed, setLoadingSuppressed] = useState(false);

  const fetchChanges = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch only active changes (activeOnly=true filters for scheduled/in_progress)
      const response = await authFetch(
        apiConfig.endpoints.changeTickets.list(undefined, true)
      );
      
      if (!response.ok) {
        throw new Error('Failed to fetch changes');
      }
      
      const data = await response.json();
      
      // Additional filter: exclude completed, review, cancelled status
      const activeChanges = (data || []).filter(
        (change: ChangeTicket) => 
          change.status === 'scheduled' || change.status === 'in_progress'
      );
      
      setChanges(activeChanges);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch changes');
      setChanges([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSuppressedTickets = useCallback(async (changeTicketId?: number) => {
    try {
      setLoadingSuppressed(true);
      const response = await authFetch(
        apiConfig.endpoints.changeTickets.suppressedTickets(changeTicketId)
      );
      
      if (!response.ok) {
        throw new Error('Failed to fetch suppressed tickets');
      }
      
      const data = await response.json();
      setSuppressedTickets(data || []);
    } catch (err) {
      console.error('Failed to fetch suppressed tickets:', err);
      setSuppressedTickets([]);
    } finally {
      setLoadingSuppressed(false);
    }
  }, []);

  const unsuppressTickets = useCallback(async (changeTicketId: number) => {
    try {
      const response = await authFetch(
        apiConfig.endpoints.changeTickets.unsuppressTickets(changeTicketId),
        { method: 'POST' }
      );
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to unsuppress tickets');
      }
      
      // Refresh data
      await fetchChanges();
      if (selectedChange === changeTicketId) {
        await fetchSuppressedTickets(changeTicketId);
      }
      
      return true;
    } catch (err) {
      console.error('Failed to unsuppress tickets:', err);
      throw err;
    }
  }, [fetchChanges, fetchSuppressedTickets, selectedChange]);

  useEffect(() => {
    fetchChanges();
    // Poll for updates every 10 seconds so new changes are detected automatically
    const interval = setInterval(fetchChanges, 10000);
    return () => clearInterval(interval);
  }, [fetchChanges]);

  useEffect(() => {
    if (selectedChange) {
      fetchSuppressedTickets(selectedChange);
    } else {
      setSuppressedTickets([]);
    }
  }, [selectedChange, fetchSuppressedTickets]);

  return {
    changes,
    loading,
    error,
    selectedChange,
    setSelectedChange,
    suppressedTickets,
    loadingSuppressed,
    fetchChanges,
    fetchSuppressedTickets,
    unsuppressTickets,
  };
}

