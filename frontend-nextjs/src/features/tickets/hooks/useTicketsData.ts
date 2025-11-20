'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiConfig } from '@/lib/api-config';
import type { Ticket, TicketDetail } from '../types';

interface UseTicketsDataProps {
  onSessionLaunched?: (sessionId: number) => void;
}

export function useTicketsData({ onSessionLaunched }: UseTicketsDataProps = {}) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTicket, setSelectedTicket] = useState<number | null>(null);
  const [ticketDetail, setTicketDetail] = useState<TicketDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const fetchTickets = useCallback(async () => {
    try {
      const response = await fetch(
        apiConfig.endpoints.tickets.list({ limit: 100 })
      );
      if (!response.ok) {
        let errorMessage = `Failed to fetch tickets: ${response.status}`;
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
      setTickets(data.tickets || []);
      setError(null);
    } catch (err) {
      console.error('Error fetching tickets:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch tickets');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchTicketDetail = useCallback(async (ticketId: number) => {
    setLoadingDetail(true);
    setTicketDetail(null);
    try {
      const response = await fetch(apiConfig.endpoints.tickets.detail(ticketId));
      if (!response.ok) {
        throw new Error(`Failed to fetch ticket detail: ${response.status}`);
      }
      const data = await response.json();
      setTicketDetail(data);
    } catch (err) {
      console.error('Error fetching ticket detail:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch ticket detail');
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    fetchTickets();
    // Poll for updates every 10 seconds
    const interval = setInterval(fetchTickets, 10000);
    return () => clearInterval(interval);
  }, [fetchTickets]);

  useEffect(() => {
    if (selectedTicket) {
      fetchTicketDetail(selectedTicket);
    } else {
      setTicketDetail(null);
    }
  }, [selectedTicket, fetchTicketDetail]);

  const filteredTickets = tickets.filter((ticket) => {
    if (filterStatus !== 'all' && ticket.status !== filterStatus) {
      return false;
    }
    if (filterSeverity !== 'all' && ticket.severity !== filterSeverity) {
      return false;
    }
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      return (
        ticket.title.toLowerCase().includes(query) ||
        (ticket.description && ticket.description.toLowerCase().includes(query)) ||
        ticket.source.toLowerCase().includes(query)
      );
    }
    return true;
  });

  const inferConnectorType = useCallback((ticket: Ticket | TicketDetail | null) => {
    if (!ticket) return 'ssh';
    const env = (ticket.environment || '').toLowerCase();
    if (env.includes('win')) return 'winrm';
    if (env.includes('k8') || env.includes('kubernetes')) return 'kubernetes';
    return 'ssh';
  }, []);

  const extractHostFromDescription = useCallback((description?: string | null) => {
    if (!description) return undefined;
    const hostPattern = /\b[a-z0-9]+(?:-[a-z0-9]+){1,}\b/gi;
    const matches = description.match(hostPattern);
    if (!matches) return undefined;
    const prioritized = matches.find((candidate) =>
      /(prod|db|web|app|srv|srv|server)/i.test(candidate)
    );
    return (prioritized || matches[0])?.toLowerCase();
  }, []);

  const buildExecutionMetadata = useCallback((ticketId: number) => {
    const detailMatch =
      ticketDetail && ticketDetail.id === ticketId ? ticketDetail : null;
    const listMatch =
      tickets.find((item) => item.id === ticketId) ?? (detailMatch || null);
    const hostFromMeta =
      detailMatch?.meta_data?.configuration_item ||
      detailMatch?.meta_data?.hostname ||
      detailMatch?.meta_data?.server ||
      detailMatch?.meta_data?.ci;
    const fallbackHost =
      extractHostFromDescription(detailMatch?.description) ||
      extractHostFromDescription(listMatch?.description || undefined);

    const metadata: Record<string, any> = {
      ticket_title: listMatch?.title,
      severity: listMatch?.severity,
      environment: listMatch?.environment,
      service: listMatch?.service,
      source: listMatch?.source,
      connector_type: inferConnectorType(listMatch),
      credential_source: detailMatch?.meta_data?.credential_source || 'vault',
      target: undefined,
      ticket_reference: {
        id: ticketId,
      },
    };

    const hostCandidate = hostFromMeta || fallbackHost;
    if (hostCandidate) {
      metadata.target = {
        host: hostCandidate,
        environment: listMatch?.environment,
        service: listMatch?.service,
      };
    }

    if (detailMatch?.meta_data) {
      metadata.ticket_meta = detailMatch.meta_data;
    }

    if (!metadata.target) {
      delete metadata.target;
    }

    if (!metadata.service) {
      delete metadata.service;
    }

    return metadata;
  }, [tickets, ticketDetail, inferConnectorType, extractHostFromDescription]);

  const handleExecuteRunbook = useCallback(async (
    ticketId: number,
    runbookId: number
  ) => {
    console.log(`[Execute] Starting execution for ticket ${ticketId}, runbook ${runbookId}`);
    try {
      const metadata = buildExecutionMetadata(ticketId);
      const detailMatch =
        ticketDetail && ticketDetail.id === ticketId ? ticketDetail : null;
      const listMatch =
        tickets.find((item) => item.id === ticketId) ?? (detailMatch || null);

      const requestBody = {
        runbook_id: runbookId,
        ticket_id: ticketId,
        issue_description: detailMatch?.description || listMatch?.description || detailMatch?.title || listMatch?.title,
        metadata,
      };
      
      console.log(`[Execute] Calling ${apiConfig.endpoints.executions.createSession()}`, requestBody);

      const response = await fetch(apiConfig.endpoints.executions.createSession(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      console.log(`[Execute] Response status: ${response.status}`, response);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
        console.error(`[Execute] Error response:`, errorData);
        throw new Error(errorData.detail || 'Failed to execute runbook');
      }

      const data = await response.json();
      console.log(`[Execute] Success response:`, data);
      const sessionId = data?.id ?? data?.session_id;
      const statusMessage = data?.status ? `Status: ${data.status}` : '';
      alert(
        ['Execution session created!', statusMessage, sessionId ? `Session ID: ${sessionId}` : '']
          .filter(Boolean)
          .join('\n')
      );
      if (sessionId) {
        onSessionLaunched?.(sessionId);
        setSelectedTicket(null);
        setTicketDetail(null);
      }
      
      // Refresh tickets and detail
      await fetchTickets();
      if (selectedTicket === ticketId) {
        await fetchTicketDetail(ticketId);
      }
    } catch (err) {
      console.error(`[Execute] Exception:`, err);
      alert(`Failed to execute runbook: ${err instanceof Error ? err.message : 'Unknown error'}`);
      throw err;
    }
  }, [tickets, ticketDetail, selectedTicket, buildExecutionMetadata, fetchTickets, fetchTicketDetail, onSessionLaunched]);

  const getStatusColor = useCallback((status: string) => {
    switch (status) {
      case 'resolved':
        return 'bg-green-100 text-green-800';
      case 'closed':
        return 'bg-gray-100 text-gray-800';
      case 'escalated':
        return 'bg-red-100 text-red-800';
      case 'in_progress':
        return 'bg-blue-100 text-blue-800';
      case 'analyzing':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  }, []);

  const getSeverityColor = useCallback((severity: string) => {
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
  }, []);

  return {
    tickets: filteredTickets,
    loading,
    error,
    selectedTicket,
    setSelectedTicket,
    ticketDetail,
    loadingDetail,
    filterStatus,
    setFilterStatus,
    filterSeverity,
    setFilterSeverity,
    searchQuery,
    setSearchQuery,
    fetchTickets,
    fetchTicketDetail,
    handleExecuteRunbook,
    getStatusColor,
    getSeverityColor,
    filteredTickets,
  };
}

