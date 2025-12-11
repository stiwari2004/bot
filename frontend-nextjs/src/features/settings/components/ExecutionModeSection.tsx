'use client';

import { CheckCircleIcon } from '@heroicons/react/24/outline';
import type { ExecutionMode } from '../types';
import { Card, CardContent } from '@/components/ui/Card';

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
    <Card variant="elevated">
      <CardContent padding="lg">
        <div className="mb-6">
          <h3 className="text-xl font-semibold text-neutral-900 mb-2">
            Execution Mode
          </h3>
          <p className="text-sm text-neutral-600">
            Control how runbooks are executed when matched to tickets
          </p>
        </div>

        <div className="space-y-4">
          <Card
            variant={executionMode?.mode === 'hil' ? 'outlined' : 'default'}
            className={`cursor-pointer transition-all ${
              executionMode?.mode === 'hil'
                ? 'border-primary-500 bg-primary-50 hover:bg-primary-100'
                : 'hover:border-primary-300 hover:shadow-md'
            }`}
            onClick={() => onModeChange('hil')}
          >
            <CardContent padding="md">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <input
                      type="radio"
                      name="execution-mode"
                      checked={executionMode?.mode === 'hil'}
                      onChange={() => onModeChange('hil')}
                      className="h-4 w-4 text-primary-600 focus:ring-primary-500"
                      disabled={saving}
                    />
                    <h4 className="font-semibold text-neutral-900">
                      Human-in-the-Loop (HIL) Mode
                    </h4>
                  </div>
                  <p className="text-sm text-neutral-600 ml-7">
                    Always require manual approval before executing any runbook step.
                  </p>
                </div>
                {executionMode?.mode === 'hil' && (
                  <div className="p-1 rounded-full bg-primary-100">
                    <CheckCircleIcon className="h-6 w-6 text-primary-600 flex-shrink-0" />
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card
            variant={executionMode?.mode === 'auto' ? 'outlined' : 'default'}
            className={`cursor-pointer transition-all ${
              executionMode?.mode === 'auto'
                ? 'border-primary-500 bg-primary-50 hover:bg-primary-100'
                : 'hover:border-primary-300 hover:shadow-md'
            }`}
            onClick={() => onModeChange('auto')}
          >
            <CardContent padding="md">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <input
                      type="radio"
                      name="execution-mode"
                      checked={executionMode?.mode === 'auto'}
                      onChange={() => onModeChange('auto')}
                      className="h-4 w-4 text-primary-600 focus:ring-primary-500"
                      disabled={saving}
                  />
                    <h4 className="font-semibold text-neutral-900">
                      Auto Mode
                    </h4>
                  </div>
                  <p className="text-sm text-neutral-600 ml-7">
                    Automatically execute runbooks when confidence score is ≥0.8.
                  </p>
                </div>
                {executionMode?.mode === 'auto' && (
                  <div className="p-1 rounded-full bg-primary-100">
                    <CheckCircleIcon className="h-6 w-6 text-primary-600 flex-shrink-0" />
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </CardContent>
    </Card>
  );
}



