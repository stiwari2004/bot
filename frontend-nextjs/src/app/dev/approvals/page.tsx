'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { apiConfig } from '@/lib/api-config';
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { 
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowUpTrayIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

interface PendingRunbook {
  id: number;
  title: string;
  status: string;
  confidence: number | null;
  created_at: string;
  valid_for_promotion: boolean;
  validation_error: string | null;
}

export default function DevApprovalsPage() {
  const { user } = useAuth();
  const [pending, setPending] = useState<PendingRunbook[]>([]);
  const [loading, setLoading] = useState(true);
  const [promoting, setPromoting] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchPending = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(apiConfig.endpoints.dev.runbooks.pendingPromotion(), {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch pending runbooks');
      }

      const data = await response.json();
      setPending(data.pending || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load pending runbooks');
      console.error('Error fetching pending runbooks:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchPending();
    }
  }, [user]);

  const handlePromote = async (runbookId: number) => {
    if (!confirm('Are you sure you want to promote this runbook to production?')) {
      return;
    }

    setPromoting(runbookId);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(apiConfig.endpoints.dev.runbooks.promote(runbookId, false), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to promote runbook');
      }

      const data = await response.json();
      alert(`Runbook promoted successfully! Production runbook ID: ${data.production_runbook_id}`);
      fetchPending();
    } catch (err: any) {
      setError(err.message || 'Failed to promote runbook');
      console.error('Error promoting runbook:', err);
    } finally {
      setPromoting(null);
    }
  };

  const handleBulkPromote = async () => {
    const validRunbooks = pending.filter(rb => rb.valid_for_promotion);
    if (validRunbooks.length === 0) {
      alert('No valid runbooks to promote');
      return;
    }

    if (!confirm(`Promote ${validRunbooks.length} runbook(s) to production?`)) {
      return;
    }

    setError(null);
    const results = [];
    for (const runbook of validRunbooks) {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(apiConfig.endpoints.dev.runbooks.promote(runbook.id, false), {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          results.push({ id: runbook.id, success: true });
        } else {
          const errorData = await response.json();
          results.push({ id: runbook.id, success: false, error: errorData.detail });
        }
      } catch (err: any) {
        results.push({ id: runbook.id, success: false, error: err.message });
      }
    }

    const successCount = results.filter(r => r.success).length;
    alert(`Promoted ${successCount} of ${validRunbooks.length} runbook(s)`);
    fetchPending();
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-xl bg-gradient-to-br from-yellow-100 to-orange-200">
            <ClockIcon className="h-6 w-6 text-yellow-600" />
          </div>
          <div>
            <h2 className="text-3xl font-bold text-neutral-900">Pending Approvals</h2>
            <p className="text-sm text-neutral-600 mt-0.5">Runbooks ready for promotion to production</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Bulk Actions */}
      {pending.filter(rb => rb.valid_for_promotion).length > 0 && (
        <Card>
          <CardContent padding="md">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-neutral-600">
                  {pending.filter(rb => rb.valid_for_promotion).length} runbook(s) ready for promotion
                </p>
              </div>
              <Button
                variant="primary"
                onClick={handleBulkPromote}
                leftIcon={<ArrowUpTrayIcon className="h-4 w-4" />}
              >
                Bulk Promote
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pending Runbooks */}
      {loading ? (
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
            <div className="text-neutral-600 font-medium">Loading pending runbooks...</div>
          </div>
        </div>
      ) : pending.length === 0 ? (
        <Card>
          <CardContent padding="lg">
            <div className="text-center py-12">
              <CheckCircleIcon className="h-12 w-12 text-green-400 mx-auto mb-4" />
              <p className="text-neutral-600">No runbooks pending promotion</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {pending.map((runbook) => (
            <Card key={runbook.id}>
              <CardContent padding="md">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-neutral-900">{runbook.title}</h3>
                      {runbook.valid_for_promotion ? (
                        <Badge variant="success">
                          <CheckCircleIcon className="h-4 w-4 mr-1" />
                          Ready
                        </Badge>
                      ) : (
                        <Badge variant="error">
                          <ExclamationTriangleIcon className="h-4 w-4 mr-1" />
                          Invalid
                        </Badge>
                      )}
                    </div>
                    {runbook.validation_error && (
                      <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-800">
                        {runbook.validation_error}
                      </div>
                    )}
                    <div className="flex items-center gap-4 text-sm text-neutral-600 mt-2">
                      {runbook.confidence && (
                        <span>Confidence: {(runbook.confidence * 100).toFixed(0)}%</span>
                      )}
                      <span>Created: {new Date(runbook.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {runbook.valid_for_promotion && (
                      <Button
                        variant="primary"
                        onClick={() => handlePromote(runbook.id)}
                        disabled={promoting === runbook.id}
                        leftIcon={<ArrowUpTrayIcon className="h-4 w-4" />}
                      >
                        {promoting === runbook.id ? 'Promoting...' : 'Promote'}
                      </Button>
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

