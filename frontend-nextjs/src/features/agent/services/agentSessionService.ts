/**
 * agentSessionService — all API calls for agent session actions.
 * Components import from here; no authFetch calls live in component files.
 */
import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';

async function post<T = unknown>(url: string, body: unknown): Promise<T> {
  const res = await authFetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail || 'Request failed');
  }
  return res.json();
}

export async function fetchSessionPlan(sessionId: number) {
  const res = await authFetch(apiConfig.endpoints.executions.agentSessionPlan(sessionId));
  if (!res.ok) throw new Error('Failed to load session status');
  return res.json();
}

export function setExclusions(sessionId: number, exclusions: string[]) {
  return post(apiConfig.endpoints.executions.agentSessionSetExclusions(sessionId), { exclusions });
}

export function escalateSession(sessionId: number, reason?: string) {
  return post(apiConfig.endpoints.executions.agentSessionEscalate(sessionId), { reason: reason || null });
}

export function confirmResolution(sessionId: number, resolved: boolean) {
  return post(apiConfig.endpoints.executions.agentSessionConfirmResolution(sessionId), { resolved });
}

export function reviewSession(sessionId: number, saveAsRunbook: boolean, runbookTitle?: string) {
  return post(apiConfig.endpoints.executions.agentSessionReview(sessionId), {
    weed_step_numbers: [],
    save_as_runbook: saveAsRunbook,
    runbook_title: runbookTitle || undefined,
  });
}

export function submitFeedback(sessionId: number, feedback: string) {
  return post(apiConfig.endpoints.executions.agentSessionFeedback(sessionId), { feedback });
}

export function retrySession(sessionId: number, userDirection?: string) {
  return post<{ session_id: number }>(
    apiConfig.endpoints.executions.agentSessionRetry(sessionId),
    userDirection?.trim() ? { user_direction: userDirection.trim() } : {},
  );
}

export function flagRunbookForReview(runbookId: number) {
  return post(apiConfig.endpoints.quarantine.quarantine(runbookId), { reason: 'review_flag' });
}
