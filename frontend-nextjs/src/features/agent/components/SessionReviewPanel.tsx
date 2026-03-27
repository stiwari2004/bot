'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { reviewSession } from '../services/agentSessionService';

interface Props {
  sessionId: number;
  agentSummary?: string;
  onDone: (runbookId?: number) => void;
}

export function SessionReviewPanel({ sessionId, agentSummary, onDone }: Props) {
  const [saveAsRunbook, setSaveAsRunbook] = useState(false);
  const [runbookTitle, setRunbookTitle] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setSaving(true);
    setError(null);
    try {
      const data: any = await reviewSession(
        sessionId,
        saveAsRunbook,
        saveAsRunbook && runbookTitle.trim() ? runbookTitle.trim() : undefined,
      );
      onDone(data.runbook_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      {agentSummary && (
        <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
          <p className="text-xs font-semibold text-neutral-600 mb-1 uppercase tracking-wide">Agent Summary</p>
          <p className="text-sm text-neutral-800">{agentSummary}</p>
        </div>
      )}

      <div className="flex items-center gap-3">
        <input type="checkbox" id="save-runbook" checked={saveAsRunbook}
          onChange={e => setSaveAsRunbook(e.target.checked)}
          className="h-4 w-4 rounded border-neutral-300 text-blue-600 focus:ring-blue-500" />
        <label htmlFor="save-runbook" className="text-sm text-neutral-800 font-medium cursor-pointer">
          Save successful steps as a runbook for future use
        </label>
      </div>

      {saveAsRunbook && (
        <input type="text" value={runbookTitle} onChange={e => setRunbookTitle(e.target.value)}
          placeholder="Runbook title (auto-generated if blank)"
          className="w-full px-3 py-2 text-sm border border-neutral-300 rounded-lg text-neutral-900 placeholder-neutral-400 focus:ring-2 focus:ring-blue-400 focus:border-blue-400" />
      )}

      {error && <p className="text-xs text-red-600 font-medium">{error}</p>}

      <div className="flex justify-end pt-2 border-t border-neutral-200">
        <Button variant="primary" size="sm" onClick={handleSubmit} isLoading={saving} disabled={saving}>
          {saveAsRunbook ? 'Save runbook & close' : 'Close session'}
        </Button>
      </div>
    </div>
  );
}
