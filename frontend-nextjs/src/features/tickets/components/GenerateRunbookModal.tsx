'use client';

import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { XMarkIcon } from '@heroicons/react/24/outline';

import type { Ticket, TicketDetail } from '@/features/tickets/types';
import { useAgentSession } from '@/features/tickets/hooks/useAgentSession';
import { AgentSetupForm }  from '@/features/tickets/components/agent/AgentSetupForm';
import { AgentRunningLog } from '@/features/tickets/components/agent/AgentRunningLog';
import { AgentStepReview } from '@/features/tickets/components/agent/AgentStepReview';
import { AgentDoneScreen } from '@/features/tickets/components/agent/AgentDoneScreen';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

const PHASE_TITLES: Record<string, string> = {
  setup:   'Solve Incident with Agent',
  running: 'Agent Running…',
  review:  'Review & Save Runbook',
  done:    'Runbook Saved',
};

interface Props {
  ticket: TicketDetail | Ticket | null;
  onClose: () => void;
}

export function GenerateRunbookModal({ ticket, onClose }: Props) {
  const [state, actions] = useAgentSession(ticket);
  const { phase, issueDescription, sessionStatus, logLines,
          steps, weedSet, runbookTitle, agentSummary,
          savedRunbook, saveLoading, error } = state;

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = 'unset'; };
  }, []);

  if (!ticket) return null;

  const handleClose = () => {
    actions.stopPolling();
    onClose();
  };

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={phase === 'setup' ? handleClose : undefined}
    >
      <div onClick={e => e.stopPropagation()} className="max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-bold text-neutral-900">{PHASE_TITLES[phase]}</h3>
              <Button variant="ghost" size="sm" onClick={handleClose}>
                <XMarkIcon className="h-6 w-6" />
              </Button>
            </div>
            {phase !== 'setup' && (
              <p className="mt-1 text-sm text-neutral-500 truncate">
                {issueDescription.slice(0, 100)}{issueDescription.length > 100 ? '…' : ''}
              </p>
            )}
          </CardHeader>

          <CardContent padding="md">
            {phase === 'setup' && (
              <AgentSetupForm
                issueDescription={issueDescription}
                error={error}
                onChange={actions.setIssueDescription}
                onSubmit={actions.startAgent}
                onCancel={handleClose}
              />
            )}

            {phase === 'running' && (
              <AgentRunningLog
                logLines={logLines}
                sessionStatus={sessionStatus}
                error={error}
                onClose={handleClose}
              />
            )}

            {phase === 'review' && (
              <AgentStepReview
                steps={steps}
                weedSet={weedSet}
                agentSummary={agentSummary}
                runbookTitle={runbookTitle}
                saveLoading={saveLoading}
                error={error}
                onToggleWeed={actions.toggleWeed}
                onTitleChange={actions.setRunbookTitle}
                onSave={actions.saveRunbook}
                onDiscard={handleClose}
              />
            )}

            {phase === 'done' && savedRunbook && (
              <AgentDoneScreen runbook={savedRunbook} onClose={handleClose} />
            )}
          </CardContent>
        </Card>
      </div>
    </div>,
    document.body
  );
}
