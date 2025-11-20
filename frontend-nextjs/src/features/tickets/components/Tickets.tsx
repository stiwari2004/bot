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
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">Loading tickets...</span>
        </div>
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
        <p className="text-gray-600">View and manage incoming tickets from various sources</p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />
            <p className="text-red-800 font-medium">Error</p>
          </div>
          <p className="text-red-700 mt-2 text-sm">{error}</p>
        </div>
      )}

      {/* Filters and Search */}
      <div className="mb-6 space-y-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search tickets..."
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <div>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
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
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
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
      {filteredTickets.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <TicketIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p>No tickets found</p>
          <p className="text-sm mt-2">
            {searchQuery || filterStatus !== 'all' || filterSeverity !== 'all'
              ? 'Try adjusting your filters'
              : 'Tickets will appear here when they are created'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredTickets.map((ticket) => (
            <div
              key={ticket.id}
              onClick={() => setSelectedTicket(ticket.id)}
              className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-medium text-gray-900">{ticket.title}</h3>
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(
                        ticket.status
                      )}`}
                    >
                      {ticket.status}
                    </span>
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(
                        ticket.severity
                      )}`}
                    >
                      {ticket.severity}
                    </span>
                    <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                      {ticket.source}
                    </span>
                  </div>
                  {ticket.description && (
                    <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                      {ticket.description}
                    </p>
                  )}
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>Created: {new Date(ticket.created_at).toLocaleDateString()}</span>
                    {ticket.service && <span>Service: {ticket.service}</span>}
                    {ticket.environment && <span>Env: {ticket.environment}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <ArrowRightIcon className="h-5 w-5 text-gray-400" />
                </div>
              </div>
            </div>
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

