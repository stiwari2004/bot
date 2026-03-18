'use client';

import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { XMarkIcon } from '@heroicons/react/24/outline';

import type { Ticket, TicketDetail } from '@/features/tickets/types';
import { useAgentSession } from '@/features/tickets/hooks/useAgentSession';
import { AgentRunningLog }  from '@/features/tickets/components/agent/AgentRunningLog';
import { AgentPlanApproval } from '@/features/tickets/components/agent/AgentPlanApproval';
import { AgentStepReview }  from '@/features/tickets/components/agent/AgentStepReview';
import { AgentDoneScreen }  from '@/features/tickets/components/agent/AgentDoneScreen';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

const PHASE_TITLES: Record<string, string> = {
  running:   'Agent Running…',
  approving: 'Review & Approve Plan',
  review:    'Review & Save Runbook',
  done:      'Runbook Saved',
};

interface Props {
  ticket: TicketDetail | Ticket | null;
  onClose: () => void;
}

export function GenerateRunbookModal({ ticket, onClose }: Props) {
  const [state, actions] = useAgentSession(ticket);
  const { phase, issueDescription, sessionStatus, logLines,
          planSteps, planDiagnosis, rejectFeedback, approveLoading, rejectLoading,
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
    >
      <div onClick={e => e.stopPropagation()} className="max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <Card variant="elevated">
          {/* Header */}
          <div className="flex items-center justify-between px-6 pt-5 pb-3 border-b border-neutral-100">
            <div className="min-w-0">
              <h3 className="text-xl font-bold text-neutral-900">{PHASE_TITLES[phase]}</h3>
              {issueDescription && (
                <p className="mt-0.5 text-xs text-neutral-500 truncate max-w-xl">
                  {issueDescription.replace(/\n/g, ' ').slice(0, 120)}
                  {issueDescription.length > 120 ? '…' : ''}
                </p>
              )}
            </div>
            <Button variant="ghost" size="sm" onClick={handleClose}>
              <XMarkIcon className="h-6 w-6" />
            </Button>
          </div>

          <CardContent padding="md">
            {phase === 'running' && (
              <AgentRunningLog
                logLines={logLines}
                sessionStatus={sessionStatus}
                error={error}
                onClose={handleClose}
              />
            )}

            {phase === 'approving' && (
              <AgentPlanApproval
                planSteps={planSteps}
                planDiagnosis={planDiagnosis}
                rejectFeedback={rejectFeedback}
                approveLoading={approveLoading}
                rejectLoading={rejectLoading}
                error={error}
                onUpdateStep={actions.updatePlanStep}
                onRemoveStep={actions.removePlanStep}
                onAddStep={actions.addPlanStep}
                onMoveStep={actions.movePlanStep}
                onSetRejectFeedback={actions.setRejectFeedback}
                onApprove={actions.approvePlan}
                onReject={actions.rejectPlan}
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
