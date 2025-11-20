'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { PlayIcon, PlusIcon, XMarkIcon } from '@heroicons/react/24/outline';

import type { TicketDetail } from '@/features/tickets/types';

interface TicketDetailModalProps {
  ticket: TicketDetail | null;
  loading: boolean;
  onClose: () => void;
  onExecute: (ticketId: number, runbookId: number) => Promise<void>;
  executing: number | null;
  onGenerateRunbook: () => void;
  onSessionLaunched?: (sessionId: number) => void;
}

export function TicketDetailModal({
  ticket,
  loading,
  onClose,
  onExecute,
  executing,
  onGenerateRunbook,
  onSessionLaunched,
}: TicketDetailModalProps) {
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
              <span
                className={`text-sm px-2 py-1 rounded ${
                  ticket.classification === 'false_positive'
                    ? 'bg-yellow-100 text-yellow-800'
                    : ticket.classification === 'true_positive'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
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
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium">Session #{session.id}</span>
                  <span className={`text-xs px-2 py-1 rounded ${getStatusColorForModal(session.status || 'unknown')}`}>
                    {session.status || 'Unknown'}
                  </span>
                  {session.status === 'waiting_approval' && (
                    <span className="text-xs px-2 py-1 rounded bg-yellow-100 text-yellow-800 font-medium">
                      ⚠️ Needs Approval
                    </span>
                  )}
                </div>
                <button
                  onClick={() => {
                    if (onSessionLaunched) {
                      onSessionLaunched(session.id);
                    }
                  }}
                  className="text-sm px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  View Execution
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

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

