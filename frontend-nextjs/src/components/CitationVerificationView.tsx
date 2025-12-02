'use client';

import { useState, useEffect } from 'react';
import {
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';

interface CitationHealth {
  runbook_id: number;
  total_citations: number;
  verified: number;
  broken: number;
  pending: number;
  avg_quality_score: number | null;
  health_status: string;
  broken_citations?: Array<{
    citation_id: number;
    verification_status: string;
    overall_quality_score: number | null;
  }>;
}

interface CitationVerificationViewProps {
  runbookId: number;
}

export function CitationVerificationView({ runbookId }: CitationVerificationViewProps) {
  const { token } = useAuth();
  const [health, setHealth] = useState<CitationHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    fetchHealth();
  }, [runbookId]);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);

    try {
      const url = apiConfig.endpoints.runbooks.citationHealth(runbookId);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(url, { headers });
      if (!response.ok) {
        throw new Error('Failed to fetch citation health');
      }

      const data = await response.json();
      setHealth(data);
    } catch (err) {
      console.error('Error fetching citation health:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch citation health');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    setError(null);

    try {
      const url = apiConfig.endpoints.runbooks.verifyCitations(runbookId);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(url, {
        method: 'POST',
        headers,
      });

      if (!response.ok) {
        throw new Error('Failed to verify citations');
      }

      // Refresh health data
      await fetchHealth();
    } catch (err) {
      console.error('Error verifying citations:', err);
      setError(err instanceof Error ? err.message : 'Failed to verify citations');
    } finally {
      setVerifying(false);
    }
  };

  const getHealthStatusColor = (status: string): string => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-800';
      case 'unhealthy':
        return 'bg-red-100 text-red-800';
      case 'low_quality':
        return 'bg-yellow-100 text-yellow-800';
      case 'needs_verification':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[200px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <div className="text-gray-600 text-sm">Loading citation health...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-sm text-red-800">Error: {error}</p>
      </div>
    );
  }

  if (!health) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Citation Verification</h3>
        <button
          onClick={handleVerify}
          disabled={verifying}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          <ArrowPathIcon className={`h-4 w-4 ${verifying ? 'animate-spin' : ''}`} />
          {verifying ? 'Verifying...' : 'Verify Citations'}
        </button>
      </div>

      {/* Health Status */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm font-medium text-gray-900">Health Status</span>
          <span className={`text-sm px-3 py-1 rounded ${getHealthStatusColor(health.health_status)}`}>
            {health.health_status.replace('_', ' ').toUpperCase()}
          </span>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-4">
          <div>
            <p className="text-xs text-gray-600">Total</p>
            <p className="text-lg font-semibold text-gray-900">{health.total_citations}</p>
          </div>
          <div>
            <p className="text-xs text-gray-600">Verified</p>
            <p className="text-lg font-semibold text-green-600">{health.verified}</p>
          </div>
          <div>
            <p className="text-xs text-gray-600">Broken</p>
            <p className="text-lg font-semibold text-red-600">{health.broken}</p>
          </div>
          <div>
            <p className="text-xs text-gray-600">Pending</p>
            <p className="text-lg font-semibold text-yellow-600">{health.pending}</p>
          </div>
        </div>

        {/* Average Quality Score */}
        {health.avg_quality_score !== null && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">Average Quality Score</span>
              <span className="text-sm font-medium text-gray-900">
                {health.avg_quality_score.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${
                  health.avg_quality_score >= 80
                    ? 'bg-green-600'
                    : health.avg_quality_score >= 60
                    ? 'bg-yellow-600'
                    : 'bg-red-600'
                }`}
                style={{ width: `${health.avg_quality_score}%` }}
              ></div>
            </div>
          </div>
        )}
      </div>

      {/* Broken Citations */}
      {health.broken > 0 && health.broken_citations && health.broken_citations.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <XCircleIcon className="h-5 w-5 text-red-600" />
            <h4 className="text-sm font-medium text-red-900">Broken Citations</h4>
          </div>
          <div className="space-y-2">
            {health.broken_citations.map((citation) => (
              <div
                key={citation.citation_id}
                className="bg-white border border-red-200 rounded p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-900">Citation #{citation.citation_id}</span>
                  <span className="text-xs px-2 py-1 bg-red-100 text-red-800 rounded">
                    {citation.verification_status}
                  </span>
                </div>
                {citation.overall_quality_score !== null && (
                  <p className="text-xs text-gray-600 mt-1">
                    Quality: {citation.overall_quality_score.toFixed(1)}%
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {health.total_citations === 0 && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
          <CheckCircleIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No citations found</h3>
          <p className="text-gray-600 text-sm">
            This runbook doesn't have any citations to verify.
          </p>
        </div>
      )}
    </div>
  );
}

