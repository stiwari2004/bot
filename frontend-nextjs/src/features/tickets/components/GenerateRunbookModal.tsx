'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { XMarkIcon } from '@heroicons/react/24/outline';

import { apiConfig } from '@/lib/api-config';
import type { Ticket, TicketDetail } from '@/features/tickets/types';

interface GenerateRunbookModalProps {
  ticket: TicketDetail | Ticket | null;
  onClose: () => void;
}

export function GenerateRunbookModal({ ticket, onClose }: GenerateRunbookModalProps) {
  const [issueDescription, setIssueDescription] = useState(
    ticket ? `${ticket.title}${ticket.description ? '\n\n' + ticket.description : ''}` : ''
  );
  const [serviceType, setServiceType] = useState(ticket?.service || 'auto');
  const [envType, setEnvType] = useState(ticket?.environment || 'prod');
  const [riskLevel, setRiskLevel] = useState(
    ticket?.severity === 'critical' ? 'high' : ticket?.severity === 'high' ? 'medium' : 'low'
  );
  const [runbook, setRunbook] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  useEffect(() => {
    if (!ticket) return;
    setIssueDescription(`${ticket.title}${ticket.description ? '\n\n' + ticket.description : ''}`);
    setServiceType(ticket.service || 'auto');
    setEnvType(ticket.environment || 'prod');
    setRiskLevel(ticket.severity === 'critical' ? 'high' : ticket.severity === 'high' ? 'medium' : 'low');
    setRunbook(null);
    setError(null);
  }, [ticket]);

  if (!ticket) {
    return null; // Don't render if no ticket
  }

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!issueDescription.trim()) return;

    setLoading(true);
    setError(null);
    setRunbook(null);

    try {
      const url = apiConfig.endpoints.runbooks.generateAgent();
      const params = new URLSearchParams({
        issue_description: issueDescription,
        service: serviceType,
        env: envType,
        risk: riskLevel,
      });

      if (ticket?.id) {
        params.append('ticket_id', ticket.id.toString());
      }

      const response = await fetch(`${url}?${params.toString()}`, { method: 'POST' });
      if (!response.ok) {
        let errorMessage = `Runbook generation failed: ${response.status}`;
        let errorData: any = null;
        try {
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            errorData = await response.json();
            if (response.status === 409 && errorData?.detail) {
              const existingRunbookId = errorData.detail?.existing_runbook_id;
              if (existingRunbookId) {
                try {
                  const runbookResponse = await fetch(`/api/v1/runbooks/demo/${existingRunbookId}`);
                  if (runbookResponse.ok) {
                    const existingRunbook = await runbookResponse.json();
                    setRunbook(existingRunbook);
                    setError(null);
                    setLoading(false);
                    return;
                  }
                } catch (fetchErr) {
                  console.error('Failed to fetch existing runbook:', fetchErr);
                }
              }
              const detail =
                typeof errorData.detail === 'string'
                  ? errorData.detail
                  : errorData.detail.message || JSON.stringify(errorData.detail);
              errorMessage = `Duplicate runbook detected: ${detail}`;
              if (existingRunbookId) {
                errorMessage += `\n\nExisting runbook ID: ${existingRunbookId}`;
                errorMessage += `\nTitle: ${errorData.detail.existing_runbook_title || 'N/A'}`;
              }
            } else {
              errorMessage = errorData?.detail || errorData?.message || errorMessage;
            }
          } else {
            const errorText = await response.text();
            console.error('Non-JSON error response:', errorText.substring(0, 200));
            errorMessage = `Server error: ${response.status}. Check console for details.`;
          }
        } catch (parseErr) {
          console.error('Error parsing error response:', parseErr);
        }
        throw new Error(errorMessage);
      }

      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        console.error('Non-JSON response received:', text.substring(0, 200));
        throw new Error('Server returned non-JSON response');
      }

      const data = await response.json();
      setRunbook(data);
    } catch (err) {
      console.error('Error generating runbook:', err);
      setError(err instanceof Error ? err.message : 'Runbook generation failed');
    } finally {
      setLoading(false);
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] overflow-y-auto bg-black bg-opacity-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold text-gray-900">Generate Runbook from Ticket</h3>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {!runbook ? (
            <form onSubmit={handleGenerate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Issue Description *</label>
                <textarea
                  value={issueDescription}
                  onChange={(e) => setIssueDescription(e.target.value)}
                  rows={6}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Describe the issue..."
                  required
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Service Type</label>
                  <select
                    value={serviceType}
                    onChange={(e) => setServiceType(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="auto">Auto-detect</option>
                    <option value="database">Database</option>
                    <option value="api">API</option>
                    <option value="infrastructure">Infrastructure</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Environment</label>
                  <select
                    value={envType}
                    onChange={(e) => setEnvType(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="prod">Production</option>
                    <option value="staging">Staging</option>
                    <option value="dev">Development</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Risk Level</label>
                  <select
                    value={riskLevel}
                    onChange={(e) => setRiskLevel(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || !issueDescription.trim()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? 'Generating...' : 'Generate Runbook'}
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-green-800 font-medium">Runbook generated successfully!</p>
                <p className="text-sm text-green-700 mt-1">Runbook ID: {runbook.id}</p>
              </div>
              <div className="border border-gray-200 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-2">{runbook.title}</h4>
                <div className="prose max-w-none text-sm">
                  <pre className="whitespace-pre-wrap bg-gray-50 p-4 rounded border overflow-x-auto">{runbook.body_md}</pre>
                </div>
              </div>
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              )}
              <div className="flex items-center justify-end gap-3 pt-4 border-t">
                <button
                  onClick={async () => {
                    setRunbook(null);
                    setError(null);
                    await handleGenerate({ preventDefault: () => {} } as React.FormEvent);
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Recreate
                </button>
                <button
                  onClick={async () => {
                    try {
                      const response = await fetch(apiConfig.buildUrl(`/api/v1/runbooks/demo/${runbook.id}/approve`), {
                        method: 'POST',
                      });
                      if (!response.ok) {
                        const errorData = await response.json().catch(() => ({ detail: 'Failed to approve runbook' }));
                        throw new Error(errorData.detail || 'Failed to approve runbook');
                      }
                      alert('Runbook approved successfully!');
                      onClose();
                    } catch (err) {
                      setError(err instanceof Error ? err.message : 'Failed to approve runbook');
                    }
                  }}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  Approve
                </button>
                <button onClick={onClose} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}

