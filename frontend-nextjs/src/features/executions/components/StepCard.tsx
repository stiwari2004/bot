'use client';

import { useState } from 'react';
import {
  CheckIcon,
  XMarkIcon,
  ClipboardDocumentIcon,
} from '@heroicons/react/24/outline';
import type { RunbookStep, StepUpdatePayload } from '../types';

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

  const approvalBadgeClass =
    approvalStatus === 'approved'
      ? 'bg-green-100 text-green-800'
      : approvalStatus === 'changes'
      ? 'bg-red-100 text-red-800'
      : approvalStatus === 'pending'
      ? 'bg-yellow-100 text-yellow-800'
      : 'bg-gray-100 text-gray-800';

  const getSeverityColor = (severity?: string) => {
    switch (severity?.toLowerCase()) {
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

  const statusIcon = isCompleted ? (
    step.success === true ? (
      <CheckIcon className="h-6 w-6 text-green-600" />
    ) : step.success === false ? (
      <XMarkIcon className="h-6 w-6 text-red-600" />
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
    <div className={`border rounded-lg p-4 shadow-sm ${isCompleted ? 'bg-gray-50 border-gray-200' : 'bg-white border-gray-100'}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-gray-900">Step {step.step_number}</span>
            {step.severity && (
              <span className={`px-2 py-0.5 text-xs font-semibold rounded-full capitalize ${getSeverityColor(step.severity)}`}>
                {step.severity}
              </span>
            )}
            <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${approvalBadgeClass}`}>
              {approvalStatus === 'approved'
                ? 'Approved'
                : approvalStatus === 'changes'
                ? 'Changes Requested'
                : approvalStatus === 'pending'
                ? 'Awaiting Approval'
                : 'Approval Not Required'}
            </span>
          </div>
          {step.description && <p className="text-sm text-gray-600">{step.description}</p>}
        </div>
        {statusIcon && <div className="flex items-center">{statusIcon}</div>}
      </div>

      {step.command && (
        <div className="mt-3 bg-gray-900 text-green-400 p-3 rounded font-mono text-sm relative">
          <pre className="overflow-x-auto whitespace-pre-wrap">{step.command}</pre>
          <button
            onClick={onCopy}
            className="absolute top-2 right-2 text-gray-400 hover:text-white"
            title="Copy command"
          >
            <ClipboardDocumentIcon className="h-5 w-5" />
          </button>
        </div>
      )}

      {step.rollback_command && step.rollback_command.trim() !== '' && (
        <div className="mt-3 bg-orange-50 border border-orange-100 rounded-lg p-3">
          <p className="text-xs font-semibold text-orange-700 mb-1">Rollback Command</p>
          <pre className="text-xs text-orange-800 whitespace-pre-wrap">{step.rollback_command}</pre>
        </div>
      )}

      {step.requires_approval && (
        <div className="mt-3 bg-blue-50 border border-blue-100 rounded-lg p-3 space-y-2">
          <p className="text-xs text-blue-700">
            {approvalStatus === 'pending'
              ? 'Approve this step before marking it complete.'
              : approvalStatus === 'approved'
              ? 'Approved. You can proceed with execution.'
              : 'Changes requested. Please review before proceeding.'}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => handleApprove(true)}
              disabled={isUpdating}
              className={`flex-1 px-3 py-2 text-xs font-semibold rounded-md transition-colors ${
                approvalStatus === 'approved'
                  ? 'bg-green-600 text-white'
                  : 'bg-white border border-green-300 text-green-700 hover:bg-green-50'
              }`}
            >
              Approve Step
            </button>
            <button
              onClick={() => handleApprove(false)}
              disabled={isUpdating}
              className={`flex-1 px-3 py-2 text-xs font-semibold rounded-md transition-colors ${
                approvalStatus === 'changes'
                  ? 'bg-red-600 text-white'
                  : 'bg-white border border-red-300 text-red-700 hover:bg-red-50'
              }`}
            >
              Request Changes
            </button>
          </div>
        </div>
      )}

      <div className="mt-4 space-y-3">
        {!isCompleted ? (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => handleMarkSuccess(true)}
              disabled={isUpdating}
              className="flex-1 min-w-[140px] bg-blue-600 text-white px-3 py-2 text-sm font-semibold rounded-md hover:bg-blue-700 transition"
            >
              Mark Step Successful
            </button>
            <button
              onClick={() => handleMarkSuccess(false)}
              disabled={isUpdating}
              className="flex-1 min-w-[140px] bg-red-100 text-red-700 px-3 py-2 text-sm font-semibold rounded-md hover:bg-red-200 transition"
            >
              Mark Step Failed
            </button>
          </div>
        ) : (
          <button
            onClick={handleReopen}
            disabled={isUpdating}
            className="bg-gray-100 text-gray-700 px-3 py-2 text-sm font-semibold rounded-md hover:bg-gray-200 transition"
          >
            Reopen Step
          </button>
        )}

        <div className="space-y-2">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Output
            </label>
            <textarea
              value={outputValue}
              onChange={(e) => setOutputValue(e.target.value)}
              onBlur={handleSaveOutput}
              disabled={isUpdating}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-50"
              placeholder="Step output..."
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              value={notesValue}
              onChange={(e) => setNotesValue(e.target.value)}
              onBlur={handleSaveNotes}
              disabled={isUpdating}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-50"
              placeholder="Add notes..."
            />
          </div>
        </div>
      </div>
    </div>
  );
}

