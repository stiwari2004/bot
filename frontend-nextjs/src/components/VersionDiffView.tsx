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
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

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
      <Card variant="elevated">
        <CardContent padding="lg">
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            <span className="ml-3 text-neutral-600 font-medium">Loading diff...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card variant="elevated">
        <CardContent padding="md">
          <div className="flex items-center gap-2">
            <XCircleIcon className="h-5 w-5 text-error-600" />
            <p className="text-sm text-error-800">Error: {error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!diff) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <Card variant="elevated">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="text-center">
                <p className="text-sm text-neutral-600">From</p>
                <p className="font-semibold text-neutral-900">v{diff.version1.version_number}</p>
                <p className="text-xs text-neutral-500">{diff.version1.title}</p>
              </div>
              <ArrowRightIcon className="h-6 w-6 text-neutral-400" />
              <div className="text-center">
                <p className="text-sm text-neutral-600">To</p>
                <p className="font-semibold text-neutral-900">v{diff.version2.version_number}</p>
                <p className="text-xs text-neutral-500">{diff.version2.title}</p>
              </div>
            </div>
            {onClose && (
              <Button variant="ghost" size="sm" onClick={onClose}>
                Close
              </Button>
            )}
          </div>
        </CardHeader>
      </Card>

      {/* Summary */}
      <Card variant="elevated">
        <CardContent padding="md">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-xs text-neutral-600">Lines Added</p>
              <p className="text-lg font-semibold text-success-600">{diff.summary.lines_added}</p>
            </div>
            <div>
              <p className="text-xs text-neutral-600">Lines Removed</p>
              <p className="text-lg font-semibold text-error-600">{diff.summary.lines_removed}</p>
            </div>
            <div>
              <p className="text-xs text-neutral-600">Net Change</p>
              <p className={`text-lg font-semibold ${
                diff.summary.net_change > 0 ? 'text-success-600' : diff.summary.net_change < 0 ? 'text-error-600' : 'text-neutral-600'
              }`}>
                {diff.summary.net_change > 0 ? '+' : ''}{diff.summary.net_change}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Diff Content */}
      <div className="grid grid-cols-2 gap-4">
        {/* Removed Lines */}
        <Card variant="elevated" className="overflow-hidden">
          <CardHeader className="bg-error-50 border-error-200">
            <h4 className="text-sm font-semibold text-error-900">
              Removed ({diff.changes.removed_lines.length} lines)
            </h4>
          </CardHeader>
          <CardContent padding="md">
            <div className="max-h-96 overflow-y-auto">
              {diff.changes.removed_lines.length > 0 ? (
                <div className="space-y-1 font-mono text-sm">
                  {diff.changes.removed_lines.map((line, idx) => (
                    <div key={idx} className="text-error-800 bg-error-50 px-2 py-1 rounded">
                      - {line}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-neutral-500 text-center py-4">No lines removed</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Added Lines */}
        <Card variant="elevated" className="overflow-hidden">
          <CardHeader className="bg-success-50 border-success-200">
            <h4 className="text-sm font-semibold text-success-900">
              Added ({diff.changes.added_lines.length} lines)
            </h4>
          </CardHeader>
          <CardContent padding="md">
            <div className="max-h-96 overflow-y-auto">
              {diff.changes.added_lines.length > 0 ? (
                <div className="space-y-1 font-mono text-sm">
                  {diff.changes.added_lines.map((line, idx) => (
                    <div key={idx} className="text-success-800 bg-success-50 px-2 py-1 rounded">
                      + {line}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-neutral-500 text-center py-4">No lines added</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}








