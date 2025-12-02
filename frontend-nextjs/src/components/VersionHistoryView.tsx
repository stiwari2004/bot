'use client';

import { useState, useEffect } from 'react';
import {
  ClockIcon,
  CheckCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';

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
        return 'bg-red-100 text-red-800';
      case 'minor':
        return 'bg-yellow-100 text-yellow-800';
      case 'patch':
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
          <div className="text-gray-600 text-sm">Loading version history...</div>
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

  if (versions.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
        <ClockIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">No versions yet</h3>
        <p className="text-gray-600 text-sm">
          Version history will appear here when runbook is updated.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Version History</h3>
      <div className="space-y-2">
        {versions.map((version) => (
          <div
            key={version.id}
            className={`border rounded-lg p-4 cursor-pointer transition-colors ${
              version.is_current
                ? 'border-blue-300 bg-blue-50'
                : 'border-gray-200 bg-white hover:bg-gray-50'
            }`}
            onClick={() => onVersionSelect && onVersionSelect(version.id)}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-medium text-gray-900">v{version.version_number}</span>
                  {version.is_current && (
                    <span className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded">
                      Current
                    </span>
                  )}
                  {version.change_type && (
                    <span className={`text-xs px-2 py-1 rounded ${getChangeTypeColor(version.change_type)}`}>
                      {version.change_type}
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-900 font-medium mb-1">{version.title}</p>
                {version.change_summary && (
                  <p className="text-sm text-gray-600 mb-2">{version.change_summary}</p>
                )}
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  {version.created_at && (
                    <span>
                      {new Date(version.created_at).toLocaleDateString()} at{' '}
                      {new Date(version.created_at).toLocaleTimeString()}
                    </span>
                  )}
                </div>
              </div>
              {onVersionSelect && (
                <button className="ml-4 text-blue-600 hover:text-blue-700">
                  <ArrowPathIcon className="h-5 w-5" />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

