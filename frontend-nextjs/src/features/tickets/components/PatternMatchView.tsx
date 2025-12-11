'use client';

import { useState, useEffect } from 'react';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

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
          if (response.status === 401 || response.status === 403) {
            throw new Error('Authentication required. Please log in again.');
          } else if (response.status === 404) {
            throw new Error('Ticket not found or access denied.');
          } else {
            const errorText = await response.text().catch(() => '');
            throw new Error(`Failed to fetch patterns: ${response.status} ${errorText || ''}`);
          }
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
      <Card variant="default">
        <CardContent padding="md">
          <div className="flex items-center gap-3">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
            <span className="text-sm text-neutral-600 font-medium">Loading patterns...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card variant="outlined" className="border-error-200 bg-error-50">
        <CardContent padding="md">
          <p className="text-sm text-error-800 font-medium">Error: {error}</p>
        </CardContent>
      </Card>
    );
  }

  if (patterns.length === 0) {
    return (
      <Card variant="outlined" className="bg-neutral-50">
        <CardContent padding="md">
          <p className="text-sm text-neutral-600">No matching patterns found</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card variant="elevated">
      <CardHeader>
        <h4 className="font-semibold text-neutral-900">Matching Patterns ({patterns.length})</h4>
      </CardHeader>
      <CardContent padding="md">
        <div className="space-y-3">
          {patterns.map((pattern) => (
            <Card key={pattern.pattern_id} variant="default">
              <CardContent padding="sm">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <Badge variant="primary" size="sm">
                        {pattern.pattern_type}
                      </Badge>
                      <span className="text-xs text-neutral-600 font-medium">
                        Match: {(pattern.match_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    {pattern.issue_signature && (
                      <p className="text-xs text-neutral-600 mt-1 line-clamp-2">{pattern.issue_signature}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-4 text-xs text-neutral-600">
                  {pattern.success_rate !== null && (
                    <span className="font-medium">
                      Success: {pattern.success_rate.toFixed(1)}%
                    </span>
                  )}
                  <span className="font-medium">Used: {pattern.usage_count} times</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

