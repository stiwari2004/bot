'use client';

import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { XMarkIcon } from '@heroicons/react/24/outline';

import type { Ticket, TicketDetail } from '@/features/tickets/types';
import { useAgentSession } from '@/features/tickets/hooks/useAgentSession';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface Props {
  ticket: TicketDetail | Ticket | null;
  onClose: () => void;
  onAgentStarted: (sessionId: number) => void;
}

export function GenerateRunbookModal({ ticket, onClose, onAgentStarted }: Props) {
  const [state, actions] = useAgentSession(ticket, onAgentStarted);
  const { issueDescription, starting, error } = state;

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = 'unset'; };
  }, []);

  if (!ticket) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div onClick={e => e.stopPropagation()} className="max-w-2xl w-full">
        <Card variant="elevated">
          <div className="flex items-center justify-between px-6 pt-5 pb-3 border-b border-neutral-100">
            <h3 className="text-xl font-bold text-neutral-900">Run Agent</h3>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <XMarkIcon className="h-6 w-6" />
            </Button>
          </div>

          <CardContent padding="md">
            <form onSubmit={actions.startAgent} className="space-y-4">
              <Card variant="outlined" className="border-blue-200 bg-blue-50">
                <CardContent padding="sm">
                  <p className="text-sm text-blue-800 font-medium">
                    The agent will connect to the target server, diagnose the issue, and propose
                    a fix plan for your approval before executing anything.
                  </p>
                </CardContent>
              </Card>

              <div>
                <label className="block text-sm font-semibold text-neutral-700 mb-2">
                  Issue Description *
                </label>
                <textarea
                  value={issueDescription}
                  onChange={e => actions.setIssueDescription(e.target.value)}
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
                <Button type="button" variant="outline" onClick={onClose} disabled={starting}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  isLoading={starting}
                  disabled={starting || !issueDescription.trim()}
                >
                  Start Agent
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>,
    document.body
  );
}
