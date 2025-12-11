'use client';

import { useState } from 'react';
import {
  TicketIcon,
  MagnifyingGlassIcon,
  ExclamationTriangleIcon,
  ArrowRightIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';
import { TicketDetailModal } from './TicketDetailModal';
import { GenerateRunbookModal } from './GenerateRunbookModal';
import { useTicketsData } from '../hooks/useTicketsData';
import type { Ticket } from '../types';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

interface TicketsProps {
  onSessionLaunched?: (sessionId: number) => void;
}

export function Tickets({ onSessionLaunched }: TicketsProps) {
  const [executing, setExecuting] = useState<number | null>(null);
  const [showGenerateRunbook, setShowGenerateRunbook] = useState(false);

  const {
    tickets,
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
  } = useTicketsData({ onSessionLaunched });

  const handleExecute = async (ticketId: number, runbookId: number) => {
    setExecuting(runbookId);
    try {
      await handleExecuteRunbook(ticketId, runbookId);
    } catch (err) {
      // Error already handled in hook
    } finally {
      setExecuting(null);
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
          <span className="ml-3 text-neutral-600 font-medium">Loading tickets...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-xl bg-gradient-to-br from-primary-100 to-primary-200">
            <TicketIcon className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h2 className="text-3xl font-bold text-neutral-900">Tickets</h2>
            <p className="text-sm text-neutral-600 mt-0.5">View and manage incoming tickets from various sources</p>
          </div>
        </div>
      </div>

      {error && (
        <Card variant="outlined" className="border-error-200 bg-error-50">
          <CardContent padding="md">
            <div className="flex items-center gap-3">
              <ExclamationTriangleIcon className="h-5 w-5 text-error-600 flex-shrink-0" />
              <div>
                <p className="text-error-800 font-semibold">Error</p>
                <p className="text-error-700 text-sm mt-1">{error}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters and Search */}
      <Card>
        <CardContent padding="md">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[250px]">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <MagnifyingGlassIcon className="h-5 w-5 text-neutral-400" />
                </div>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search tickets by title, description, or source..."
                  className="block w-full pl-10 pr-4 py-2.5 border border-neutral-300 rounded-lg leading-5 bg-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all text-neutral-900"
                />
              </div>
            </div>
            <div>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="px-4 py-2.5 border border-neutral-300 rounded-lg bg-white text-neutral-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all font-medium"
              >
                <option value="all">All Statuses</option>
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
                <option value="closed">Closed</option>
              </select>
            </div>
            <div>
              <select
                value={filterSeverity}
                onChange={(e) => setFilterSeverity(e.target.value)}
                className="px-4 py-2.5 border border-neutral-300 rounded-lg bg-white text-neutral-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all font-medium"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tickets List */}
      {filteredTickets.length === 0 ? (
        <Card>
          <CardContent padding="lg">
            <div className="text-center py-12">
              <div className="mx-auto w-16 h-16 rounded-full bg-neutral-100 flex items-center justify-center mb-4">
                <TicketIcon className="h-8 w-8 text-neutral-400" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-900 mb-1">No tickets found</h3>
              <p className="text-sm text-neutral-600">
                {searchQuery || filterStatus !== 'all' || filterSeverity !== 'all'
                  ? 'Try adjusting your filters to see more results'
                  : 'Tickets will appear here when they are created'}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {filteredTickets.map((ticket) => (
            <Card
              key={ticket.id}
              hover
              onClick={() => setSelectedTicket(ticket.id)}
              variant="elevated"
            >
              <CardContent padding="md">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-3 mb-3">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-semibold text-neutral-900 mb-2 line-clamp-1">
                          {ticket.title}
                        </h3>
                        <div className="flex flex-wrap items-center gap-2 mb-3">
                          <Badge variant="status" status={ticket.status as any} size="sm">
                            {ticket.status.replace('_', ' ')}
                          </Badge>
                          <Badge variant="severity" severity={ticket.severity as any} size="sm">
                            {ticket.severity}
                          </Badge>
                          <Badge variant="secondary" size="sm">
                            {ticket.source}
                          </Badge>
                        </div>
                      </div>
                    </div>
                    {ticket.description && (
                      <p className="text-sm text-neutral-600 mb-3 line-clamp-2">
                        {ticket.description}
                      </p>
                    )}
                    <div className="flex flex-wrap items-center gap-4 text-xs text-neutral-500">
                      <span className="flex items-center gap-1">
                        <span className="font-medium">Created:</span>
                        {new Date(ticket.created_at).toLocaleDateString()}
                      </span>
                      {ticket.service && (
                        <span className="flex items-center gap-1">
                          <span className="font-medium">Service:</span>
                          {ticket.service}
                        </span>
                      )}
                      {ticket.environment && (
                        <span className="flex items-center gap-1">
                          <span className="font-medium">Env:</span>
                          {ticket.environment}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex-shrink-0">
                    <div className="p-2 rounded-lg bg-primary-50 text-primary-600">
                      <ArrowRightIcon className="h-5 w-5" />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Ticket Detail Modal */}
      {selectedTicket && (
        <TicketDetailModal
          ticket={ticketDetail}
          loading={loadingDetail}
          onClose={() => setSelectedTicket(null)}
          onExecute={handleExecute}
          executing={executing}
          onGenerateRunbook={() => setShowGenerateRunbook(true)}
          onSessionLaunched={onSessionLaunched}
        />
      )}

      {/* Generate Runbook Modal */}
      {showGenerateRunbook && (ticketDetail || selectedTicket) && (
        <GenerateRunbookModal
          ticket={ticketDetail || tickets.find((t) => t.id === selectedTicket) || null}
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

