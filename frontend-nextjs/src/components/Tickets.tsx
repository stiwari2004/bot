'use client';

import { useState, useEffect, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import {
  TicketIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  PlayIcon,
  DocumentTextIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  ArrowRightIcon,
  XMarkIcon,
  InformationCircleIcon,
  PlusIcon,
} from '@heroicons/react/24/outline';
import { RunbookGenerator } from '@/components/RunbookGenerator';
import { apiConfig } from '@/lib/api-config';

interface Ticket {
  id: number;
  source: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  classification: string | null;
  classification_confidence: string | null;
  environment: string;
  service: string | null;
  created_at: string;
  analyzed_at: string | null;
  resolved_at: string | null;
}

interface MatchedRunbook {
  id: number;
  title: string;
  confidence_score: number;
  reasoning: string;
}

interface TicketDetail extends Ticket {
  meta_data: any;
  matched_runbooks: MatchedRunbook[];
  execution_sessions: Array<{
    id: number;
    status: string;
    created_at: string;
  }>;
}

interface TicketsProps {
  onSessionLaunched?: (sessionId: number) => void;
}

export function Tickets({ onSessionLaunched }: TicketsProps) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTicket, setSelectedTicket] = useState<number | null>(null);
  const [ticketDetail, setTicketDetail] = useState<TicketDetail | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [executing, setExecuting] = useState<number | null>(null);
  const [showGenerateRunbook, setShowGenerateRunbook] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    fetchTickets();
    // Poll for updates every 10 seconds
    const interval = setInterval(fetchTickets, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedTicket) {
      fetchTicketDetail(selectedTicket);
    }
  }, [selectedTicket]);

  const fetchTickets = async () => {
    try {
      const response = await fetch(
        apiConfig.endpoints.tickets.list({ limit: 100 })
      );
      if (!response.ok) {
        // Try to parse error response as JSON first
        let errorMessage = `Failed to fetch tickets: ${response.status}`;
        try {
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            const errorData = await response.json();
            errorMessage = errorData?.detail || errorData?.message || errorMessage;
          } else {
            // If not JSON, read as text to avoid JSON parse error
            const errorText = await response.text();
            console.error('Non-JSON error response:', errorText.substring(0, 200));
            errorMessage = `Server error: ${response.status}`;
          }
        } catch (parseErr) {
          // If parsing fails, use default message
          console.error('Error parsing error response:', parseErr);
        }
        throw new Error(errorMessage);
      }
      
      // Check if response is JSON before parsing
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
  };

  const checkForExistingRunbook = async (issueDescription: string): Promise<MatchedRunbook | null> => {
    try {
      // Try to generate a runbook - if it returns 409, we have a duplicate
      const url = apiConfig.endpoints.runbooks.generateAgent();
      const params = new URLSearchParams({
        issue_description: issueDescription,
        service: 'auto',
        env: 'prod',
        risk: 'low',
      });

      const response = await fetch(`${url}?${params.toString()}`, { method: 'POST' });
      
      if (response.status === 409) {
        // Duplicate found - extract existing runbook info
        const errorData = await response.json();
        if (errorData?.detail?.existing_runbook_id) {
          return {
            id: errorData.detail.existing_runbook_id,
            title: errorData.detail.existing_runbook_title || 'Existing Runbook',
            confidence_score: 1.0, // Perfect match since it's a duplicate
            reasoning: 'Existing runbook found for this issue',
          };
        }
      }
      return null;
    } catch (err) {
      console.error('Error checking for existing runbook:', err);
      return null;
    }
  };

  const fetchTicketDetail = async (ticketId: number) => {
    setLoadingDetail(true);
    setTicketDetail(null); // Clear previous ticket detail
    try {
      console.log('Fetching ticket detail for ID:', ticketId);
      const response = await fetch(apiConfig.endpoints.tickets.detail(ticketId));
      console.log('Ticket detail response status:', response.status);
      if (!response.ok) {
        // Try to parse error response as JSON first
        let errorMessage = `Failed to fetch ticket details: ${response.status}`;
        try {
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            const errorData = await response.json();
            errorMessage = errorData?.detail || errorData?.message || errorMessage;
          } else {
            // If not JSON, read as text to avoid JSON parse error
            const errorText = await response.text();
            console.error('Non-JSON error response:', errorText.substring(0, 200));
            errorMessage = `Server error: ${response.status}`;
          }
        } catch (parseErr) {
          console.error('Error parsing error response:', parseErr);
        }
        throw new Error(errorMessage);
      }
      
      // Check if response is JSON before parsing
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        console.error('Non-JSON response received:', text.substring(0, 200));
        throw new Error('Server returned non-JSON response');
      }
      
      const data = await response.json();
      console.log('Ticket detail data received:', data);
      
      // Check for existing runbook based on ticket title/description
      const issueDescription = `${data.title}${data.description ? '\n\n' + data.description : ''}`;
      const existingRunbook = await checkForExistingRunbook(issueDescription);
      
      if (existingRunbook) {
        // Add existing runbook to matched_runbooks
        if (!data.matched_runbooks) {
          data.matched_runbooks = [];
        }
        // Check if it's not already in the list
        const alreadyExists = data.matched_runbooks.some((rb: MatchedRunbook) => rb.id === existingRunbook.id);
        if (!alreadyExists) {
          data.matched_runbooks.unshift(existingRunbook); // Add to beginning
        }
      }
      
      setTicketDetail(data);
    } catch (err) {
      console.error('Failed to fetch ticket details:', err);
      setTicketDetail(null);
    } finally {
      setLoadingDetail(false);
    }
  };

  const inferConnectorType = (ticket: Ticket | TicketDetail | null) => {
    if (!ticket) return 'ssh';
    const env = (ticket.environment || '').toLowerCase();
    if (env.includes('win')) return 'winrm';
    if (env.includes('k8') || env.includes('kubernetes')) return 'kubernetes';
    return 'ssh';
  };

  const extractHostFromDescription = (description?: string | null) => {
    if (!description) return undefined;
    const hostPattern = /\b[a-z0-9]+(?:-[a-z0-9]+){1,}\b/gi;
    const matches = description.match(hostPattern);
    if (!matches) return undefined;
    const prioritized = matches.find((candidate) =>
      /(prod|db|web|app|srv|srv|server)/i.test(candidate)
    );
    return (prioritized || matches[0])?.toLowerCase();
  };

  const buildExecutionMetadata = (ticketId: number) => {
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
  };

  const handleExecuteRunbook = async (ticketId: number, runbookId: number) => {
    setExecuting(runbookId);
    try {
      const metadata = buildExecutionMetadata(ticketId);
      const detailMatch =
        ticketDetail && ticketDetail.id === ticketId ? ticketDetail : null;
      const listMatch =
        tickets.find((item) => item.id === ticketId) ?? (detailMatch || null);

      const response = await fetch(apiConfig.endpoints.executions.createSession(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          runbook_id: runbookId,
          ticket_id: ticketId,
          issue_description: detailMatch?.description || listMatch?.description,
          metadata,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to execute runbook');
      }

      const data = await response.json();
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
      alert(`Failed to execute runbook: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setExecuting(null);
    }
  };

  const getStatusColor = (status: string) => {
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

  const filteredTickets = tickets.filter((ticket) => {
    if (filterStatus !== 'all' && ticket.status !== filterStatus) return false;
    if (filterSeverity !== 'all' && ticket.severity !== filterSeverity) return false;
    if (searchQuery && !ticket.title.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !(ticket.description || '').toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-gray-600">Loading tickets...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-center gap-2">
          <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />
          <p className="text-red-800 font-medium">Error loading tickets</p>
        </div>
        <p className="text-red-700 mt-2 text-sm">{error}</p>
        <button
          onClick={fetchTickets}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2 flex items-center">
          <TicketIcon className="h-7 w-7 mr-2 text-blue-600" />
          Tickets
        </h2>
        <p className="text-gray-600">
          View all tickets from connected ticketing tools. Tickets are automatically ingested via webhooks.
        </p>
        <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-start gap-2">
            <InformationCircleIcon className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium">Configure ticketing tool connections in Settings & Connections</p>
              <p className="text-xs mt-1">Once connected, tickets will appear here automatically</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-6 bg-white p-4 rounded-lg border border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search
            </label>
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search tickets..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Status
            </label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
            >
              <option value="all">All Statuses</option>
              <option value="open">Open</option>
              <option value="analyzing">Analyzing</option>
              <option value="in_progress">In Progress</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
              <option value="escalated">Escalated</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Severity
            </label>
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tickets List */}
      <div className="space-y-4">
        {filteredTickets.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
            <TicketIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No tickets found</p>
            {tickets.length === 0 && (
              <p className="text-gray-500 text-sm mt-2">
                Upload tickets via CSV or create them via API to get started.
              </p>
            )}
          </div>
        ) : (
          filteredTickets.map((ticket) => (
            <div
              key={ticket.id}
              className="bg-white border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => setSelectedTicket(ticket.id)}
            >
              <div className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {ticket.title}
                      </h3>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(ticket.status)}`}>
                        {ticket.status}
                      </span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(ticket.severity)}`}>
                        {ticket.severity}
                      </span>
                    </div>
                    {ticket.description && (
                      <p className="text-gray-600 text-sm mb-3 line-clamp-2">
                        {ticket.description}
                      </p>
                    )}
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>Source: {ticket.source}</span>
                      {ticket.service && <span>Service: {ticket.service}</span>}
                      <span>Env: {ticket.environment}</span>
                      {ticket.classification && (
                        <span className={`px-2 py-1 rounded ${
                          ticket.classification === 'false_positive' ? 'bg-yellow-100 text-yellow-800' :
                          ticket.classification === 'true_positive' ? 'bg-green-100 text-green-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {ticket.classification}
                        </span>
                      )}
                      <span>
                        {new Date(ticket.created_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedTicket(ticket.id);
                    }}
                    className="ml-4 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2"
                  >
                    View Details
                    <ArrowRightIcon className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Ticket Detail Modal */}
      {selectedTicket && (
        <TicketDetailModal
          ticket={ticketDetail}
          loading={loadingDetail}
          onClose={() => {
            setSelectedTicket(null);
            setTicketDetail(null);
          }}
          onExecute={handleExecuteRunbook}
          executing={executing}
          onGenerateRunbook={() => {
            console.log('Generate runbook clicked, setting showGenerateRunbook to true');
            setShowGenerateRunbook(true);
          }}
        />
      )}

      {/* Generate Runbook Modal */}
      {showGenerateRunbook && (ticketDetail || selectedTicket) && (
        <GenerateRunbookModal
          ticket={ticketDetail || tickets.find(t => t.id === selectedTicket) || null}
          onClose={() => {
            console.log('Closing GenerateRunbookModal');
            setShowGenerateRunbook(false);
            fetchTickets();
            if (selectedTicket) {
              fetchTicketDetail(selectedTicket);
            }
          }}
        />
      )}
    </div>
  );
}

interface TicketDetailModalProps {
  ticket: TicketDetail | null;
  loading: boolean;
  onClose: () => void;
  onExecute: (ticketId: number, runbookId: number) => Promise<void>;
  executing: number | null;
  onGenerateRunbook: () => void;
}

function TicketDetailModal({ ticket, loading, onClose, onExecute, executing, onGenerateRunbook }: TicketDetailModalProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  if (!mounted) {
    return null;
  }

  const renderModal = (content: ReactNode) =>
    createPortal(
      <div
        className="fixed inset-0 z-[9999] overflow-y-auto bg-black bg-opacity-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <div
          className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {content}
        </div>
      </div>,
      document.body
    );

  if (loading) {
    return renderModal(
      <div className="p-6">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
          <span className="ml-4 text-gray-600 text-lg">Loading ticket details...</span>
        </div>
      </div>
    );
  }

  if (!ticket) {
    return renderModal(
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold text-gray-900">Ticket Details</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>
        <div className="text-center py-10">
          <p className="text-red-600 text-lg">Failed to load ticket details</p>
          <p className="text-sm text-gray-600 mt-2">Please try again.</p>
          <button
            onClick={onClose}
            className="mt-6 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  const matchedRunbooks = ticket.matched_runbooks || [];
  const executionSessions = ticket.execution_sessions || [];

  return renderModal(
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-semibold text-gray-900">Ticket Details</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
          <XMarkIcon className="h-6 w-6" />
        </button>
      </div>

      <div>
        <h4 className="font-medium text-gray-900 mb-2">Ticket Information</h4>
        <div className="bg-gray-50 rounded-lg p-4 space-y-2">
          <div className="flex justify-between">
            <span className="text-sm text-gray-600">Title:</span>
            <span className="text-sm font-medium">{ticket.title || 'N/A'}</span>
          </div>
          {ticket.description && (
            <div>
              <span className="text-sm text-gray-600">Description:</span>
              <p className="text-sm mt-1 whitespace-pre-wrap">{ticket.description}</p>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-sm text-gray-600">Status:</span>
            <span className={`text-sm px-2 py-1 rounded ${getStatusColorForModal(ticket.status || 'unknown')}`}>
              {ticket.status || 'Unknown'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-gray-600">Severity:</span>
            <span className={`text-sm px-2 py-1 rounded ${getSeverityColorForModal(ticket.severity || 'unknown')}`}>
              {ticket.severity || 'Unknown'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-gray-600">Source:</span>
            <span className="text-sm">{ticket.source || 'N/A'}</span>
          </div>
          {ticket.classification && (
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Classification:</span>
              <span className={`text-sm px-2 py-1 rounded ${
                ticket.classification === 'false_positive'
                  ? 'bg-yellow-100 text-yellow-800'
                  : ticket.classification === 'true_positive'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-gray-100 text-gray-800'
              }`}>
                {ticket.classification}
              </span>
            </div>
          )}
        </div>
      </div>

      <div>
        <h4 className="font-medium text-gray-900 mb-2">Matched Runbooks</h4>
        {matchedRunbooks.length > 0 ? (
          <div className="space-y-3">
            {matchedRunbooks.map((runbook: any) => (
              <div key={runbook.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <h5 className="font-medium text-gray-900">{runbook.title}</h5>
                  <span className="text-sm font-medium text-blue-600">
                    {((runbook.confidence_score || 0) * 100).toFixed(0)}% match
                  </span>
                </div>
                <p className="text-sm text-gray-600 mb-3">{runbook.reasoning || 'No reasoning provided'}</p>
                <button
                  onClick={() => onExecute(ticket.id, runbook.id)}
                  disabled={executing === runbook.id}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {executing === runbook.id ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      Executing...
                    </>
                  ) : (
                    <>
                      <PlayIcon className="h-4 w-4" />
                      Execute Runbook
                    </>
                  )}
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm text-yellow-800 mb-3">No matching runbooks found for this ticket.</p>
            <button
              onClick={onGenerateRunbook}
              className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
            >
              <PlusIcon className="h-4 w-4" />
              Generate New Runbook
            </button>
          </div>
        )}
      </div>

      {executionSessions.length > 0 && (
        <div>
          <h4 className="font-medium text-gray-900 mb-2">Execution History</h4>
          <div className="space-y-2">
            {executionSessions.map((session: any) => (
              <div key={session.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">Session #{session.id}</span>
                <span className={`text-sm px-2 py-1 rounded ${getStatusColorForModal(session.status || 'unknown')}`}>
                  {session.status || 'Unknown'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Helper functions for TicketDetailModal
function getStatusColorForModal(status: string) {
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
}

function getSeverityColorForModal(severity: string) {
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
}

function getStatusColor(status: string) {
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
}

function getSeverityColor(severity: string) {
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
}

interface GenerateRunbookModalProps {
  ticket: TicketDetail | Ticket | null;
  onClose: () => void;
}

function GenerateRunbookModal({ ticket, onClose }: GenerateRunbookModalProps) {
  const [issueDescription, setIssueDescription] = useState(
    ticket ? `${ticket.title}${ticket.description ? '\n\n' + ticket.description : ''}` : ''
  );
  const [serviceType, setServiceType] = useState(ticket?.service || 'auto');
  const [envType, setEnvType] = useState(ticket?.environment || 'prod');
  const [riskLevel, setRiskLevel] = useState(
    ticket?.severity === 'critical' ? 'high' : ticket?.severity === 'high' ? 'medium' : 'low'
  );
  const [runbook, setRunbook] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  useEffect(() => {
    if (!ticket) return;
    setIssueDescription(`${ticket.title}${ticket.description ? '\n\n' + ticket.description : ''}`);
    setServiceType(ticket.service || 'auto');
    setEnvType(ticket.environment || 'prod');
    setRiskLevel(
      ticket.severity === 'critical' ? 'high' : ticket.severity === 'high' ? 'medium' : 'low'
    );
    setRunbook(null);
    setError(null);
  }, [ticket]);

  if (!ticket) {
    return null; // Don't render if no ticket
  }

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!issueDescription.trim()) return;

    setLoading(true);
    setError(null);
    setRunbook(null);

    try {
      const url = apiConfig.endpoints.runbooks.generateAgent();
      const params = new URLSearchParams({
        issue_description: issueDescription,
        service: serviceType,
        env: envType,
        risk: riskLevel,
      });

      const response = await fetch(`${url}?${params.toString()}`, { method: 'POST' });
      if (!response.ok) {
        // Try to parse error response as JSON first
        let errorMessage = `Runbook generation failed: ${response.status}`;
        let errorData: any = null;
        try {
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            errorData = await response.json();
            // Handle duplicate runbook error (409 Conflict)
            if (response.status === 409 && errorData?.detail) {
              const detail = typeof errorData.detail === 'string' 
                ? errorData.detail 
                : errorData.detail.message || JSON.stringify(errorData.detail);
              errorMessage = `Duplicate runbook detected: ${detail}`;
              // Show existing runbook info if available
              if (errorData.detail?.existing_runbook_id) {
                errorMessage += `\n\nExisting runbook ID: ${errorData.detail.existing_runbook_id}`;
                errorMessage += `\nTitle: ${errorData.detail.existing_runbook_title || 'N/A'}`;
              }
            } else {
              errorMessage = errorData?.detail || errorData?.message || errorMessage;
            }
          } else {
            // If not JSON, read as text to avoid JSON parse error
            const errorText = await response.text();
            console.error('Non-JSON error response:', errorText.substring(0, 200));
            errorMessage = `Server error: ${response.status}. Check console for details.`;
          }
        } catch (parseErr) {
          // If parsing fails, use default message
          console.error('Error parsing error response:', parseErr);
        }
        throw new Error(errorMessage);
      }

      // Check if response is JSON before parsing
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        console.error('Non-JSON response received:', text.substring(0, 200));
        throw new Error('Server returned non-JSON response');
      }

      const data = await response.json();
      setRunbook(data);
    } catch (err) {
      console.error('Error generating runbook:', err);
      setError(err instanceof Error ? err.message : 'Runbook generation failed');
    } finally {
      setLoading(false);
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] overflow-y-auto bg-black bg-opacity-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold text-gray-900">Generate Runbook from Ticket</h3>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {!runbook ? (
            <form onSubmit={handleGenerate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Issue Description *
                </label>
                <textarea
                  value={issueDescription}
                  onChange={(e) => setIssueDescription(e.target.value)}
                  rows={6}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Describe the issue..."
                  required
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Service Type
                  </label>
                  <select
                    value={serviceType}
                    onChange={(e) => setServiceType(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="auto">Auto-detect</option>
                    <option value="database">Database</option>
                    <option value="api">API</option>
                    <option value="infrastructure">Infrastructure</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Environment
                  </label>
                  <select
                    value={envType}
                    onChange={(e) => setEnvType(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="prod">Production</option>
                    <option value="staging">Staging</option>
                    <option value="dev">Development</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Risk Level
                  </label>
                  <select
                    value={riskLevel}
                    onChange={(e) => setRiskLevel(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || !issueDescription.trim()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? 'Generating...' : 'Generate Runbook'}
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-green-800 font-medium">Runbook generated successfully!</p>
                <p className="text-sm text-green-700 mt-1">Runbook ID: {runbook.id}</p>
              </div>
              <div className="border border-gray-200 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-2">{runbook.title}</h4>
                <div className="prose max-w-none text-sm">
                  <pre className="whitespace-pre-wrap bg-gray-50 p-4 rounded border overflow-x-auto">{runbook.body_md}</pre>
                </div>
              </div>
              <div className="flex items-center justify-end gap-3 pt-4 border-t">
                <button
                  onClick={async () => {
                    // Recreate/regenerate runbook
                    setRunbook(null);
                    setError(null);
                    await handleGenerate({ preventDefault: () => {} } as React.FormEvent);
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Recreate
                </button>
                <button
                  onClick={async () => {
                    // Approve runbook
                    try {
                      const response = await fetch(apiConfig.buildUrl(`/api/v1/runbooks/demo/${runbook.id}/approve`), {
                        method: 'POST',
                      });
                      if (!response.ok) {
                        const errorData = await response.json().catch(() => ({ detail: 'Failed to approve runbook' }));
                        throw new Error(errorData.detail || 'Failed to approve runbook');
                      }
                      alert('Runbook approved successfully!');
                      onClose();
                    } catch (err) {
                      setError(err instanceof Error ? err.message : 'Failed to approve runbook');
                    }
                  }}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  Approve
                </button>
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}

