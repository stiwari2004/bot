'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { XMarkIcon } from '@heroicons/react/24/outline';

import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';
import type { Ticket, TicketDetail } from '@/features/tickets/types';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface GenerateRunbookModalProps {
  ticket: TicketDetail | Ticket | null;
  onClose: () => void;
}

export function GenerateRunbookModal({ ticket, onClose }: GenerateRunbookModalProps) {
  const [issueDescription, setIssueDescription] = useState(
    ticket ? `${ticket.title}${ticket.description ? '\n\n' + ticket.description : ''}` : ''
  );
  // CI Type: server, database, web, storage, network
  const [ciType, setCiType] = useState('auto');
  // OS Type: Windows, Linux (only for servers)
  const [osType, setOsType] = useState<string>('auto');
  const [envType, setEnvType] = useState(ticket?.environment || 'prod');
  const [riskLevel, setRiskLevel] = useState(
    ticket?.severity === 'critical' ? 'high' : ticket?.severity === 'high' ? 'medium' : 'low'
  );
  const [runbook, setRunbook] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detectingOS, setDetectingOS] = useState(false);
  const [reviewStatus, setReviewStatus] = useState<any | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  useEffect(() => {
    if (!ticket) return;
    setIssueDescription(`${ticket.title}${ticket.description ? '\n\n' + ticket.description : ''}`);
    // Map ticket.service to CI type (if it's Windows/Linux, treat as server)
    const ticketService = ticket.service || 'auto';
    if (ticketService === 'Windows' || ticketService === 'Linux') {
      setCiType('server');
      setOsType(ticketService);
    } else {
      setCiType(ticketService || 'auto');
      setOsType('auto');
    }
    setEnvType(ticket.environment || 'prod');
    setRiskLevel(ticket.severity === 'critical' ? 'high' : ticket.severity === 'high' ? 'medium' : 'low');
    setRunbook(null);
    setError(null);
    setReviewStatus(null);
  }, [ticket]);

  const loadReviewStatus = async (runbookId: number) => {
    try {
      setReviewLoading(true);
      const res = await authFetch(apiConfig.endpoints.runbooks.reviewStatus(runbookId));
      if (!res.ok) {
        throw new Error('Failed to load review status');
      }
      const data = await res.json();
      setReviewStatus(data);
    } catch (e) {
      console.error('Failed to load review status', e);
    } finally {
      setReviewLoading(false);
    }
  };

  const reloadRunbook = async (runbookId: number) => {
    try {
      const res = await authFetch(apiConfig.buildUrl(`/api/v1/runbooks/demo/${runbookId}`));
      if (!res.ok) return;
      const data = await res.json();
      setRunbook(data);
    } catch (e) {
      console.error('Failed to reload runbook', e);
    }
  };

  // Auto-detect OS from server name in issue description (for servers only)
  useEffect(() => {
    const detectOS = async () => {
      // Only detect OS if CI type is server (or auto which might be server)
      if (ciType !== 'auto' && ciType !== 'server') {
        return;
      }
      
      // Don't override if OS type is already set manually
      if (osType !== 'auto') {
        return;
      }

      // Extract server name from issue description (simple pattern matching)
      const serverPatterns = [
        /\b([A-Za-z0-9-]+(?:VM|vm|Server|server))\b/g,
        /\b([A-Za-z0-9-]+\.(?:local|com|net|org))\b/g,
        /\b(InfraBotTestVM\d+)\b/gi,
      ];

      let serverName: string | null = null;
      for (const pattern of serverPatterns) {
        const matches = issueDescription.match(pattern);
        if (matches && matches.length > 0) {
          serverName = matches[0];
          break;
        }
      }

      // Also check for common server name patterns
      if (!serverName) {
        const words = issueDescription.split(/\s+/);
        for (const word of words) {
          // Look for words that might be server names (alphanumeric with dashes, 3+ chars)
          if (/^[A-Za-z0-9-]{3,}$/.test(word) && !['server', 'database', 'service', 'application'].includes(word.toLowerCase())) {
            serverName = word;
            break;
          }
        }
      }

      if (serverName) {
        setDetectingOS(true);
        try {
          const response = await fetch(apiConfig.endpoints.runbooks.detectOS(serverName));
          if (response.ok) {
            const data = await response.json();
            if (data.detected && data.os_type) {
              setOsType(data.os_type);  // Set OS type
              // If CI type is auto, set it to server since we detected an OS
              if (ciType === 'auto') {
                setCiType('server');
              }
            }
          }
        } catch (err) {
          console.error('Failed to detect OS:', err);
        } finally {
          setDetectingOS(false);
        }
      }
    };

    // Debounce the detection
    const timeoutId = setTimeout(detectOS, 1000);
    return () => clearTimeout(timeoutId);
  }, [issueDescription, ciType, osType]);

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

      // Determine service parameter: if CI type is server and OS type is set, use OS type for backward compatibility
      // Otherwise use CI type
      let serviceParam = ciType;
      if (ciType === 'server' && osType !== 'auto' && osType !== '') {
        serviceParam = osType; // Backward compatibility: Windows/Linux treated as server
      } else if (ciType === 'auto') {
        serviceParam = 'auto';
      }

      const body: any = {
        issue_description: issueDescription,
        service: serviceParam,
        env: envType,
        risk: riskLevel,
      };

      if (ticket?.id) {
        body.ticket_id = ticket.id;
      }

      const response = await authFetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });
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
                    // Show an informational message (not an error) that we found an existing runbook
                    setError(`ℹ️ A similar runbook already exists: "${existingRunbook.title || errorData.detail.existing_runbook_title}" (ID: ${existingRunbookId}). It has been loaded for you.`);
                    setLoading(false);
                    return; // Exit early - we successfully loaded the existing runbook
                  } else {
                    // If fetch fails, show the duplicate message with the ID
                    const detail =
                      typeof errorData.detail === 'string'
                        ? errorData.detail
                        : errorData.detail.message || JSON.stringify(errorData.detail);
                    errorMessage = `Duplicate runbook detected: ${detail}`;
                    if (existingRunbookId) {
                      errorMessage += `\n\nExisting runbook ID: ${existingRunbookId}`;
                      errorMessage += `\nTitle: ${errorData.detail.existing_runbook_title || 'N/A'}`;
                    }
                  }
                } catch (fetchErr) {
                  console.error('Failed to fetch existing runbook:', fetchErr);
                  // Show error but include the runbook ID so user can find it
                  const detail =
                    typeof errorData.detail === 'string'
                      ? errorData.detail
                      : errorData.detail.message || JSON.stringify(errorData.detail);
                  errorMessage = `Duplicate runbook detected: ${detail}`;
                  if (existingRunbookId) {
                    errorMessage += `\n\nExisting runbook ID: ${existingRunbookId}`;
                    errorMessage += `\nTitle: ${errorData.detail.existing_runbook_title || 'N/A'}`;
                  }
                }
              } else {
                // No existing runbook ID provided
                const detail =
                  typeof errorData.detail === 'string'
                    ? errorData.detail
                    : errorData.detail.message || JSON.stringify(errorData.detail);
                errorMessage = `Duplicate runbook detected: ${detail}`;
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
        setError(errorMessage);
        setLoading(false);
        return;
      }

      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        console.error('Non-JSON response received:', text.substring(0, 200));
        throw new Error('Server returned non-JSON response');
      }

      const data = await response.json();
      setRunbook(data);
      loadReviewStatus(data.id);
    } catch (err) {
      console.error('Error generating runbook:', err);
      setError(err instanceof Error ? err.message : 'Runbook generation failed');
    } finally {
      setLoading(false);
    }
  };

  const pendingReviewSteps = (reviewStatus?.steps || []).filter(
    (s: any) =>
      (s.command_validation_status === 'invalid' || s.command_validation_status === 'pending_review') &&
      s.command_review_status !== 'approved_by_human'
  );

  const handleApproveStep = async (step: any) => {
    if (!runbook) return;
    try {
      const res = await authFetch(apiConfig.endpoints.runbooks.stepApprove(runbook.id), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section: step.section, index: step.index }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to approve step');
      }
      await loadReviewStatus(runbook.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to approve step');
    }
  };

  const handleUseSuggested = async (step: any) => {
    if (!runbook) return;
    if (!step.command_suggested_fix) return;
    try {
      const res = await authFetch(apiConfig.endpoints.runbooks.stepUpdateCommand(runbook.id), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section: step.section,
          index: step.index,
          command: step.command_suggested_fix,
        }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to update command');
      }
      await reloadRunbook(runbook.id);
      await loadReviewStatus(runbook.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to apply suggested command');
    }
  };

  const handleRedoCommand = async (step: any) => {
    if (!runbook) return;
    // Simple prompt for optional human context; cancel if user closes dialog
    const humanContext = window.prompt(
      'Optional: provide extra context for regenerating this command (e.g. \"use bash\", \"RHEL 8\", \"mon01 is production\").\nLeave empty to let AI decide.',
      ''
    );
    if (humanContext === null) {
      return;
    }
    try {
      const res = await authFetch(apiConfig.endpoints.runbooks.stepRegenerate(runbook.id), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section: step.section,
          index: step.index,
          human_context: humanContext || undefined,
        }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to regenerate command');
      }
      await reloadRunbook(runbook.id);
      await loadReviewStatus(runbook.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to regenerate command');
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="max-w-4xl w-full max-h-[90vh] overflow-y-auto"
      >
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-bold text-neutral-900">Generate Runbook from Ticket</h3>
              <Button variant="ghost" size="sm" onClick={onClose}>
                <XMarkIcon className="h-6 w-6" />
              </Button>
            </div>
          </CardHeader>
          <CardContent padding="md">

          {!runbook ? (
            <form onSubmit={handleGenerate} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-neutral-700 mb-2">Issue Description *</label>
                <textarea
                  value={issueDescription}
                  onChange={(e) => setIssueDescription(e.target.value)}
                  rows={6}
                  className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                  placeholder="Describe the issue..."
                  required
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">CI Type *</label>
                  <select
                    value={ciType}
                    onChange={(e) => {
                      setCiType(e.target.value);
                      // Reset OS type if CI type is not server
                      if (e.target.value !== 'server' && e.target.value !== 'auto') {
                        setOsType('auto');
                      }
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="auto">Auto-detect</option>
                    <option value="server">Server</option>
                    <option value="database">Database</option>
                    <option value="web">Web Application</option>
                    <option value="storage">Storage</option>
                    <option value="network">Network</option>
                  </select>
                  <p className="mt-1 text-xs text-neutral-500">CI Type: server, router, switch, storage, etc.</p>
                </div>
                
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    OS Type {ciType === 'server' || ciType === 'auto' ? '*' : '(N/A)'}
                  </label>
                  <select
                    value={osType}
                    onChange={(e) => setOsType(e.target.value)}
                    disabled={ciType !== 'server' && ciType !== 'auto'}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                  >
                    <option value="auto">Auto-detect {detectingOS && '(detecting...)'}</option>
                    <option value="Windows">Windows</option>
                    <option value="Linux">Linux</option>
                  </select>
                  <p className="mt-1 text-xs text-neutral-500">
                    {ciType === 'server' || ciType === 'auto' 
                      ? 'OS Type: Windows or Linux (only for servers)'
                      : 'OS Type not applicable for this CI type'}
                  </p>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Environment
                  </label>
                  <select
                    value={envType}
                    onChange={(e) => setEnvType(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="prod">Production</option>
                    <option value="staging">Staging</option>
                    <option value="dev">Development</option>
                    <option value="testing">Testing</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">Risk Level</label>
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
                <Card variant="outlined" className="border-error-200 bg-error-50">
                  <CardContent padding="sm">
                    <p className="text-sm text-error-800 font-medium">{error}</p>
                  </CardContent>
                </Card>
              )}

              <div className="flex items-center justify-end gap-3 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={onClose}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  disabled={loading || !issueDescription.trim()}
                  isLoading={loading}
                >
                  {loading ? 'Generating...' : 'Generate Runbook'}
                </Button>
              </div>
            </form>
          ) : (
            <div className="space-y-4">
              {reviewStatus && !reviewStatus.command_review_ready && (
                <Card variant="outlined" className="border-amber-200 bg-amber-50">
                  <CardContent padding="md">
                    <p className="text-sm font-semibold text-amber-900">
                      This runbook has {reviewStatus.steps_pending_review} step(s) that need command review before
                      approval.
                    </p>
                    {pendingReviewSteps.length > 0 && (
                      <div className="mt-3 space-y-2 max-h-64 overflow-y-auto">
                        {pendingReviewSteps.map((s: any, idx: number) => (
                          <div
                            key={`${s.section}-${s.index}-${idx}`}
                            className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 rounded-md border border-amber-200 bg-white px-3 py-2"
                          >
                            <div className="text-xs text-neutral-800 text-left">
                              <div className="font-semibold">
                                {s.section} step #{s.index + 1}
                              </div>
                              {s.command_validation_issue && (
                                <div className="text-amber-800">
                                  Issue: {s.command_validation_issue}
                                </div>
                              )}
                              {s.command_suggested_fix && (
                                <div className="text-neutral-700 truncate">
                                  Suggested: <code>{s.command_suggested_fix}</code>
                                </div>
                              )}
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {s.command_suggested_fix && (
                                <Button
                                  size="xs"
                                  variant="outline"
                                  onClick={() => handleUseSuggested(s)}
                                >
                                  Use suggested
                                </Button>
                              )}
                              <Button
                                size="xs"
                                variant="secondary"
                                onClick={() => handleApproveStep(s)}
                              >
                                Mark reviewed
                              </Button>
                              <Button
                                size="xs"
                                variant="ghost"
                                onClick={() => handleRedoCommand(s)}
                              >
                                Redo command
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    {reviewLoading && (
                      <p className="mt-2 text-xs text-amber-700">Refreshing review status…</p>
                    )}
                  </CardContent>
                </Card>
              )}
              <Card variant="outlined" className="border-success-200 bg-success-50">
                <CardContent padding="md">
                  <p className="text-success-800 font-semibold">Runbook generated successfully!</p>
                  <p className="text-sm text-success-700 mt-1">Runbook ID: {runbook.id}</p>
                </CardContent>
              </Card>
              <Card variant="default">
                <CardContent padding="md">
                  <h4 className="font-semibold text-neutral-900 mb-3">{runbook.title}</h4>
                  <div className="prose max-w-none text-sm">
                    <pre className="whitespace-pre-wrap bg-neutral-50 p-4 rounded-lg border-2 border-neutral-200 overflow-x-auto text-neutral-900">{runbook.body_md}</pre>
                  </div>
                </CardContent>
              </Card>
              {error && (
                <Card variant="outlined" className="border-error-200 bg-error-50">
                  <CardContent padding="sm">
                    <p className="text-sm text-error-800 font-medium">{error}</p>
                  </CardContent>
                </Card>
              )}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-neutral-200">
                <Button
                  variant="outline"
                  onClick={async () => {
                    setRunbook(null);
                    setError(null);
                    await handleGenerate({ preventDefault: () => {} } as React.FormEvent);
                  }}
                >
                  Recreate
                </Button>
                <Button
                  variant="success"
                  onClick={async () => {
                    try {
                      // Include ticket_id in approve request if available
                      const approveUrl = ticket?.id 
                        ? apiConfig.buildUrl(`/api/v1/runbooks/demo/${runbook.id}/approve?ticket_id=${ticket.id}`)
                        : apiConfig.buildUrl(`/api/v1/runbooks/demo/${runbook.id}/approve`);
                      
                      const response = await authFetch(approveUrl, {
                        method: 'POST',
                      });
                      if (!response.ok) {
                        let detail = 'Failed to approve runbook';
                        try {
                          const errorData = await response.json();
                          const d = (errorData && (errorData.detail || errorData.message)) || errorData;
                          if (typeof d === 'string') {
                            detail = d;
                          } else if (d && d.message) {
                            detail = d.message;
                          }
                        } catch {
                          // ignore parse error
                        }
                        throw new Error(detail);
                      }
                      alert('Runbook approved successfully!');
                      onClose();
                    } catch (err) {
                      setError(err instanceof Error ? err.message : 'Failed to approve runbook');
                    }
                  }}
                  disabled={reviewStatus && !reviewStatus.command_review_ready}
                >
                  Approve
                </Button>
                <Button variant="primary" onClick={onClose}>
                  Close
                </Button>
              </div>
            </div>
          )}
          </CardContent>
        </Card>
      </div>
    </div>,
    document.body
  );
}
