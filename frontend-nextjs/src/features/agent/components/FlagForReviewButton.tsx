'use client';

import { useState } from 'react';
import { FlagIcon } from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/Button';
import { flagRunbookForReview } from '../services/agentSessionService';

export function FlagForReviewButton({ runbookId }: { runbookId: number }) {
  const [loading, setLoading] = useState(false);
  const [flagged, setFlagged] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFlag = async () => {
    setLoading(true);
    setError(null);
    try {
      await flagRunbookForReview(runbookId);
      setFlagged(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to flag for review');
    } finally {
      setLoading(false);
    }
  };

  if (flagged) {
    return (
      <div className="flex items-center gap-2 text-sm text-amber-800 font-medium">
        <FlagIcon className="h-4 w-4 text-amber-600" />
        Runbook flagged for review — visible in the Quarantine Dashboard.
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <Button variant="outline" size="sm" onClick={handleFlag} isLoading={loading} disabled={loading}
        leftIcon={<FlagIcon className="h-4 w-4" />}
        className="border-amber-400 text-amber-700 hover:bg-amber-50">
        Flag runbook for review
      </Button>
      {error && <p className="text-xs text-red-600 font-medium">{error}</p>}
    </div>
  );
}
