'use client';

import { useState, useEffect } from 'react';
import {
  ClockIcon,
  CheckCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface Version {
  id: number;
  version_number: string;
  title: string;
  change_summary: string | null;
  change_type: string | null;
  is_current: boolean;
  created_at: string | null;
  created_by: number | null;
  parent_version_id: number | null;
}

interface VersionHistoryViewProps {
  runbookId: number;
  onVersionSelect?: (versionId: number) => void;
}

export function VersionHistoryView({ runbookId, onVersionSelect }: VersionHistoryViewProps) {
  const { token } = useAuth();
  const [versions, setVersions] = useState<Version[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchVersions();
  }, [runbookId]);

  const fetchVersions = async () => {
    setLoading(true);
    setError(null);

    try {
      const url = apiConfig.endpoints.runbooks.versions(runbookId);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(url, { headers });
      if (!response.ok) {
        throw new Error('Failed to fetch version history');
      }

      const data = await response.json();
      setVersions(data);
    } catch (err) {
      console.error('Error fetching versions:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch version history');
    } finally {
      setLoading(false);
    }
  };

  const getChangeTypeColor = (changeType: string | null): string => {
    switch (changeType) {
      case 'major':
        return 'bg-error-100 text-error-800';
      case 'minor':
        return 'bg-warning-100 text-warning-800';
      case 'patch':
        return 'bg-primary-100 text-primary-800';
      default:
        return 'bg-neutral-100 text-neutral-800';
    }
  };

  if (loading) {
    return (
      <Card variant="elevated">
        <CardContent padding="lg">
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            <span className="ml-3 text-neutral-600 font-medium">Loading version history...</span>
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
            <p className="text-sm text-error-800">Error: {error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (versions.length === 0) {
    return (
      <Card variant="elevated">
        <CardContent padding="lg">
          <div className="text-center py-12">
            <div className="p-1.5 rounded-lg bg-neutral-100 mx-auto mb-4 w-fit">
              <ClockIcon className="h-12 w-12 text-neutral-400" />
            </div>
            <h3 className="text-lg font-semibold text-neutral-900 mb-2">No versions yet</h3>
            <p className="text-neutral-600 text-sm">
              Version history will appear here when runbook is updated.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card variant="elevated">
        <CardHeader>
          <div className="flex items-center mb-2">
            <div className="p-1.5 rounded-lg bg-secondary-100 mr-3">
              <ClockIcon className="h-6 w-6 text-secondary-600" />
            </div>
            <h3 className="text-xl font-semibold text-neutral-900">Version History</h3>
          </div>
        </CardHeader>
        <CardContent padding="md">
          <div className="space-y-3">
            {versions.map((version) => (
              <Card
                key={version.id}
                variant={version.is_current ? "default" : "default"}
                className={`cursor-pointer transition-colors ${
                  version.is_current
                    ? 'border-primary-300 bg-primary-50'
                    : 'hover:border-primary-300'
                }`}
                onClick={() => onVersionSelect && onVersionSelect(version.id)}
              >
                <CardContent padding="md">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-semibold text-neutral-900">v{version.version_number}</span>
                        {version.is_current && (
                          <span className="text-xs px-2 py-1 bg-success-100 text-success-800 rounded">
                            Current
                          </span>
                        )}
                        {version.change_type && (
                          <span className={`text-xs px-2 py-1 rounded ${getChangeTypeColor(version.change_type)}`}>
                            {version.change_type}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-neutral-900 font-semibold mb-1">{version.title}</p>
                      {version.change_summary && (
                        <p className="text-sm text-neutral-600 mb-2">{version.change_summary}</p>
                      )}
                      <div className="flex items-center gap-4 text-xs text-neutral-500">
                        {version.created_at && (
                          <span>
                            {new Date(version.created_at).toLocaleDateString()} at{' '}
                            {new Date(version.created_at).toLocaleTimeString()}
                          </span>
                        )}
                      </div>
                    </div>
                    {onVersionSelect && (
                      <Button variant="ghost" size="sm" className="ml-4">
                        <ArrowPathIcon className="h-5 w-5" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}








