'use client';

import { ArrowPathIcon } from '@heroicons/react/24/outline';
import type { ExecutionSessionSummary } from '../types';
import { statusColor, formatDate } from '../services/utils';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

interface SessionSidebarProps {
  sessions: ExecutionSessionSummary[];
  loading: boolean;
  error: string | null;
  activeSessionId: number | null;
  onSelectSession: (sessionId: number) => void;
  onRefresh: () => void;
}

export function SessionSidebar({
  sessions,
  loading,
  error,
  activeSessionId,
  onSelectSession,
  onRefresh,
}: SessionSidebarProps) {
  return (
    <Card variant="elevated" className="h-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-neutral-800 uppercase tracking-wide">
            Active Sessions
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            leftIcon={<ArrowPathIcon className="h-4 w-4" />}
          >
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent padding="md">
        {loading ? (
          <div className="text-sm text-neutral-500 font-medium text-center py-4">Loading sessions…</div>
        ) : error ? (
          <div className="text-sm text-error-600 font-medium text-center py-4">{error}</div>
        ) : sessions.length === 0 ? (
          <div className="text-sm text-neutral-500 text-center py-8">
            No execution sessions found.
          </div>
        ) : (
          <ul className="space-y-2">
            {sessions.map((session) => (
              <li key={session.id}>
                <Card
                  variant={activeSessionId === session.id ? 'outlined' : 'default'}
                  className={`cursor-pointer transition-all ${
                    activeSessionId === session.id
                      ? 'border-primary-500 bg-primary-50 hover:bg-primary-100'
                      : 'hover:border-primary-300 hover:shadow-md'
                  }`}
                  onClick={() => onSelectSession(session.id)}
                >
                  <CardContent padding="sm">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-neutral-900">Session #{session.id}</span>
                      <Badge variant="status" status={session.status as any} size="sm">
                        {session.status}
                      </Badge>
                    </div>
                    <div className="mt-1 text-xs text-neutral-600 line-clamp-2">
                      {session.runbook_title}
                    </div>
                    <div className="mt-1 text-[11px] text-neutral-400">
                      Started {formatDate(session.started_at)}
                    </div>
                  </CardContent>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}



