'use client';

import { useState, useEffect } from 'react';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';

interface PatternMatch {
  pattern_id: number;
  pattern_type: string;
  runbook_id: number | null;
  issue_signature: string | null;
  match_score: number;
  success_rate: number | null;
  usage_count: number;
}

interface PatternMatchViewProps {
  ticketId: number;
}

export function PatternMatchView({ ticketId }: PatternMatchViewProps) {
  const [patterns, setPatterns] = useState<PatternMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { token, loading: authLoading } = useAuth();

  useEffect(() => {
    const fetchPatterns = async () => {
      // Wait for auth to finish loading
      if (authLoading) return;
      
      // Get token from localStorage as fallback
      const authToken = token || (typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null);
      
      if (!authToken) {
        setLoading(false);
        setError('Authentication required');
        return;
      }
      
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(apiConfig.endpoints.decision.patterns(ticketId), {
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json',
          },
        });
        if (!response.ok) {
          throw new Error(`Failed to fetch patterns: ${response.status}`);
        }
        const data = await response.json();
        setPatterns(data);
      } catch (err) {
        console.error('Error fetching patterns:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch patterns');
      } finally {
        setLoading(false);
      }
    };

    if (ticketId) {
      fetchPatterns();
    }
  }, [ticketId, token, authLoading]);

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <span className="text-sm text-gray-600">Loading patterns...</span>
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

  if (patterns.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <p className="text-sm text-gray-600">No matching patterns found</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
      <h4 className="font-medium text-gray-900">Matching Patterns ({patterns.length})</h4>
      <div className="space-y-2">
        {patterns.map((pattern) => (
          <div key={pattern.pattern_id} className="border border-gray-200 rounded-lg p-3">
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-800">
                    {pattern.pattern_type}
                  </span>
                  <span className="text-xs text-gray-600">
                    Match: {(pattern.match_score * 100).toFixed(0)}%
                  </span>
                </div>
                {pattern.issue_signature && (
                  <p className="text-xs text-gray-600 mt-1 line-clamp-2">{pattern.issue_signature}</p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-4 text-xs text-gray-600">
              {pattern.success_rate !== null && (
                <span>
                  Success: {pattern.success_rate.toFixed(1)}%
                </span>
              )}
              <span>Used: {pattern.usage_count} times</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

