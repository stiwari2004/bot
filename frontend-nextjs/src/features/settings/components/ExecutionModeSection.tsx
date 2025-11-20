'use client';

import { CheckCircleIcon } from '@heroicons/react/24/outline';
import type { ExecutionMode } from '../types';

interface ExecutionModeSectionProps {
  executionMode: ExecutionMode | null;
  saving: boolean;
  onModeChange: (mode: 'hil' | 'auto') => void;
}

export function ExecutionModeSection({
  executionMode,
  saving,
  onModeChange,
}: ExecutionModeSectionProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm mb-6">
      <div className="p-6">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Execution Mode
          </h3>
          <p className="text-sm text-gray-600 mb-4">
            Control how runbooks are executed when matched to tickets
          </p>
        </div>

        <div className="space-y-4">
          <div
            className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
              executionMode?.mode === 'hil'
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
            onClick={() => onModeChange('hil')}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <input
                    type="radio"
                    name="execution-mode"
                    checked={executionMode?.mode === 'hil'}
                    onChange={() => onModeChange('hil')}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500"
                    disabled={saving}
                  />
                  <h4 className="font-medium text-gray-900">
                    Human-in-the-Loop (HIL) Mode
                  </h4>
                </div>
                <p className="text-sm text-gray-600 ml-7">
                  Always require manual approval before executing any runbook step.
                </p>
              </div>
              {executionMode?.mode === 'hil' && (
                <CheckCircleIcon className="h-6 w-6 text-blue-600 flex-shrink-0 ml-4" />
              )}
            </div>
          </div>

          <div
            className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
              executionMode?.mode === 'auto'
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
            onClick={() => onModeChange('auto')}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <input
                    type="radio"
                    name="execution-mode"
                    checked={executionMode?.mode === 'auto'}
                    onChange={() => onModeChange('auto')}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500"
                    disabled={saving}
                  />
                  <h4 className="font-medium text-gray-900">
                    Auto Mode
                  </h4>
                </div>
                <p className="text-sm text-gray-600 ml-7">
                  Automatically execute runbooks when confidence score is ≥0.8.
                </p>
              </div>
              {executionMode?.mode === 'auto' && (
                <CheckCircleIcon className="h-6 w-6 text-blue-600 flex-shrink-0 ml-4" />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}



