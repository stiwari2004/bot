'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { apiConfig } from '@/lib/api-config';
import {
  ArrowPathIcon,
  ArrowDownTrayIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';

interface AuditEvent {
  ts?: number;
  session_id?: number;
  event_type?: string;
  tenant_id?: number;
  payload?: Record<string, unknown>;
  hash?: string;
  prev_hash?: string;
}

export function AuditLogView() {
  const { token } = useAuth();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string>('');
  const [eventType, setEventType] = useState<string>('');
  const [limit, setLimit] = useState(500);
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  const buildParams = useCallback(() => {
    const params: { from_ts?: number; to_ts?: number; session_id?: number; event_type?: string; limit?: number } = {
      limit: Math.min(2000, Math.max(1, limit)),
    };
    if (fromDate) {
      const t = new Date(fromDate).getTime() / 1000;
      if (!Number.isNaN(t)) params.from_ts = t;
    }
    if (toDate) {
      const t = new Date(toDate).getTime() / 1000;
      if (!Number.isNaN(t)) params.to_ts = t;
    }
    const sid = sessionId.trim() ? parseInt(sessionId.trim(), 10) : undefined;
    if (sid != null && !Number.isNaN(sid)) params.session_id = sid;
    if (eventType.trim()) params.event_type = eventType.trim();
    return params;
  }, [fromDate, toDate, sessionId, eventType, limit]);

  const fetchEvents = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const params = buildParams();
      const url = apiConfig.endpoints.auditLog.list(params);
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Request failed: ${res.status}`);
      }
      const data = await res.json();
      setEvents(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load audit log');
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [token, buildParams]);

  useEffect(() => {
    if (token) fetchEvents();
  }, [token]);

  const handleDownload = async () => {
    if (!token) return;
    try {
      const params = buildParams();
      const url = apiConfig.endpoints.auditLog.export(params);
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Export failed');
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.jsonl`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Download failed');
    }
  };

  const formatTs = (ts?: number) => {
    if (ts == null) return '—';
    try {
      return new Date(ts * 1000).toISOString();
    } catch {
      return String(ts);
    }
  };

  const payloadSummary = (p?: Record<string, unknown>) => {
    if (!p) return '—';
    try {
      const s = JSON.stringify(p);
      return s.length > 80 ? s.slice(0, 80) + '…' : s;
    } catch {
      return '—';
    }
  };

  if (!token) {
    return (
      <div className="p-6 text-center text-neutral-600">
        Sign in to view the audit log.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-4">
        <h2 className="text-lg font-semibold text-neutral-900 flex items-center gap-2">
          <DocumentTextIcon className="h-5 w-5" />
          Audit log
        </h2>
      </div>
      <div className="bg-white rounded-xl border border-neutral-200 p-4 shadow-sm">
        <div className="flex flex-wrap gap-4 items-end">
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-neutral-700">From date</span>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="border border-neutral-300 rounded px-2 py-1.5 text-sm"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-neutral-700">To date</span>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="border border-neutral-300 rounded px-2 py-1.5 text-sm"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-neutral-700">Session ID</span>
            <input
              type="text"
              placeholder="Optional"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              className="border border-neutral-300 rounded px-2 py-1.5 text-sm w-28"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-neutral-700">Event type</span>
            <input
              type="text"
              placeholder="Optional"
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="border border-neutral-300 rounded px-2 py-1.5 text-sm w-48"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-neutral-700">Limit</span>
            <input
              type="number"
              min={1}
              max={2000}
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value, 10) || 500)}
              className="border border-neutral-300 rounded px-2 py-1.5 text-sm w-24"
            />
          </label>
          <button
            type="button"
            onClick={fetchEvents}
            disabled={loading}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? <ArrowPathIcon className="h-4 w-4 animate-spin" /> : null}
            Apply
          </button>
          <button
            type="button"
            onClick={handleDownload}
            className="px-4 py-2 border border-neutral-300 rounded-lg hover:bg-neutral-50 flex items-center gap-2"
          >
            <ArrowDownTrayIcon className="h-4 w-4" />
            Download
          </button>
        </div>
      </div>
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
          {error}
        </div>
      )}
      <div className="bg-white rounded-xl border border-neutral-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50">
                <th className="text-left py-2 px-3 font-medium text-neutral-700">Time</th>
                <th className="text-left py-2 px-3 font-medium text-neutral-700">Session</th>
                <th className="text-left py-2 px-3 font-medium text-neutral-700">Event type</th>
                <th className="text-left py-2 px-3 font-medium text-neutral-700">Payload</th>
              </tr>
            </thead>
            <tbody>
              {events.length === 0 && !loading && (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-neutral-500">
                    No events match the filters. Adjust filters and click Apply, or run a runbook to generate events.
                  </td>
                </tr>
              )}
              {events.map((ev, i) => (
                <tr key={i} className="border-b border-neutral-100 hover:bg-neutral-50/50">
                  <td className="py-2 px-3 font-mono text-xs text-neutral-600 whitespace-nowrap">
                    {formatTs(ev.ts)}
                  </td>
                  <td className="py-2 px-3">{ev.session_id ?? '—'}</td>
                  <td className="py-2 px-3 font-medium">{ev.event_type ?? '—'}</td>
                  <td className="py-2 px-3 text-neutral-600 max-w-md truncate" title={JSON.stringify(ev.payload)}>
                    {payloadSummary(ev.payload)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
