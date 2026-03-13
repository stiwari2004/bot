'use client';
import { CheckCircleIcon } from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/Button';

interface Props {
  runbook: { id: number; title: string };
  onClose: () => void;
}

export function AgentDoneScreen({ runbook, onClose }: Props) {
  return (
    <div className="space-y-4 py-4 text-center">
      <CheckCircleIcon className="h-16 w-16 text-green-500 mx-auto" />
      <p className="text-xl font-bold text-neutral-900">Runbook saved!</p>
      <p className="text-neutral-600">{runbook.title}</p>
      <p className="text-sm text-neutral-500">
        Runbook ID: {runbook.id} — reused automatically for future incidents of the same
        type with no LLM calls.
      </p>
      <Button variant="primary" onClick={onClose}>Close</Button>
    </div>
  );
}
