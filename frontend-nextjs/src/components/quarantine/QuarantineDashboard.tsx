'use client';

import { useState, useEffect } from 'react';
import {
  ShieldExclamationIcon,
  CheckCircleIcon,
  XCircleIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';

interface QuarantineRecord {
  quarantine_id: number;
  runbook_id: number;
  runbook_title?: string;
  runbook_version_id?: number;
  reason: string;
  failure_count: number;
  quarantined_at?: string;
  failure_pattern?: any;
}

interface FailurePattern {
  has_pattern: boolean;
  failure_count?: number;
  error_types?: string[];
  same_error?: boolean;
  varied_errors?: boolean;
  recent_errors?: any[];
  quarantine_reason?: string;
  quarantined_at?: string;
  message?: string;
}

export function QuarantineDashboard() {
  const { token } = useAuth();
  const [pendingReviews, setPendingReviews] = useState<QuarantineRecord[]>([]);
  const [selectedRunbook, setSelectedRunbook] = useState<number | null>(null);
  const [failurePattern, setFailurePattern] = useState<FailurePattern | null>(null);
  const [loading, setLoading] = useState(true);
  const [releaseNotes, setReleaseNotes] = useState('');

  useEffect(() => {
    fetchPendingReviews();
  }, []);

  useEffect(() => {
    if (selectedRunbook) {
      fetchFailurePatterns(selectedRunbook);
    }
  }, [selectedRunbook]);

  const fetchPendingReviews = async () => {
    setLoading(true);
    try {
      const url = apiConfig.endpoints.quarantine.pendingReview();
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(url, { headers });
      if (!response.ok) throw new Error('Failed to fetch pending reviews');
      const data = await response.json();
      setPendingReviews(data);
    } catch (err) {
      console.error('Error fetching pending reviews:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchFailurePatterns = async (runbookId: number) => {
    try {
      const url = apiConfig.endpoints.quarantine.failurePatterns(runbookId);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(url, { headers });
      if (!response.ok) throw new Error('Failed to fetch failure patterns');
      const data = await response.json();
      setFailurePattern(data);
    } catch (err) {
      console.error('Error fetching failure patterns:', err);
    }
  };

  const handleRelease = async (runbookId: number, versionId?: number) => {
    try {
      const url = apiConfig.endpoints.quarantine.release(runbookId);
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
          runbook_version_id: versionId,
          review_notes: releaseNotes,
        }),
      });

      if (!response.ok) throw new Error('Failed to release quarantine');
      
      await fetchPendingReviews();
      setReleaseNotes('');
      setSelectedRunbook(null);
      alert('Quarantine released successfully');
    } catch (err) {
      console.error('Error releasing quarantine:', err);
      alert('Failed to release quarantine');
    }
  };

  if (loading) {
    return (
      <Card variant="elevated">
        <CardContent padding="md">
          <div className="flex items-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
            <span>Loading quarantined runbooks...</span>
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
            <ShieldExclamationIcon className="h-5 w-5 text-warning-600" />
            <h3 className="font-semibold text-neutral-900">Quarantined Runbooks</h3>
            <span className="text-sm text-neutral-500">({pendingReviews.length})</span>
          </div>
        </CardHeader>
        <CardContent padding="md">
          {pendingReviews.length === 0 ? (
            <p className="text-sm text-neutral-500">No runbooks pending review</p>
          ) : (
            <div className="space-y-4">
              {pendingReviews.map((quarantine) => (
                <Card key={quarantine.quarantine_id} variant="outlined" className="border-warning-200">
                  <CardContent padding="md">
                    <div className="space-y-4">
                      <div>
                        <h4 className="font-semibold text-neutral-900">{quarantine.runbook_title}</h4>
                        <div className="flex gap-4 text-sm text-neutral-600 mt-1">
                          <span>Runbook ID: {quarantine.runbook_id}</span>
                          {quarantine.runbook_version_id && (
                            <span>Version: {quarantine.runbook_version_id}</span>
                          )}
                          <span>Failures: {quarantine.failure_count}</span>
                        </div>
                        <div className="mt-2">
                          <span className={`text-xs px-2 py-1 rounded ${
                            quarantine.reason === 'auto_quarantine' 
                              ? 'bg-error-100 text-error-800' 
                              : 'bg-warning-100 text-warning-800'
                          }`}>
                            {quarantine.reason}
                          </span>
                        </div>
                      </div>

                      {quarantine.failure_pattern && (
                        <div>
                          <h5 className="text-sm font-semibold mb-2 flex items-center gap-1">
                            <ChartBarIcon className="h-4 w-4" />
                            Failure Pattern
                          </h5>
                          <div className="text-xs text-neutral-600 space-y-1">
                            {quarantine.failure_pattern.error_types && (
                              <p>Error Types: {quarantine.failure_pattern.error_types.join(', ')}</p>
                            )}
                            {quarantine.failure_pattern.same_error !== undefined && (
                              <p>
                                Pattern: {quarantine.failure_pattern.same_error 
                                  ? 'Same error repeated' 
                                  : 'Varied errors'}
                              </p>
                            )}
                          </div>
                        </div>
                      )}

                      <div>
                        <label className="block text-sm font-semibold text-neutral-900 mb-2">
                          Review Notes
                        </label>
                        <Textarea
                          value={releaseNotes}
                          onChange={(e) => setReleaseNotes(e.target.value)}
                          placeholder="Enter review notes before releasing..."
                        />
                      </div>

                      <div className="flex gap-2">
                        <Button
                          variant="primary"
                          onClick={() => {
                            setSelectedRunbook(quarantine.runbook_id);
                            fetchFailurePatterns(quarantine.runbook_id);
                          }}
                        >
                          <ChartBarIcon className="h-4 w-4 mr-1" />
                          Analyze Patterns
                        </Button>
                        <Button
                          variant="primary"
                          onClick={() => handleRelease(quarantine.runbook_id, quarantine.runbook_version_id)}
                        >
                          <CheckCircleIcon className="h-4 w-4 mr-1" />
                          Release Quarantine
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

      {selectedRunbook && failurePattern && (
        <Card variant="elevated">
          <CardHeader>
            <h3 className="font-semibold text-neutral-900">Failure Pattern Analysis</h3>
          </CardHeader>
          <CardContent padding="md">
            {failurePattern.has_pattern ? (
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-neutral-600">
                    Total Failures: <span className="font-semibold">{failurePattern.failure_count}</span>
                  </p>
                  {failurePattern.error_types && (
                    <div className="mt-2">
                      <p className="text-sm font-semibold mb-1">Error Types:</p>
                      <div className="flex flex-wrap gap-1">
                        {failurePattern.error_types.map((type, idx) => (
                          <span key={idx} className="text-xs px-2 py-1 bg-neutral-100 rounded">
                            {type}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {failurePattern.same_error !== undefined && (
                    <p className="text-sm text-neutral-600 mt-2">
                      Pattern: {failurePattern.same_error 
                        ? 'Same error repeated (systematic issue)' 
                        : 'Varied errors (environmental or configuration issue)'}
                    </p>
                  )}
                </div>
                {failurePattern.recent_errors && failurePattern.recent_errors.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold mb-2">Recent Errors:</p>
                    <div className="space-y-2">
                      {failurePattern.recent_errors.map((error: any, idx: number) => (
                        <div key={idx} className="text-xs p-2 bg-neutral-50 rounded">
                          <p className="font-semibold">{error.error_type || 'Unknown'}</p>
                          <p className="text-neutral-600 mt-1">{error.error?.substring(0, 200)}</p>
                          {error.timestamp && (
                            <p className="text-neutral-400 mt-1">
                              {new Date(error.timestamp).toLocaleString()}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-neutral-500">{failurePattern.message || 'No pattern data available'}</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
