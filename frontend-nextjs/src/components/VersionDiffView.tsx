'use client';

import { useState, useEffect } from 'react';
import {
  ArrowLeftIcon,
  ArrowRightIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';

interface VersionDiff {
  version1: {
    id: number;
    version_number: string;
    title: string;
  };
  version2: {
    id: number;
    version_number: string;
    title: string;
  };
  changes: {
    added_lines: string[];
    removed_lines: string[];
    total_lines_v1: number;
    total_lines_v2: number;
  };
  summary: {
    lines_added: number;
    lines_removed: number;
    net_change: number;
  };
}

interface VersionDiffViewProps {
  runbookId: number;
  versionId1: number;
  versionId2: number;
  onClose?: () => void;
}

export function VersionDiffView({
  runbookId,
  versionId1,
  versionId2,
  onClose,
}: VersionDiffViewProps) {
  const { token } = useAuth();
  const [diff, setDiff] = useState<VersionDiff | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDiff();
  }, [runbookId, versionId1, versionId2]);

  const fetchDiff = async () => {
    setLoading(true);
    setError(null);

    try {
      const url = apiConfig.endpoints.runbooks.versionDiff(runbookId, versionId1, versionId2);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(url, { headers });
      if (!response.ok) {
        throw new Error('Failed to fetch version diff');
      }

      const data = await response.json();
      setDiff(data);
    } catch (err) {
      console.error('Error fetching diff:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch version diff');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <div className="text-gray-600 text-sm">Loading diff...</div>
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

  if (!diff) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="text-center">
            <p className="text-sm text-gray-600">From</p>
            <p className="font-medium text-gray-900">v{diff.version1.version_number}</p>
            <p className="text-xs text-gray-500">{diff.version1.title}</p>
          </div>
          <ArrowRightIcon className="h-6 w-6 text-gray-400" />
          <div className="text-center">
            <p className="text-sm text-gray-600">To</p>
            <p className="font-medium text-gray-900">v{diff.version2.version_number}</p>
            <p className="text-xs text-gray-500">{diff.version2.title}</p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Close
          </button>
        )}
      </div>

      {/* Summary */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-gray-600">Lines Added</p>
            <p className="text-lg font-semibold text-green-600">{diff.summary.lines_added}</p>
          </div>
          <div>
            <p className="text-xs text-gray-600">Lines Removed</p>
            <p className="text-lg font-semibold text-red-600">{diff.summary.lines_removed}</p>
          </div>
          <div>
            <p className="text-xs text-gray-600">Net Change</p>
            <p className={`text-lg font-semibold ${
              diff.summary.net_change > 0 ? 'text-green-600' : diff.summary.net_change < 0 ? 'text-red-600' : 'text-gray-600'
            }`}>
              {diff.summary.net_change > 0 ? '+' : ''}{diff.summary.net_change}
            </p>
          </div>
        </div>
      </div>

      {/* Diff Content */}
      <div className="grid grid-cols-2 gap-4">
        {/* Removed Lines */}
        <div className="border border-gray-200 rounded-lg">
          <div className="bg-red-50 border-b border-red-200 px-4 py-2">
            <h4 className="text-sm font-medium text-red-900">
              Removed ({diff.changes.removed_lines.length} lines)
            </h4>
          </div>
          <div className="p-4 max-h-96 overflow-y-auto">
            {diff.changes.removed_lines.length > 0 ? (
              <div className="space-y-1 font-mono text-sm">
                {diff.changes.removed_lines.map((line, idx) => (
                  <div key={idx} className="text-red-800 bg-red-50 px-2 py-1 rounded">
                    - {line}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 text-center py-4">No lines removed</p>
            )}
          </div>
        </div>

        {/* Added Lines */}
        <div className="border border-gray-200 rounded-lg">
          <div className="bg-green-50 border-b border-green-200 px-4 py-2">
            <h4 className="text-sm font-medium text-green-900">
              Added ({diff.changes.added_lines.length} lines)
            </h4>
          </div>
          <div className="p-4 max-h-96 overflow-y-auto">
            {diff.changes.added_lines.length > 0 ? (
              <div className="space-y-1 font-mono text-sm">
                {diff.changes.added_lines.map((line, idx) => (
                  <div key={idx} className="text-green-800 bg-green-50 px-2 py-1 rounded">
                    + {line}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 text-center py-4">No lines added</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

