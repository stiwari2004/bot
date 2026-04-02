'use client';

import { useEffect, useState } from 'react';
import type { DiscoveredTarget, AgentDiagnosis } from '../types';
import { Button } from '@/components/ui/Button';
import { fetchSessionPlan, setExclusions } from '../services/agentSessionService';

const TYPE_LABELS: Record<DiscoveredTarget['type'], string> = {
  system_logs:   'System Logs',
  package_cache: 'Package Cache',
  temp_files:    'Temp Files',
  app_data:      'App Data',
  app_logs:      'App Logs',
  core_dumps:    'Core Dumps',
  other:         'Other',
};

const TYPE_COLORS: Record<DiscoveredTarget['type'], string> = {
  system_logs:   'bg-blue-100 text-blue-700',
  package_cache: 'bg-purple-100 text-purple-700',
  temp_files:    'bg-yellow-100 text-yellow-700',
  app_data:      'bg-red-100 text-red-700',
  app_logs:      'bg-orange-100 text-orange-700',
  core_dumps:    'bg-rose-100 text-rose-700',
  other:         'bg-neutral-100 text-neutral-600',
};

interface Props {
  sessionId: number;
  onExclusionsSubmitted: () => void;
}

export function ExclusionPanel({ sessionId, onExclusionsSubmitted }: Props) {
  const [targets, setTargets] = useState<DiscoveredTarget[]>([]);
  const [diagnosis, setDiagnosis] = useState<AgentDiagnosis | null>(null);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchSessionPlan(sessionId)
      .then((data: any) => {
        if (cancelled) return;
        const t: DiscoveredTarget[] = data.targets || [];
        setTargets(t);
        setDiagnosis(data.diagnosis || null);
        // All targets included (checked) by default
        const initial: Record<string, boolean> = {};
        t.forEach(target => { initial[target.path] = true; });
        setChecked(initial);
      })
      .catch(() => { if (!cancelled) setError('Could not load discovered targets — try refreshing.'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [sessionId]);

  const toggle = (path: string) =>
    setChecked(prev => ({ ...prev, [path]: !prev[path] }));

  const handleSubmit = async () => {
    // Exclusions = paths the human unchecked (wants to protect)
    const exclusions = targets.filter(t => !checked[t.path]).map(t => t.path);
    setSubmitting(true);
    setError(null);
    try {
      await setExclusions(sessionId, exclusions);
      onExclusionsSubmitted();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to submit — please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-6 text-sm text-neutral-500">
        <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />
        Scanning system for cleanup targets…
      </div>
    );
  }

  const includedCount = targets.filter(t => checked[t.path]).length;

  return (
    <div className="space-y-4">

      {/* Diagnosis summary */}
      {diagnosis && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
          <p className="text-sm font-semibold text-blue-900 mb-1">
            Diagnosis — <span className="font-normal">{diagnosis.confidence} confidence</span>
          </p>
          <p className="text-sm text-blue-800">{diagnosis.root_cause}</p>
          {diagnosis.evidence?.length > 0 && (
            <ul className="mt-1.5 space-y-0.5">
              {diagnosis.evidence.map((e, i) => (
                <li key={i} className="text-xs text-blue-700 flex gap-1.5">
                  <span className="text-blue-400 flex-shrink-0 mt-px">•</span>{e}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Target list */}
      {targets.length === 0 ? (
        <p className="text-sm text-neutral-500 py-2">No cleanup targets discovered.</p>
      ) : (
        <div>
          <p className="text-sm font-semibold text-neutral-700 mb-1">
            Discovered targets — uncheck any folders you want to protect
          </p>
          <p className="text-xs text-neutral-500 mb-3">
            The agent will only clean up checked items. Unchecked paths will not be touched.
          </p>
          <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
            {targets.map(target => (
              <label key={target.path}
                className={`flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                  checked[target.path]
                    ? 'border-blue-300 bg-blue-50/60'
                    : 'border-neutral-200 bg-neutral-50 opacity-60'
                }`}>
                <input
                  type="checkbox"
                  checked={!!checked[target.path]}
                  onChange={() => toggle(target.path)}
                  className="mt-0.5 h-4 w-4 rounded border-neutral-300 text-blue-600 focus:ring-blue-500 flex-shrink-0 cursor-pointer"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-mono font-semibold text-neutral-900 break-all">
                      {target.path}
                    </span>
                    <span className="text-xs font-semibold text-neutral-500 flex-shrink-0">
                      {target.size}
                    </span>
                    <span className={`text-xs px-1.5 py-0.5 rounded font-medium flex-shrink-0 ${TYPE_COLORS[target.type] ?? TYPE_COLORS.other}`}>
                      {TYPE_LABELS[target.type] ?? target.type}
                    </span>
                  </div>
                  {target.description && (
                    <p className="text-xs text-neutral-500 mt-0.5">{target.description}</p>
                  )}
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      {error && <p className="text-xs text-red-600 font-medium">{error}</p>}

      <div className="flex items-center justify-between pt-2 border-t border-neutral-200">
        <p className="text-xs text-neutral-500">
          {includedCount} of {targets.length} target{targets.length !== 1 ? 's' : ''} included in cleanup
        </p>
        <Button
          variant="primary"
          size="sm"
          onClick={handleSubmit}
          isLoading={submitting}
          disabled={submitting || targets.length === 0}>
          Confirm &amp; Start Cleanup
        </Button>
      </div>

    </div>
  );
}
