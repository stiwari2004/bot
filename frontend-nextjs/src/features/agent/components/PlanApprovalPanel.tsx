'use client';

import { useEffect, useState } from 'react';
import { ArrowUpIcon, ArrowDownIcon, TrashIcon, PlusIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import type { PlanStep, Approach, PlanDiagnosis } from '../types';
import { RISK_COLORS, RISK_BADGE } from '../types';
import { Button } from '@/components/ui/Button';
import { fetchSessionPlan, selectApproach, approvePlan, rejectPlan } from '../services/agentSessionService';

interface Props {
  sessionId: number;
  onApproved: () => void;
}

export function PlanApprovalPanel({ sessionId, onApproved }: Props) {
  const [approaches, setApproaches] = useState<Approach[]>([]);
  const [diagnosis, setDiagnosis] = useState<PlanDiagnosis | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [steps, setSteps] = useState<PlanStep[]>([]);
  const [loading, setLoading] = useState(true);
  const [planGenerating, setPlanGenerating] = useState(false);
  const [approveLoading, setApproveLoading] = useState(false);
  const [rejectLoading, setRejectLoading] = useState(false);
  const [showReject, setShowReject] = useState(false);
  const [rejectFeedback, setRejectFeedback] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchSessionPlan(sessionId)
      .then(data => {
        if (cancelled) return;
        setDiagnosis(data.diagnosis || null);
        setApproaches(
          (data.approaches || []).map((a: Approach, i: number) => ({
            id: a.id ?? String.fromCharCode(65 + i),
            title: a.title ?? `Approach ${i + 1}`,
            rationale: a.rationale ?? '',
            risk: a.risk ?? 'medium',
          }))
        );
      })
      .catch(() => { if (!cancelled) setError('Could not load plan — try refreshing.'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [sessionId]);

  const handleSelectApproach = async (id: string) => {
    if (planGenerating || selectedId === id) return;
    setSelectedId(id);
    setSteps([]);
    setError(null);
    setPlanGenerating(true);
    try {
      const data: any = await selectApproach(sessionId, id);
      setSteps(
        (data.steps || []).map((s: PlanStep, i: number) => ({
          step: s.step ?? i + 1,
          intent: s.intent ?? '',
          command: s.command ?? '',
          risk: s.risk ?? 'medium',
        }))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate plan');
      setSelectedId(null);
    } finally {
      setPlanGenerating(false);
    }
  };

  const updateStep = (idx: number, field: keyof PlanStep, value: string) =>
    setSteps(prev => prev.map((s, i) => i === idx ? { ...s, [field]: value } : s));

  const removeStep = (idx: number) =>
    setSteps(prev => prev.filter((_, i) => i !== idx).map((s, i) => ({ ...s, step: i + 1 })));

  const moveStep = (idx: number, dir: 'up' | 'down') =>
    setSteps(prev => {
      const next = [...prev];
      const swap = dir === 'up' ? idx - 1 : idx + 1;
      if (swap < 0 || swap >= next.length) return prev;
      [next[idx], next[swap]] = [next[swap], next[idx]];
      return next.map((s, i) => ({ ...s, step: i + 1 }));
    });

  const addStep = () =>
    setSteps(prev => [...prev, { step: prev.length + 1, intent: '', command: '', risk: 'medium' }]);

  const handleApprove = async () => {
    if (!selectedId) { setError('Please select an approach first.'); return; }
    setApproveLoading(true);
    setError(null);
    try {
      await approvePlan(sessionId, selectedId, steps);
      onApproved();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Approval failed');
    } finally {
      setApproveLoading(false);
    }
  };

  const handleReject = async () => {
    if (!rejectFeedback.trim()) return;
    setRejectLoading(true);
    setError(null);
    try {
      await rejectPlan(sessionId, rejectFeedback);
      setShowReject(false);
      setRejectFeedback('');
      onApproved();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Rejection failed');
    } finally {
      setRejectLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-6 text-sm text-neutral-500">
        <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />
        Loading plan…
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {diagnosis && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
          <p className="text-sm font-semibold text-blue-900 mb-1">Diagnosis — {diagnosis.confidence} confidence</p>
          <p className="text-sm text-blue-800">{diagnosis.root_cause}</p>
          {diagnosis.evidence?.length > 0 && (
            <ul className="mt-1 space-y-0.5">
              {diagnosis.evidence.map((e, i) => (
                <li key={i} className="text-xs text-blue-700 flex gap-1">
                  <span className="text-blue-400 flex-shrink-0">•</span>{e}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {approaches.length > 0 && (
        <div>
          <p className="text-sm font-semibold text-neutral-700 mb-2">Choose an approach</p>
          <div className="space-y-2">
            {approaches.map(approach => {
              const isSelected = selectedId === approach.id;
              const isGenerating = isSelected && planGenerating;
              return (
                <button key={approach.id} type="button" onClick={() => handleSelectApproach(approach.id)}
                  disabled={planGenerating}
                  className={`w-full text-left rounded-lg border p-3 transition-all disabled:cursor-wait ${
                    isSelected ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200' : 'border-neutral-200 bg-white hover:border-blue-300 hover:bg-blue-50/40'
                  }`}>
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="flex items-center gap-2">
                      {isGenerating
                        ? <div className="h-5 w-5 rounded-full border-2 border-blue-500 border-t-transparent animate-spin flex-shrink-0" />
                        : <span className={`inline-flex items-center justify-center h-5 w-5 rounded-full text-xs font-bold flex-shrink-0 ${isSelected ? 'bg-blue-600 text-white' : 'bg-neutral-200 text-neutral-600'}`}>{approach.id}</span>
                      }
                      <span className="text-sm font-semibold text-neutral-900">{approach.title}</span>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium uppercase ${RISK_BADGE[approach.risk] || RISK_BADGE.medium}`}>{approach.risk}</span>
                  </div>
                  {approach.rationale && <p className="text-xs text-neutral-600 ml-7">{approach.rationale}</p>}
                  {isGenerating && <p className="text-xs text-blue-600 ml-7 mt-0.5 animate-pulse">Generating remediation plan…</p>}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {selectedId && steps.length > 0 && (
        <div>
          <p className="text-sm font-semibold text-neutral-700 mb-1">Steps — edit, reorder or remove before approving.</p>
          <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
            {steps.map((step, idx) => (
              <div key={idx} className="rounded-lg border border-neutral-300 bg-white p-3">
                <div className="flex items-start gap-2">
                  <div className="flex flex-col gap-0.5 pt-0.5 flex-shrink-0">
                    <button type="button" onClick={() => moveStep(idx, 'up')} disabled={idx === 0}
                      className="p-0.5 text-neutral-400 hover:text-neutral-700 disabled:opacity-30">
                      <ArrowUpIcon className="h-3.5 w-3.5" />
                    </button>
                    <button type="button" onClick={() => moveStep(idx, 'down')} disabled={idx === steps.length - 1}
                      className="p-0.5 text-neutral-400 hover:text-neutral-700 disabled:opacity-30">
                      <ArrowDownIcon className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <div className="flex-1 min-w-0 space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-neutral-500">Step {step.step}</span>
                      <select value={step.risk} onChange={e => updateStep(idx, 'risk', e.target.value)}
                        className={`text-xs px-1.5 py-0.5 rounded border font-medium cursor-pointer ${RISK_COLORS[step.risk] || RISK_COLORS.medium}`}>
                        <option value="low">LOW</option>
                        <option value="medium">MEDIUM</option>
                        <option value="high">HIGH</option>
                      </select>
                    </div>
                    <input type="text" value={step.intent} onChange={e => updateStep(idx, 'intent', e.target.value)}
                      placeholder="What this step achieves…"
                      className="w-full text-xs px-2 py-1.5 border border-neutral-200 rounded text-neutral-700 italic placeholder-neutral-400 focus:ring-1 focus:ring-blue-400 focus:border-blue-400" />
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-mono text-neutral-500 flex-shrink-0">$</span>
                      <input type="text" value={step.command} onChange={e => updateStep(idx, 'command', e.target.value)}
                        placeholder="shell command"
                        className="flex-1 text-xs font-mono px-2 py-1.5 bg-neutral-100 border border-neutral-200 rounded text-neutral-900 placeholder-neutral-400 focus:ring-1 focus:ring-blue-400 focus:border-blue-400" />
                    </div>
                  </div>
                  <button type="button" onClick={() => removeStep(idx)}
                    className="p-1 text-neutral-400 hover:text-red-500 flex-shrink-0">
                    <TrashIcon className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
          <button type="button" onClick={addStep}
            className="mt-2 flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 font-medium">
            <PlusIcon className="h-4 w-4" /> Add step
          </button>
        </div>
      )}

      {showReject && (
        <div className="space-y-2 pt-2 border-t border-neutral-200">
          <div className="flex items-center gap-1.5 text-sm text-amber-700 font-medium">
            <ExclamationTriangleIcon className="h-4 w-4" /> Rejection feedback
          </div>
          <textarea value={rejectFeedback} onChange={e => setRejectFeedback(e.target.value)} rows={3}
            placeholder="Explain what's wrong and what the agent should try instead…"
            className="w-full px-3 py-2 text-sm border border-neutral-300 rounded-lg focus:ring-2 focus:ring-amber-400 text-neutral-900" />
        </div>
      )}

      {error && <p className="text-xs text-red-600 font-medium">{error}</p>}

      <div className="flex items-center justify-between pt-2 border-t border-neutral-200">
        <p className="text-xs text-neutral-500">
          {selectedId ? `${steps.length} step${steps.length !== 1 ? 's' : ''} · approach ${selectedId} selected` : 'Select an approach above'}
        </p>
        <div className="flex gap-2">
          {!showReject ? (
            <Button variant="outline" size="sm" onClick={() => setShowReject(true)}>None of these work</Button>
          ) : (
            <>
              <Button variant="ghost" size="sm" onClick={() => setShowReject(false)}>Cancel</Button>
              <Button variant="outline" size="sm" onClick={handleReject}
                isLoading={rejectLoading} disabled={rejectLoading || !rejectFeedback.trim()}
                className="border-amber-400 text-amber-700 hover:bg-amber-50">
                Send Feedback
              </Button>
            </>
          )}
          <Button variant="primary" size="sm" onClick={handleApprove}
            isLoading={approveLoading} disabled={approveLoading || !selectedId || steps.length === 0}>
            Approve & Execute
          </Button>
        </div>
      </div>
    </div>
  );
}
