'use client';
import { CheckCircleIcon, TrashIcon } from '@heroicons/react/24/outline';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import type { StepForReview } from '@/features/tickets/hooks/useAgentSession';

const SAFETY_COLORS: Record<number, string> = {
  1: 'text-green-700 bg-green-50 border-green-200',
  2: 'text-amber-700 bg-amber-50 border-amber-200',
  3: 'text-orange-700 bg-orange-50 border-orange-200',
  4: 'text-red-700 bg-red-50 border-red-200',
};

interface Props {
  steps: StepForReview[];
  weedSet: Set<number>;
  agentSummary: string;
  runbookTitle: string;
  saveLoading: boolean;
  error: string | null;
  onToggleWeed: (stepNumber: number) => void;
  onTitleChange: (v: string) => void;
  onSave: () => void;
  onDiscard: () => void;
}

export function AgentStepReview({
  steps, weedSet, agentSummary, runbookTitle,
  saveLoading, error,
  onToggleWeed, onTitleChange, onSave, onDiscard,
}: Props) {
  const keptCount = steps.length - weedSet.size;

  return (
    <div className="space-y-4">
      {agentSummary && (
        <Card variant="outlined" className="border-green-200 bg-green-50">
          <CardContent padding="sm">
            <p className="text-sm font-semibold text-green-900">Agent summary</p>
            <p className="text-sm text-green-800 mt-1">{agentSummary}</p>
          </CardContent>
        </Card>
      )}

      <div>
        <p className="text-sm font-semibold text-neutral-700 mb-1">
          Review steps — uncheck any that were unnecessary (weeds).
          Only checked steps will be saved in the runbook.
        </p>
        <p className="text-xs text-neutral-500 mb-3">
          Failed or blocked steps are pre-marked as weeds. You can override any selection.
        </p>

        <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
          {steps.map(step => {
            const isWeed = weedSet.has(step.step_number);
            return (
              <div
                key={step.step_number}
                className={`rounded-lg border p-3 cursor-pointer transition-all ${
                  isWeed ? 'border-neutral-200 bg-neutral-50 opacity-50' : 'border-neutral-300 bg-white'
                }`}
                onClick={() => onToggleWeed(step.step_number)}
              >
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 h-5 w-5 rounded border-2 flex-shrink-0 flex items-center justify-center ${
                    isWeed ? 'border-neutral-300 bg-white' : 'border-blue-500 bg-blue-500'
                  }`}>
                    {!isWeed && <CheckCircleIcon className="h-4 w-4 text-white" />}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-semibold text-neutral-500">
                        Step {step.step_number}
                      </span>
                      <span className={`text-xs px-1.5 py-0.5 rounded border font-medium ${SAFETY_COLORS[step.safety_level] || ''}`}>
                        {step.safety_label}
                      </span>
                      {isWeed && (
                        <span className="text-xs text-neutral-400 flex items-center gap-1">
                          <TrashIcon className="h-3 w-3" /> weed
                        </span>
                      )}
                    </div>

                    {step.reasoning && (
                      <p className="text-xs text-neutral-500 mt-0.5 italic">{step.reasoning}</p>
                    )}

                    <code className="block text-xs font-mono text-neutral-800 mt-1 bg-neutral-100 rounded px-2 py-1 truncate">
                      $ {step.command}
                    </code>

                    {step.output && !isWeed && (
                      <pre className="text-xs text-neutral-600 mt-1 whitespace-pre-wrap line-clamp-2">
                        {step.output.slice(0, 200)}
                      </pre>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <label className="block text-sm font-semibold text-neutral-700 mb-1">Runbook title</label>
        <input
          type="text"
          value={runbookTitle}
          onChange={e => onTitleChange(e.target.value)}
          className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
          placeholder="Name for the saved runbook…"
        />
      </div>

      {error && (
        <Card variant="outlined" className="border-red-200 bg-red-50">
          <CardContent padding="sm">
            <p className="text-sm text-red-800">{error}</p>
          </CardContent>
        </Card>
      )}

      <div className="flex justify-between items-center pt-2 border-t border-neutral-200">
        <p className="text-xs text-neutral-500">
          {keptCount} of {steps.length} steps will be saved
        </p>
        <div className="flex gap-3">
          <Button variant="outline" onClick={onDiscard}>Discard</Button>
          <Button
            variant="primary"
            onClick={onSave}
            isLoading={saveLoading}
            disabled={saveLoading || keptCount === 0}
          >
            Save as Runbook
          </Button>
        </div>
      </div>
    </div>
  );
}
