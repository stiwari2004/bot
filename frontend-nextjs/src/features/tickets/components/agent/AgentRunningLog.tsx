'use client';
import { useEffect, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface Props {
  logLines: string[];
  sessionStatus: string;
  error: string | null;
  onClose: () => void;
}

export function AgentRunningLog({ logLines, sessionStatus, error, onClose }: Props) {
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logLines]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-neutral-600">
        <span className="inline-block h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
        Agent working… {sessionStatus && `(${sessionStatus})`}
      </div>

      <div className="bg-neutral-950 rounded-lg p-4 h-80 overflow-y-auto font-mono text-xs text-green-400 space-y-1">
        {logLines.length === 0 ? (
          <span className="text-neutral-500">Waiting for agent output…</span>
        ) : (
          logLines.map((line, i) => (
            <div key={i} className="whitespace-pre-wrap leading-relaxed">{line}</div>
          ))
        )}
        <div ref={logEndRef} />
      </div>

      <Card variant="outlined" className="border-amber-200 bg-amber-50">
        <CardContent padding="sm">
          <p className="text-xs text-amber-800">
            If the agent requests approval for a destructive command it will appear above.
            The agent pauses until you respond.
          </p>
        </CardContent>
      </Card>

      {error && (
        <Card variant="outlined" className="border-red-200 bg-red-50">
          <CardContent padding="sm">
            <p className="text-sm text-red-800">{error}</p>
          </CardContent>
        </Card>
      )}

      <div className="flex justify-end">
        <Button variant="outline" onClick={onClose}>
          Close (agent continues in background)
        </Button>
      </div>
    </div>
  );
}
