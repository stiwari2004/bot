'use client';

import { useState } from 'react';
import {
  CheckIcon,
  XMarkIcon,
  ClipboardDocumentIcon,
} from '@heroicons/react/24/outline';
import type { RunbookStep, StepUpdatePayload } from '../types';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

interface StepCardProps {
  step: RunbookStep;
  isUpdating: boolean;
  onUpdate: (updates: StepUpdatePayload) => void;
  onCopy: () => void;
}

export function StepCard({ step, isUpdating, onUpdate, onCopy }: StepCardProps) {
  const [outputValue, setOutputValue] = useState(step.output || '');
  const [notesValue, setNotesValue] = useState(step.notes || '');

  const isCompleted = step.completed === true;
  const approvalStatus =
    !step.requires_approval
      ? 'not_required'
      : step.approved === true
      ? 'approved'
      : step.approved === false
      ? 'changes'
      : 'pending';

  const getApprovalBadgeVariant = () => {
    switch (approvalStatus) {
      case 'approved':
        return 'success';
      case 'changes':
        return 'error';
      case 'pending':
        return 'warning';
      default:
        return 'secondary';
    }
  };

  const statusIcon = isCompleted ? (
    step.success === true ? (
      <div className="p-2 rounded-lg bg-success-100">
        <CheckIcon className="h-6 w-6 text-success-600" />
      </div>
    ) : step.success === false ? (
      <div className="p-2 rounded-lg bg-error-100">
        <XMarkIcon className="h-6 w-6 text-error-600" />
      </div>
    ) : null
  ) : null;

  const handleApprove = (value: boolean) => onUpdate({ approved: value });
  const handleMarkSuccess = (value: boolean) => onUpdate({ completed: true, success: value });
  const handleReopen = () => onUpdate({ completed: false, success: null });
  const handleSaveOutput = () => {
    if ((step.output || '') === outputValue) return;
    onUpdate({ output: outputValue });
  };
  const handleSaveNotes = () => {
    if ((step.notes || '') === notesValue) return;
    onUpdate({ notes: notesValue });
  };

  return (
    <Card variant={isCompleted ? 'default' : 'elevated'} className={isCompleted ? 'bg-neutral-50' : ''}>
      <CardContent padding="md">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="space-y-2 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-neutral-900">Step {step.step_number}</span>
              {step.severity && (
                <Badge variant="severity" severity={step.severity as any} size="sm">
                  {step.severity}
                </Badge>
              )}
              <Badge variant={getApprovalBadgeVariant()} size="sm">
                {approvalStatus === 'approved'
                  ? 'Approved'
                  : approvalStatus === 'changes'
                  ? 'Changes Requested'
                  : approvalStatus === 'pending'
                  ? 'Awaiting Approval'
                  : 'Approval Not Required'}
              </Badge>
            </div>
            {step.description && <p className="text-sm text-neutral-600">{step.description}</p>}
          </div>
          {statusIcon && <div className="flex items-center flex-shrink-0">{statusIcon}</div>}
        </div>

        {step.command && (
          <div className="mb-4 bg-neutral-900 text-accent-400 p-4 rounded-lg font-mono text-sm relative">
            <pre className="overflow-x-auto whitespace-pre-wrap">{step.command}</pre>
            <button
              onClick={onCopy}
              className="absolute top-2 right-2 text-neutral-400 hover:text-white transition-colors p-1 rounded hover:bg-neutral-800"
              title="Copy command"
            >
              <ClipboardDocumentIcon className="h-5 w-5" />
            </button>
          </div>
        )}

        {step.rollback_command && step.rollback_command.trim() !== '' && (
          <Card variant="outlined" className="mb-4 bg-warning-50 border-warning-200">
            <CardContent padding="sm">
              <p className="text-xs font-semibold text-warning-700 mb-2">Rollback Command</p>
              <pre className="text-xs text-warning-800 whitespace-pre-wrap font-mono">{step.rollback_command}</pre>
            </CardContent>
          </Card>
        )}

        {step.requires_approval && (
          <Card variant="outlined" className="mb-4 bg-primary-50 border-primary-200">
            <CardContent padding="sm">
              <p className="text-xs text-primary-700 mb-3">
                {approvalStatus === 'pending'
                  ? 'Approve this step before marking it complete.'
                  : approvalStatus === 'approved'
                  ? 'Approved. You can proceed with execution.'
                  : 'Changes requested. Please review before proceeding.'}
              </p>
              <div className="flex gap-2">
                <Button
                  variant={approvalStatus === 'approved' ? 'success' : 'outline'}
                  size="sm"
                  onClick={() => handleApprove(true)}
                  disabled={isUpdating}
                  className="flex-1"
                >
                  Approve Step
                </Button>
                <Button
                  variant={approvalStatus === 'changes' ? 'danger' : 'outline'}
                  size="sm"
                  onClick={() => handleApprove(false)}
                  disabled={isUpdating}
                  className="flex-1"
                >
                  Request Changes
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="space-y-4">
          {!isCompleted ? (
            <div className="flex flex-wrap gap-2">
              <Button
                variant="primary"
                size="sm"
                onClick={() => handleMarkSuccess(true)}
                disabled={isUpdating}
                className="flex-1 min-w-[140px]"
              >
                Mark Step Successful
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => handleMarkSuccess(false)}
                disabled={isUpdating}
                className="flex-1 min-w-[140px]"
              >
                Mark Step Failed
              </Button>
            </div>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReopen}
              disabled={isUpdating}
            >
              Reopen Step
            </Button>
          )}

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-2">
                Output
              </label>
              <textarea
                value={outputValue}
                onChange={(e) => setOutputValue(e.target.value)}
                onBlur={handleSaveOutput}
                disabled={isUpdating}
                rows={4}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-neutral-50 text-neutral-900 transition-all"
                placeholder="Step output..."
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-2">
                Notes
              </label>
              <textarea
                value={notesValue}
                onChange={(e) => setNotesValue(e.target.value)}
                onBlur={handleSaveNotes}
                disabled={isUpdating}
                rows={2}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-neutral-50 text-neutral-900 transition-all"
                placeholder="Add notes..."
              />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}



