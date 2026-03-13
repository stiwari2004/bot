'use client';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface Props {
  issueDescription: string;
  error: string | null;
  onChange: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
}

export function AgentSetupForm({ issueDescription, error, onChange, onSubmit, onCancel }: Props) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <Card variant="outlined" className="border-blue-200 bg-blue-50">
        <CardContent padding="sm">
          <p className="text-sm text-blue-800 font-medium">
            The agent connects to the target server, runs discovery commands, and fixes
            the issue step-by-step. Destructive commands require your approval before
            executing. Once resolved, save the steps as a reusable runbook.
          </p>
        </CardContent>
      </Card>

      <div>
        <label className="block text-sm font-semibold text-neutral-700 mb-2">
          Issue Description *
        </label>
        <textarea
          value={issueDescription}
          onChange={e => onChange(e.target.value)}
          rows={6}
          className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
          placeholder="Describe the issue…"
          required
        />
      </div>

      {error && (
        <Card variant="outlined" className="border-red-200 bg-red-50">
          <CardContent padding="sm">
            <p className="text-sm text-red-800">{error}</p>
          </CardContent>
        </Card>
      )}

      <div className="flex justify-end gap-3 pt-2">
        <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
        <Button type="submit" variant="primary" disabled={!issueDescription.trim()}>
          Start Agent
        </Button>
      </div>
    </form>
  );
}
