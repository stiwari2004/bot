'use client';

import { ArrowPathIcon } from '@heroicons/react/24/outline';
import type { ExecutionSessionSummary } from '../types';
import { statusColor, formatDate } from '../services/utils';

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
    <aside className="bg-white border border-gray-200 rounded-2xl shadow-sm p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">
          Active Sessions
        </h2>
        <button
          onClick={onRefresh}
          className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
        >
          <ArrowPathIcon className="h-4 w-4" />
          Refresh
        </button>
      </div>
      {loading ? (
        <div className="text-sm text-gray-500">Loading sessions…</div>
      ) : error ? (
        <div className="text-sm text-red-600">{error}</div>
      ) : sessions.length === 0 ? (
        <div className="text-sm text-gray-500">
          No execution sessions found.
        </div>
      ) : (
        <ul className="space-y-2">
          {sessions.map((session) => (
            <li key={session.id}>
              <button
                onClick={() => onSelectSession(session.id)}
                className={`w-full text-left px-3 py-2 rounded-xl border transition-colors ${
                  activeSessionId === session.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-blue-300'
                }`}
              >
                <div className="flex items-center justify-between text-sm font-semibold text-gray-800">
                  <span>Session #{session.id}</span>
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(
                      session.status
                    )}`}
                  >
                    {session.status}
                  </span>
                </div>
                <div className="mt-1 text-xs text-gray-500 line-clamp-2">
                  {session.runbook_title}
                </div>
                <div className="mt-1 text-[11px] text-gray-400">
                  Started {formatDate(session.started_at)}
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}



