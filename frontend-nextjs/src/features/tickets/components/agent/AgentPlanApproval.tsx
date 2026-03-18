'use client';
import { useState } from 'react';
import {
  PlusIcon,
  TrashIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import type { PlanStep, PlanDiagnosis } from '@/features/tickets/hooks/useAgentSession';

const RISK_COLORS: Record<string, string> = {
  low:    'text-green-700 bg-green-50 border-green-200',
  medium: 'text-amber-700 bg-amber-50 border-amber-200',
  high:   'text-red-700 bg-red-50 border-red-200',
};

interface Props {
  planSteps: PlanStep[];
  planDiagnosis: PlanDiagnosis | null;
  rejectFeedback: string;
  approveLoading: boolean;
  rejectLoading: boolean;
  error: string | null;
  onUpdateStep: (index: number, field: keyof PlanStep, value: string) => void;
  onRemoveStep: (index: number) => void;
  onAddStep: () => void;
  onMoveStep: (index: number, direction: 'up' | 'down') => void;
  onSetRejectFeedback: (v: string) => void;
  onApprove: () => void;
  onReject: () => void;
}

export function AgentPlanApproval({
  planSteps, planDiagnosis,
  rejectFeedback, approveLoading, rejectLoading, error,
  onUpdateStep, onRemoveStep, onAddStep, onMoveStep,
  onSetRejectFeedback, onApprove, onReject,
}: Props) {
  const [showReject, setShowReject] = useState(false);

  return (
    <div className="space-y-4">
      {/* Diagnosis findings */}
      {planDiagnosis && (
        <Card variant="outlined" className="border-blue-200 bg-blue-50">
          <CardContent padding="sm">
            <p className="text-sm font-semibold text-blue-900 mb-1">
              Diagnosis — {planDiagnosis.confidence} confidence
            </p>
            <p className="text-sm text-blue-800">{planDiagnosis.root_cause}</p>
            {planDiagnosis.evidence?.length > 0 && (
              <ul className="mt-1 space-y-0.5">
                {planDiagnosis.evidence.map((e, i) => (
                  <li key={i} className="text-xs text-blue-700 flex gap-1">
                    <span className="text-blue-400 flex-shrink-0">•</span> {e}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      {/* Instructions */}
      <div>
        <p className="text-sm font-semibold text-neutral-700 mb-0.5">
          Proposed Plan — review, edit, reorder, or remove steps before approving.
        </p>
        <p className="text-xs text-neutral-500 mb-3">
          The agent will execute exactly what you approve, in this order.
        </p>

        {/* Step list */}
        <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
          {planSteps.map((step, idx) => (
            <div key={idx} className="rounded-lg border border-neutral-300 bg-white p-3">
              <div className="flex items-start gap-2">
                {/* Reorder buttons */}
                <div className="flex flex-col gap-0.5 pt-0.5 flex-shrink-0">
                  <button
                    type="button"
                    onClick={() => onMoveStep(idx, 'up')}
                    disabled={idx === 0}
                    className="p-0.5 text-neutral-400 hover:text-neutral-700 disabled:opacity-30"
                    title="Move up"
                  >
                    <ArrowUpIcon className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => onMoveStep(idx, 'down')}
                    disabled={idx === planSteps.length - 1}
                    className="p-0.5 text-neutral-400 hover:text-neutral-700 disabled:opacity-30"
                    title="Move down"
                  >
                    <ArrowDownIcon className="h-3.5 w-3.5" />
                  </button>
                </div>

                <div className="flex-1 min-w-0 space-y-2">
                  {/* Step number + risk */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-neutral-500">Step {step.step}</span>
                    <select
                      value={step.risk}
                      onChange={e => onUpdateStep(idx, 'risk', e.target.value)}
                      className={`text-xs px-1.5 py-0.5 rounded border font-medium cursor-pointer ${RISK_COLORS[step.risk] || RISK_COLORS.medium}`}
                    >
                      <option value="low">LOW</option>
                      <option value="medium">MEDIUM</option>
                      <option value="high">HIGH</option>
                    </select>
                  </div>

                  {/* Intent */}
                  <input
                    type="text"
                    value={step.intent}
                    onChange={e => onUpdateStep(idx, 'intent', e.target.value)}
                    placeholder="What this step achieves…"
                    className="w-full text-xs px-2 py-1.5 border border-neutral-200 rounded text-neutral-700 italic placeholder-neutral-400 focus:ring-1 focus:ring-blue-400 focus:border-blue-400"
                  />

                  {/* Command */}
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-mono text-neutral-500 flex-shrink-0">$</span>
                    <input
                      type="text"
                      value={step.command}
                      onChange={e => onUpdateStep(idx, 'command', e.target.value)}
                      placeholder="shell command"
                      className="flex-1 text-xs font-mono px-2 py-1.5 bg-neutral-100 border border-neutral-200 rounded text-neutral-900 placeholder-neutral-400 focus:ring-1 focus:ring-blue-400 focus:border-blue-400"
                    />
                  </div>
                </div>

                {/* Delete */}
                <button
                  type="button"
                  onClick={() => onRemoveStep(idx)}
                  className="p-1 text-neutral-400 hover:text-red-500 flex-shrink-0"
                  title="Remove step"
                >
                  <TrashIcon className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Add step */}
        <button
          type="button"
          onClick={onAddStep}
          className="mt-2 flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 font-medium"
        >
          <PlusIcon className="h-4 w-4" />
          Add step
        </button>
      </div>

      {/* Error */}
      {error && (
        <Card variant="outlined" className="border-red-200 bg-red-50">
          <CardContent padding="sm">
            <p className="text-sm text-red-800">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Reject section */}
      {showReject && (
        <div className="space-y-2 pt-2 border-t border-neutral-200">
          <div className="flex items-center gap-1.5 text-sm text-amber-700">
            <ExclamationTriangleIcon className="h-4 w-4" />
            <span className="font-medium">Rejection feedback</span>
          </div>
          <textarea
            value={rejectFeedback}
            onChange={e => onSetRejectFeedback(e.target.value)}
            rows={3}
            placeholder="Explain what's wrong and what the agent should do instead…"
            className="w-full px-3 py-2 text-sm border border-neutral-300 rounded-lg focus:ring-2 focus:ring-amber-400 focus:border-amber-400 text-neutral-900"
          />
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-2 border-t border-neutral-200">
        <p className="text-xs text-neutral-500">{planSteps.length} step{planSteps.length !== 1 ? 's' : ''}</p>
        <div className="flex gap-2">
          {!showReject ? (
            <Button variant="outline" size="sm" onClick={() => setShowReject(true)}>
              Reject
            </Button>
          ) : (
            <>
              <Button variant="ghost" size="sm" onClick={() => setShowReject(false)}>
                Cancel
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={onReject}
                isLoading={rejectLoading}
                disabled={rejectLoading || !rejectFeedback.trim()}
                className="border-amber-400 text-amber-700 hover:bg-amber-50"
              >
                Send Feedback
              </Button>
            </>
          )}
          <Button
            variant="primary"
            size="sm"
            onClick={onApprove}
            isLoading={approveLoading}
            disabled={approveLoading || planSteps.length === 0}
          >
            Approve & Execute
          </Button>
        </div>
      </div>
    </div>
  );
}
