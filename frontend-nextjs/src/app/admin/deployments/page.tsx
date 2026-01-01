'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { apiConfig } from '@/lib/api-config';
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { 
  RocketLaunchIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

interface DeploymentApproval {
  id: number;
  deployment_type: string;
  target_environment: string;
  reference_id: number | null;
  reference_name: string | null;
  status: string;
  requested_by: number | null;
  approved_by: number | null;
  approved_at: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  deployed_at: string | null;
  created_at: string;
}

export default function DeploymentsPage() {
  const { user } = useAuth();
  const [approvals, setApprovals] = useState<DeploymentApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [approving, setApproving] = useState<number | null>(null);
  const [rejecting, setRejecting] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchApprovals = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      if (statusFilter) params.append('status_filter', statusFilter);
      if (typeFilter) params.append('deployment_type', typeFilter);
      const url = `/api/v1/deployment-approvals?${params.toString()}`;
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch deployment approvals');
      }

      const data = await response.json();
      setApprovals(data.approvals || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load deployment approvals');
      console.error('Error fetching approvals:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchApprovals();
    }
  }, [user, statusFilter, typeFilter]);

  const handleApprove = async (approvalId: number) => {
    if (!confirm('Are you sure you want to approve this deployment?')) {
      return;
    }

    setApproving(approvalId);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/v1/deployment-approvals/${approvalId}/approve`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to approve deployment');
      }

      alert('Deployment approved successfully!');
      fetchApprovals();
    } catch (err: any) {
      setError(err.message || 'Failed to approve deployment');
      console.error('Error approving deployment:', err);
    } finally {
      setApproving(null);
    }
  };

  const handleReject = async (approvalId: number) => {
    const reason = prompt('Enter rejection reason:');
    if (!reason) {
      return;
    }

    setRejecting(approvalId);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/v1/deployment-approvals/${approvalId}/reject?reason=${encodeURIComponent(reason)}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to reject deployment');
      }

      alert('Deployment rejected');
      fetchApprovals();
    } catch (err: any) {
      setError(err.message || 'Failed to reject deployment');
      console.error('Error rejecting deployment:', err);
    } finally {
      setRejecting(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return <Badge variant="warning"><ClockIcon className="h-4 w-4 mr-1" />Pending</Badge>;
      case 'approved':
        return <Badge variant="success"><CheckCircleIcon className="h-4 w-4 mr-1" />Approved</Badge>;
      case 'rejected':
        return <Badge variant="error"><XCircleIcon className="h-4 w-4 mr-1" />Rejected</Badge>;
      case 'deployed':
        return <Badge variant="success"><RocketLaunchIcon className="h-4 w-4 mr-1" />Deployed</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getTypeBadge = (type: string) => {
    return type === 'code' ? (
      <Badge variant="primary">Code</Badge>
    ) : (
      <Badge variant="secondary">Runbook</Badge>
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-xl bg-gradient-to-br from-blue-100 to-indigo-200">
            <RocketLaunchIcon className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h2 className="text-3xl font-bold text-neutral-900">Deployment Approvals</h2>
            <p className="text-sm text-neutral-600 mt-0.5">Review and approve deployments to production</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardContent padding="md">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex gap-2">
              <Button
                variant={statusFilter === '' ? 'primary' : 'ghost'}
                onClick={() => setStatusFilter('')}
              >
                All Status
              </Button>
              <Button
                variant={statusFilter === 'pending' ? 'primary' : 'ghost'}
                onClick={() => setStatusFilter('pending')}
              >
                Pending
              </Button>
              <Button
                variant={statusFilter === 'approved' ? 'primary' : 'ghost'}
                onClick={() => setStatusFilter('approved')}
              >
                Approved
              </Button>
            </div>
            <div className="flex gap-2">
              <Button
                variant={typeFilter === '' ? 'primary' : 'ghost'}
                onClick={() => setTypeFilter('')}
              >
                All Types
              </Button>
              <Button
                variant={typeFilter === 'code' ? 'primary' : 'ghost'}
                onClick={() => setTypeFilter('code')}
              >
                Code
              </Button>
              <Button
                variant={typeFilter === 'runbook' ? 'primary' : 'ghost'}
                onClick={() => setTypeFilter('runbook')}
              >
                Runbook
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Approvals List */}
      {loading ? (
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
            <div className="text-neutral-600 font-medium">Loading approvals...</div>
          </div>
        </div>
      ) : approvals.length === 0 ? (
        <Card>
          <CardContent padding="lg">
            <div className="text-center py-12">
              <RocketLaunchIcon className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
              <p className="text-neutral-600">No deployment approvals found</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {approvals.map((approval) => (
            <Card key={approval.id}>
              <CardContent padding="md">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      {getTypeBadge(approval.deployment_type)}
                      {getStatusBadge(approval.status)}
                      {approval.reference_name && (
                        <span className="text-sm font-medium text-neutral-700">
                          {approval.reference_name}
                        </span>
                      )}
                    </div>
                    {approval.rejection_reason && (
                      <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-800">
                        Rejection reason: {approval.rejection_reason}
                      </div>
                    )}
                    <div className="flex items-center gap-4 text-sm text-neutral-600 mt-2">
                      {approval.reference_id && (
                        <span>ID: {approval.reference_id}</span>
                      )}
                      <span>Created: {new Date(approval.created_at).toLocaleString()}</span>
                      {approval.approved_at && (
                        <span>Approved: {new Date(approval.approved_at).toLocaleString()}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {approval.status === 'pending' && (
                      <>
                        <Button
                          variant="primary"
                          onClick={() => handleApprove(approval.id)}
                          disabled={approving === approval.id}
                          leftIcon={<CheckCircleIcon className="h-4 w-4" />}
                        >
                          {approving === approval.id ? 'Approving...' : 'Approve'}
                        </Button>
                        <Button
                          variant="error"
                          onClick={() => handleReject(approval.id)}
                          disabled={rejecting === approval.id}
                          leftIcon={<XCircleIcon className="h-4 w-4" />}
                        >
                          {rejecting === approval.id ? 'Rejecting...' : 'Reject'}
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

