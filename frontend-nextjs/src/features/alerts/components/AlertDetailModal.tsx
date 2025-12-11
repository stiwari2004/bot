'use client';

import { useState } from 'react';
import { XMarkIcon, BellIcon, CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline';
import type { AlertDetail } from '../types';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

interface AlertDetailModalProps {
  alert: AlertDetail | null;
  loading: boolean;
  onClose: () => void;
  onUpdate?: (alertId: number, status: string, notes?: string) => Promise<void>;
}

export function AlertDetailModal({ alert, loading, onClose, onUpdate }: AlertDetailModalProps) {
  const [updating, setUpdating] = useState(false);
  const [notes, setNotes] = useState('');
  const [showNotesInput, setShowNotesInput] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpdateStatus = async (status: string) => {
    if (!alert || !onUpdate) return;

    setUpdating(true);
    setError(null);
    try {
      await onUpdate(alert.id, status, notes || undefined);
      setNotes('');
      setShowNotesInput(false);
      // Optionally close modal after update
      // onClose();
    } catch (err) {
      console.error('Error updating alert:', err);
      setError(err instanceof Error ? err.message : 'Failed to update alert. Please try again.');
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
        <Card variant="elevated" className="max-w-2xl w-full mx-4">
          <CardContent padding="lg">
            <div className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              <span className="ml-3 text-neutral-600 font-medium">Loading alert details...</span>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!alert) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        className="max-w-4xl w-full max-h-[90vh] overflow-y-auto"
      >
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-1.5 rounded-lg bg-warning-100">
                  <BellIcon className="h-6 w-6 text-warning-600" />
                </div>
                <h2 className="text-2xl font-bold text-neutral-900">Alert Details</h2>
              </div>
              <Button variant="ghost" size="sm" onClick={onClose}>
                <XMarkIcon className="h-6 w-6" />
              </Button>
            </div>
            
            {/* Action Buttons */}
            {alert.status !== 'resolved' && onUpdate && (
              <div className="space-y-3">
                <div className="flex gap-2 flex-wrap">
                  <Button
                    variant="success"
                    onClick={() => handleUpdateStatus('resolved')}
                    disabled={updating}
                    isLoading={updating}
                    leftIcon={<CheckCircleIcon className="h-5 w-5" />}
                  >
                    {updating ? 'Resolving...' : 'Resolve Alert'}
                  </Button>
                  {alert.status === 'firing' && (
                    <Button
                      variant="warning"
                      onClick={() => handleUpdateStatus('acknowledged')}
                      disabled={updating}
                      isLoading={updating}
                      leftIcon={<ExclamationCircleIcon className="h-5 w-5" />}
                    >
                      {updating ? 'Acknowledging...' : 'Acknowledge'}
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    onClick={() => setShowNotesInput(!showNotesInput)}
                  >
                    {showNotesInput ? 'Hide Notes' : 'Add Notes'}
                  </Button>
                </div>
                
                {/* Error Message */}
                {error && (
                  <Card variant="outlined" className="border-error-200 bg-error-50">
                    <CardContent padding="sm">
                      <p className="text-sm text-error-800 font-medium">{error}</p>
                    </CardContent>
                  </Card>
                )}
                
                {/* Notes Input */}
                {showNotesInput && (
                  <div>
                    <textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Add notes about this update..."
                      className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                      rows={3}
                    />
                  </div>
                )}
              </div>
            )}
            
            {/* Status Info for Resolved/Acknowledged */}
            {alert.status !== 'firing' && (
              <Card variant="outlined" className={alert.status === 'resolved' ? 'border-success-200 bg-success-50' : 'border-warning-200 bg-warning-50'}>
                <CardContent padding="sm">
                  <p className={`text-sm font-semibold ${
                    alert.status === 'resolved' ? 'text-success-800' : 'text-warning-800'
                  }`}>
                    This alert has been {alert.status}.
                    {alert.resolved_at && (
                      <span className="ml-2 text-neutral-600">
                        Resolved at: {new Date(alert.resolved_at).toLocaleString()}
                      </span>
                    )}
                  </p>
                </CardContent>
              </Card>
            )}
          </CardHeader>

          <CardContent padding="md" className="space-y-6">
            {/* Basic Information */}
            <Card variant="elevated">
              <CardHeader>
                <h3 className="text-lg font-semibold text-neutral-900">Basic Information</h3>
              </CardHeader>
              <CardContent padding="md">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-semibold text-neutral-500 mb-1 block">Title</label>
                    <p className="mt-1 text-neutral-900 font-medium">{alert.title}</p>
                  </div>
                  <div>
                    <label className="text-sm font-semibold text-neutral-500 mb-1 block">Source</label>
                    <p className="mt-1 text-neutral-900 font-medium capitalize">{alert.source.replace('_', ' ')}</p>
                  </div>
                  <div>
                    <label className="text-sm font-semibold text-neutral-500 mb-1 block">Status</label>
                    <p className="mt-1">
                      <Badge variant="status" status={alert.status as any} size="sm">
                        {alert.status}
                      </Badge>
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-semibold text-neutral-500 mb-1 block">Severity</label>
                    <p className="mt-1">
                      <Badge variant="severity" severity={alert.severity as any} size="sm">
                        {alert.severity}
                      </Badge>
                    </p>
                  </div>
                  {alert.external_id && (
                    <div>
                      <label className="text-sm font-semibold text-neutral-500 mb-1 block">External ID</label>
                      <p className="mt-1 text-neutral-900 font-mono text-sm">{alert.external_id}</p>
                    </div>
                  )}
                  {alert.service && (
                    <div>
                      <label className="text-sm font-semibold text-neutral-500 mb-1 block">Service</label>
                      <p className="mt-1 text-neutral-900 font-medium">{alert.service}</p>
                    </div>
                  )}
                  {alert.environment && (
                    <div>
                      <label className="text-sm font-semibold text-neutral-500 mb-1 block">Environment</label>
                      <p className="mt-1 text-neutral-900 font-medium">{alert.environment}</p>
                    </div>
                  )}
                  {alert.matched_ticket_id && (
                    <div>
                      <label className="text-sm font-semibold text-neutral-500 mb-1 block">Matched Ticket</label>
                      <p className="mt-1 text-neutral-900 font-medium">Ticket #{alert.matched_ticket_id}</p>
                      {alert.matched_at && (
                        <p className="mt-1 text-sm text-neutral-500">
                          Matched: {new Date(alert.matched_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Description */}
            {alert.description && (
              <Card variant="elevated">
                <CardHeader>
                  <h3 className="text-lg font-semibold text-neutral-900">Description</h3>
                </CardHeader>
                <CardContent padding="md">
                  <p className="text-neutral-700 whitespace-pre-wrap">{alert.description}</p>
                </CardContent>
              </Card>
            )}

            {/* Timestamps */}
            <Card variant="elevated">
              <CardHeader>
                <h3 className="text-lg font-semibold text-neutral-900">Timestamps</h3>
              </CardHeader>
              <CardContent padding="md">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-semibold text-neutral-500 mb-1 block">Received At</label>
                    <p className="mt-1 text-neutral-900 font-medium">
                      {new Date(alert.received_at).toLocaleString()}
                    </p>
                  </div>
                  {alert.starts_at && (
                    <div>
                      <label className="text-sm font-semibold text-neutral-500 mb-1 block">Started At</label>
                      <p className="mt-1 text-neutral-900 font-medium">
                        {new Date(alert.starts_at).toLocaleString()}
                      </p>
                    </div>
                  )}
                  {alert.ends_at && (
                    <div>
                      <label className="text-sm font-semibold text-neutral-500 mb-1 block">Ended At</label>
                      <p className="mt-1 text-neutral-900 font-medium">
                        {new Date(alert.ends_at).toLocaleString()}
                      </p>
                    </div>
                  )}
                  {alert.resolved_at && (
                    <div>
                      <label className="text-sm font-semibold text-neutral-500 mb-1 block">Resolved At</label>
                      <p className="mt-1 text-neutral-900 font-medium">
                        {new Date(alert.resolved_at).toLocaleString()}
                      </p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Metadata */}
            {alert.meta_data && Object.keys(alert.meta_data).length > 0 && (
              <Card variant="elevated">
                <CardHeader>
                  <h3 className="text-lg font-semibold text-neutral-900">Metadata</h3>
                </CardHeader>
                <CardContent padding="md">
                  <pre className="bg-neutral-50 p-4 rounded-lg border-2 border-neutral-200 overflow-x-auto text-sm text-neutral-900">
                    {JSON.stringify(alert.meta_data, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            )}

            {/* Raw Payload */}
            {alert.raw_payload && (
              <Card variant="elevated">
                <CardHeader>
                  <h3 className="text-lg font-semibold text-neutral-900">Raw Payload</h3>
                </CardHeader>
                <CardContent padding="md">
                  <pre className="bg-neutral-50 p-4 rounded-lg border-2 border-neutral-200 overflow-x-auto text-xs max-h-96 text-neutral-900">
                    {JSON.stringify(alert.raw_payload, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

