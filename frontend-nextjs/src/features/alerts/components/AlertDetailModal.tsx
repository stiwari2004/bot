'use client';

import { useState } from 'react';
import { XMarkIcon, BellIcon, CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline';
import type { AlertDetail } from '../types';

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
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
        <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-2 text-gray-600">Loading alert details...</span>
          </div>
        </div>
      </div>
    );
  }

  if (!alert) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <BellIcon className="h-6 w-6 text-orange-600" />
              <h2 className="text-xl font-bold text-gray-900">Alert Details</h2>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
          
          {/* Action Buttons */}
          {/* Allow actions when alert is not yet resolved (firing or acknowledged) */}
          {alert.status !== 'resolved' && onUpdate && (
            <div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleUpdateStatus('resolved')}
                  disabled={updating}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <CheckCircleIcon className="h-5 w-5" />
                  {updating ? 'Resolving...' : 'Resolve Alert'}
                </button>
                {alert.status === 'firing' && (
                  <button
                    onClick={() => handleUpdateStatus('acknowledged')}
                    disabled={updating}
                    className="flex items-center gap-2 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <ExclamationCircleIcon className="h-5 w-5" />
                    {updating ? 'Acknowledging...' : 'Acknowledge'}
                  </button>
                )}
                <button
                  onClick={() => setShowNotesInput(!showNotesInput)}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                >
                  {showNotesInput ? 'Hide Notes' : 'Add Notes'}
                </button>
              </div>
              
              {/* Error Message */}
              {error && (
                <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                  {error}
                </div>
              )}
              
              {/* Notes Input */}
              {showNotesInput && (
                <div className="mt-3">
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Add notes about this update..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    rows={3}
                  />
                </div>
              )}
            </div>
          )}
          
          {/* Status Info for Resolved/Acknowledged */}
          {alert.status !== 'firing' && (
            <div className={`p-3 rounded-lg ${
              alert.status === 'resolved' ? 'bg-green-50 border border-green-200' :
              'bg-yellow-50 border border-yellow-200'
            }`}>
              <p className={`text-sm font-medium ${
                alert.status === 'resolved' ? 'text-green-800' : 'text-yellow-800'
              }`}>
                This alert has been {alert.status}.
                {alert.resolved_at && (
                  <span className="ml-2 text-gray-600">
                    Resolved at: {new Date(alert.resolved_at).toLocaleString()}
                  </span>
                )}
              </p>
            </div>
          )}
        </div>

        <div className="p-6 space-y-6">
          {/* Basic Information */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-500">Title</label>
                <p className="mt-1 text-gray-900">{alert.title}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Source</label>
                <p className="mt-1 text-gray-900 capitalize">{alert.source.replace('_', ' ')}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Status</label>
                <p className="mt-1">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    alert.status === 'firing' ? 'bg-red-100 text-red-800' :
                    alert.status === 'resolved' ? 'bg-green-100 text-green-800' :
                    'bg-yellow-100 text-yellow-800'
                  }`}>
                    {alert.status}
                  </span>
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Severity</label>
                <p className="mt-1">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    alert.severity === 'critical' ? 'bg-red-100 text-red-800' :
                    alert.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                    alert.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-blue-100 text-blue-800'
                  }`}>
                    {alert.severity}
                  </span>
                </p>
              </div>
              {alert.external_id && (
                <div>
                  <label className="text-sm font-medium text-gray-500">External ID</label>
                  <p className="mt-1 text-gray-900 font-mono text-sm">{alert.external_id}</p>
                </div>
              )}
              {alert.service && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Service</label>
                  <p className="mt-1 text-gray-900">{alert.service}</p>
                </div>
              )}
              {alert.environment && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Environment</label>
                  <p className="mt-1 text-gray-900">{alert.environment}</p>
                </div>
              )}
              {alert.matched_ticket_id && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Matched Ticket</label>
                  <p className="mt-1 text-gray-900">Ticket #{alert.matched_ticket_id}</p>
                  {alert.matched_at && (
                    <p className="mt-1 text-sm text-gray-500">
                      Matched: {new Date(alert.matched_at).toLocaleString()}
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Description */}
          {alert.description && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Description</h3>
              <p className="text-gray-700 whitespace-pre-wrap">{alert.description}</p>
            </div>
          )}

          {/* Timestamps */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Timestamps</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-500">Received At</label>
                <p className="mt-1 text-gray-900">
                  {new Date(alert.received_at).toLocaleString()}
                </p>
              </div>
              {alert.starts_at && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Started At</label>
                  <p className="mt-1 text-gray-900">
                    {new Date(alert.starts_at).toLocaleString()}
                  </p>
                </div>
              )}
              {alert.ends_at && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Ended At</label>
                  <p className="mt-1 text-gray-900">
                    {new Date(alert.ends_at).toLocaleString()}
                  </p>
                </div>
              )}
              {alert.resolved_at && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Resolved At</label>
                  <p className="mt-1 text-gray-900">
                    {new Date(alert.resolved_at).toLocaleString()}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Metadata */}
          {alert.meta_data && Object.keys(alert.meta_data).length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Metadata</h3>
              <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-sm">
                {JSON.stringify(alert.meta_data, null, 2)}
              </pre>
            </div>
          )}

          {/* Raw Payload */}
          {alert.raw_payload && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Raw Payload</h3>
              <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-xs max-h-96">
                {JSON.stringify(alert.raw_payload, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

