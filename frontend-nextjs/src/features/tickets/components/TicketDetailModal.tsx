'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { PlayIcon, PlusIcon, XMarkIcon, NoSymbolIcon } from '@heroicons/react/24/outline';

import type { TicketDetail } from '@/features/tickets/types';
import { DecisionRecommendationPanel } from './DecisionRecommendationPanel';
import { PatternMatchView } from './PatternMatchView';
import { ContextCorrelationView } from './ContextCorrelationView';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';

interface TicketDetailModalProps {
  ticket: TicketDetail | null;
  loading: boolean;
  onClose: () => void;
  onExecute: (ticketId: number, runbookId: number) => Promise<void>;
  executing: number | null;
  onGenerateRunbook: () => void;
  onRefresh?: () => void;
  onSessionLaunched?: (sessionId: number) => void;
}

export function TicketDetailModal({
  ticket,
  loading,
  onClose,
  onExecute,
  executing,
  onGenerateRunbook,
  onRefresh,
  onSessionLaunched,
}: TicketDetailModalProps) {
  const [mounted, setMounted] = useState(false);
  const [feedbackSubmitting, setFeedbackSubmitting] = useState<number | null>(null);

  useEffect(() => {
    setMounted(true);
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  const handleRunbookNotRelevant = async (runbookId: number) => {
    if (!ticket?.id || !onRefresh) return;
    setFeedbackSubmitting(runbookId);
    try {
      const url = apiConfig.endpoints.decision.runbookFeedback(ticket.id);
      const res = await authFetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ runbook_id: runbookId, matches: false }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as any).detail || `Failed to submit feedback`);
      }
      onRefresh();
    } catch (err) {
      console.error('Runbook feedback failed:', err);
      // Optionally show a toast; for now we don't block
    } finally {
      setFeedbackSubmitting(null);
    }
  };

  if (!mounted) {
    return null;
  }

  const renderModal = (content: ReactNode) =>
    createPortal(
      <div
        className="fixed inset-0 z-[9999] overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
        onClick={onClose}
      >
        <div
          onClick={(e) => e.stopPropagation()}
          className="max-w-4xl w-full max-h-[90vh] overflow-y-auto"
        >
          <Card variant="elevated">
            {content}
          </Card>
        </div>
      </div>,
      document.body
    );

  if (loading) {
    return renderModal(
      <CardContent padding="lg">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
          <span className="ml-4 text-neutral-600 text-lg font-medium">Loading ticket details...</span>
        </div>
      </CardContent>
    );
  }

  if (!ticket) {
    return renderModal(
      <CardContent padding="lg">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-2xl font-bold text-neutral-900">Ticket Details</h3>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <XMarkIcon className="h-6 w-6" />
          </Button>
        </div>
        <div className="text-center py-10">
          <p className="text-error-600 text-lg font-semibold mb-2">Failed to load ticket details</p>
          <p className="text-sm text-neutral-600 mb-6">Please try again.</p>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </CardContent>
    );
  }

  const matchedRunbooks = ticket.matched_runbooks || [];
  const executionSessions = ticket.execution_sessions || [];
  const recommendation = (ticket as any).recommendation || null;
  const metaData = ticket.meta_data && typeof ticket.meta_data === 'object' ? ticket.meta_data : {};
  const noMatchSuggestion = metaData.no_match_suggestion as string | undefined;

  return renderModal(
    <CardContent padding="lg" className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-2xl font-bold text-neutral-900">Ticket Details</h3>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <XMarkIcon className="h-6 w-6" />
        </Button>
      </div>

      <Card variant="elevated">
        <CardHeader>
          <h4 className="font-semibold text-neutral-900">Ticket Information</h4>
        </CardHeader>
        <CardContent padding="md">
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-neutral-600 font-semibold">Title:</span>
              <span className="text-sm font-bold text-neutral-900">{ticket.title || 'N/A'}</span>
            </div>
            {ticket.description && (
              <div>
                <span className="text-sm text-neutral-600 font-semibold block mb-1">Description:</span>
                <p className="text-sm mt-1 whitespace-pre-wrap text-neutral-700 bg-neutral-50 p-3 rounded-lg">{ticket.description}</p>
              </div>
            )}
            <div className="flex justify-between items-center">
              <span className="text-sm text-neutral-600 font-semibold">Status:</span>
              <Badge variant="status" status={ticket.status as any} size="sm">
                {ticket.status || 'Unknown'}
              </Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-neutral-600 font-semibold">Severity:</span>
              <Badge variant="severity" severity={ticket.severity as any} size="sm">
                {ticket.severity || 'Unknown'}
              </Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-neutral-600 font-semibold">Source:</span>
              <span className="text-sm font-medium text-neutral-900">{ticket.source || 'N/A'}</span>
            </div>
            {ticket.classification && (
              <div className="flex justify-between items-center">
                <span className="text-sm text-neutral-600 font-semibold">Classification:</span>
                <Badge
                  variant={ticket.classification === 'false_positive' ? 'warning' : ticket.classification === 'true_positive' ? 'success' : 'secondary'}
                  size="sm"
                >
                  {ticket.classification}
                </Badge>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Decision Making Section */}
      <div className="space-y-4">
        <h4 className="font-semibold text-neutral-900 text-lg">AI Decision Support</h4>
        <DecisionRecommendationPanel
          ticketId={ticket.id}
          onExecute={recommendation?.runbook_id ? () => onExecute(ticket.id, recommendation.runbook_id!) : undefined}
        />
        <PatternMatchView ticketId={ticket.id} />
        <ContextCorrelationView ticketId={ticket.id} />
      </div>

      <Card variant="elevated">
        <CardHeader className="flex flex-row items-center justify-between gap-4 flex-wrap">
          <h4 className="font-semibold text-neutral-900">Matched Runbooks</h4>
          <Button
            variant="secondary"
            size="sm"
            onClick={onGenerateRunbook}
            leftIcon={<PlusIcon className="h-4 w-4" />}
          >
            Run Agent
          </Button>
        </CardHeader>
        <CardContent padding="md">
          {matchedRunbooks.length > 0 ? (
            <div className="space-y-4">
              {matchedRunbooks.map((runbook: any) => (
                <Card key={runbook.id} variant="default">
                  <CardContent padding="md">
                    <div className="flex items-start justify-between mb-3">
                      <h5 className="font-semibold text-neutral-900">{runbook.title}</h5>
                      <Badge variant="primary" size="sm">
                        {((runbook.confidence_score || 0) * 100).toFixed(0)}% match
                      </Badge>
                    </div>
                    <p className="text-sm text-neutral-600 mb-4">{runbook.reasoning || 'No reasoning provided'}</p>
                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => onExecute(ticket.id, runbook.id)}
                        disabled={executing === runbook.id}
                        isLoading={executing === runbook.id}
                        leftIcon={<PlayIcon className="h-4 w-4" />}
                      >
                        {executing === runbook.id ? 'Executing...' : 'Execute Runbook'}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRunbookNotRelevant(runbook.id)}
                        disabled={feedbackSubmitting === runbook.id}
                        leftIcon={<NoSymbolIcon className="h-4 w-4" />}
                        className="text-neutral-600 hover:text-error-600"
                      >
                        {feedbackSubmitting === runbook.id ? 'Submitting...' : 'Not relevant'}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card variant="outlined" className="border-warning-200 bg-warning-50">
              <CardContent padding="md">
                <p className="text-sm text-warning-800 mb-2 font-medium">No matching runbooks found for this ticket.</p>
                {noMatchSuggestion && (
                  <p className="text-sm text-warning-700 mb-4">{noMatchSuggestion}</p>
                )}
                <Button
                  variant="warning"
                  onClick={onGenerateRunbook}
                  leftIcon={<PlusIcon className="h-4 w-4" />}
                >
                  Run Agent
                </Button>
              </CardContent>
            </Card>
          )}
        </CardContent>
      </Card>

      {executionSessions.length > 0 && (
        <Card variant="elevated">
          <CardHeader>
            <h4 className="font-semibold text-neutral-900">Execution History</h4>
          </CardHeader>
          <CardContent padding="md">
            <div className="space-y-3">
              {executionSessions.map((session: any) => (
                <Card key={session.id} variant="default">
                  <CardContent padding="sm">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-semibold text-neutral-900">Session #{session.id}</span>
                        <Badge variant="status" status={session.status as any} size="sm">
                          {session.status || 'Unknown'}
                        </Badge>
                        {session.status === 'waiting_approval' && (
                          <Badge variant="warning" size="sm">
                            ⚠️ Needs Approval
                          </Badge>
                        )}
                      </div>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => {
                          if (onSessionLaunched) {
                            onSessionLaunched(session.id);
                          }
                        }}
                      >
                        View Execution
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </CardContent>
  );
}




