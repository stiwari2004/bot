'use client';

import { useState, useEffect } from 'react';
import {
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  DocumentTextIcon,
  AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';

interface PendingApproval {
  session_id: number;
  step_id: number;
  step_number: number;
  runbook_id: number;
  runbook_title?: string;
  ticket_id?: number;
  command?: string;
  command_payload?: any;
  waiting_since?: string;
  current_parameters?: any;
}

interface AuditTrailEntry {
  id: number;
  action: string;
  user_id?: number;
  timestamp: string;
  reason?: string;
  modified_parameters?: any;
  original_parameters?: any;
  outcome?: string;
}

export function HumanInLoopWorkspace() {
  const { token } = useAuth();
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [selectedSession, setSelectedSession] = useState<number | null>(null);
  const [auditTrail, setAuditTrail] = useState<AuditTrailEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [tuningParams, setTuningParams] = useState<Record<string, any>>({});
  const [approvalReason, setApprovalReason] = useState('');

  useEffect(() => {
    fetchPendingApprovals();
  }, []);

  useEffect(() => {
    if (selectedSession) {
      fetchAuditTrail(selectedSession);
    }
  }, [selectedSession]);

  const fetchPendingApprovals = async () => {
    setLoading(true);
    try {
      const url = apiConfig.endpoints.workspace.pendingApprovals();
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(url, { headers });
      if (!response.ok) throw new Error('Failed to fetch pending approvals');
      const data = await response.json();
      setPendingApprovals(data);
    } catch (err) {
      console.error('Error fetching pending approvals:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAuditTrail = async (sessionId: number) => {
    try {
      const url = apiConfig.endpoints.workspace.auditTrail(sessionId);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(url, { headers });
      if (!response.ok) throw new Error('Failed to fetch audit trail');
      const data = await response.json();
      setAuditTrail(data);
    } catch (err) {
      console.error('Error fetching audit trail:', err);
    }
  };

  const handleApprove = async (sessionId: number, stepId: number, approve: boolean) => {
    try {
      const url = apiConfig.endpoints.workspace.approve(sessionId, stepId);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const body: any = { approve, reason: approvalReason };
      if (Object.keys(tuningParams).length > 0) {
        body.parameters = tuningParams;
      }

      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });

      if (!response.ok) throw new Error('Failed to approve/reject step');
      
      await fetchPendingApprovals();
      setTuningParams({});
      setApprovalReason('');
      setSelectedSession(null);
    } catch (err) {
      console.error('Error approving step:', err);
      alert('Failed to approve/reject step');
    }
  };

  const handleTuneParameters = async (sessionId: number, stepId: number) => {
    try {
      const url = apiConfig.endpoints.workspace.tuneParameters(sessionId, stepId);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          parameters: tuningParams,
          reason: approvalReason,
        }),
      });

      if (!response.ok) throw new Error('Failed to tune parameters');
      
      alert('Parameters tuned successfully');
      setTuningParams({});
    } catch (err) {
      console.error('Error tuning parameters:', err);
      alert('Failed to tune parameters');
    }
  };

  if (loading) {
    return (
      <Card variant="elevated">
        <CardContent padding="md">
          <div className="flex items-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
            <span>Loading pending approvals...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card variant="elevated">
        <CardHeader>
          <div className="flex items-center gap-2">
            <ClockIcon className="h-5 w-5 text-primary-600" />
            <h3 className="font-semibold text-neutral-900">Pending Approvals</h3>
            <span className="text-sm text-neutral-500">({pendingApprovals.length})</span>
          </div>
        </CardHeader>
        <CardContent padding="md">
          {pendingApprovals.length === 0 ? (
            <p className="text-sm text-neutral-500">No pending approvals</p>
          ) : (
            <div className="space-y-4">
              {pendingApprovals.map((approval) => (
                <Card key={approval.session_id} variant="outlined">
                  <CardContent padding="md">
                    <div className="space-y-4">
                      <div>
                        <h4 className="font-semibold text-neutral-900">{approval.runbook_title}</h4>
                        <p className="text-sm text-neutral-600">
                          Session {approval.session_id} • Step {approval.step_number}
                        </p>
                        {approval.command && (
                          <p className="text-xs text-neutral-500 mt-2 font-mono bg-neutral-50 p-2 rounded">
                            {approval.command}
                          </p>
                        )}
                      </div>

                      {approval.current_parameters && (
                        <div>
                          <h5 className="text-sm font-semibold mb-2 flex items-center gap-1">
                            <AdjustmentsHorizontalIcon className="h-4 w-4" />
                            Current Parameters
                          </h5>
                          <div className="space-y-2">
                            {Object.entries(approval.current_parameters).map(([key, value]) => (
                              <div key={key} className="flex flex-col gap-1">
                                <label className="text-xs font-medium text-neutral-700">
                                  {key}
                                </label>
                                <Input
                                  value={tuningParams[key] ?? String(value)}
                                  onChange={(e) =>
                                    setTuningParams({ ...tuningParams, [key]: e.target.value })
                                  }
                                  className="flex-1"
                                />
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <div>
                        <label className="block text-sm font-semibold text-neutral-900 mb-2">
                          Reason (optional)
                        </label>
                        <Textarea
                          value={approvalReason}
                          onChange={(e) => setApprovalReason(e.target.value)}
                          placeholder="Enter reason for approval/rejection..."
                        />
                      </div>

                      <div className="flex gap-2">
                        <Button
                          variant="primary"
                          onClick={() => handleApprove(approval.session_id, approval.step_id, true)}
                        >
                          <CheckCircleIcon className="h-4 w-4 mr-1" />
                          Approve
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => handleApprove(approval.session_id, approval.step_id, false)}
                        >
                          <XCircleIcon className="h-4 w-4 mr-1" />
                          Reject
                        </Button>
                        {Object.keys(tuningParams).length > 0 && (
                          <Button
                            variant="ghost"
                            onClick={() => handleTuneParameters(approval.session_id, approval.step_id)}
                          >
                            Tune Parameters
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          onClick={() => {
                            setSelectedSession(approval.session_id);
                            fetchAuditTrail(approval.session_id);
                          }}
                        >
                          <DocumentTextIcon className="h-4 w-4 mr-1" />
                          View Audit Trail
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {selectedSession && auditTrail.length > 0 && (
        <Card variant="elevated">
          <CardHeader>
            <h3 className="font-semibold text-neutral-900">Audit Trail - Session {selectedSession}</h3>
          </CardHeader>
          <CardContent padding="md">
            <div className="space-y-2">
              {auditTrail.map((entry) => (
                <div key={entry.id} className="flex gap-3 p-3 bg-neutral-50 rounded">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-1 rounded ${
                        entry.action === 'approve' ? 'bg-success-100 text-success-800' :
                        entry.action === 'reject' ? 'bg-error-100 text-error-800' :
                        'bg-warning-100 text-warning-800'
                      }`}>
                        {entry.action}
                      </span>
                      <span className="text-xs text-neutral-500">
                        {new Date(entry.timestamp).toLocaleString()}
                      </span>
                    </div>
                    {entry.reason && (
                      <p className="text-sm text-neutral-600 mt-1">{entry.reason}</p>
                    )}
                    {entry.modified_parameters && (
                      <div className="text-xs text-neutral-500 mt-1">
                        Modified: {JSON.stringify(entry.modified_parameters)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
