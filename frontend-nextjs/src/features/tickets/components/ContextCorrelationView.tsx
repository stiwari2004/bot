'use client';

import { useState, useEffect } from 'react';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

interface ContextCorrelationViewProps {
  ticketId: number;
  timeWindowHours?: number;
}

export function ContextCorrelationView({ ticketId, timeWindowHours = 24 }: ContextCorrelationViewProps) {
  const [context, setContext] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { token, loading: authLoading } = useAuth();

  useEffect(() => {
    const fetchContext = async () => {
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
        const response = await fetch(apiConfig.endpoints.decision.context(ticketId, timeWindowHours), {
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
            throw new Error(`Failed to fetch context: ${response.status} ${errorText || ''}`);
          }
        }
        const data = await response.json();
        setContext(data);
      } catch (err) {
        console.error('Error fetching context:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch context');
      } finally {
        setLoading(false);
      }
    };

    if (ticketId) {
      fetchContext();
    }
  }, [ticketId, timeWindowHours, token, authLoading]);

  if (loading) {
    return (
      <Card variant="default">
        <CardContent padding="md">
          <div className="flex items-center gap-3">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
            <span className="text-sm text-neutral-600 font-medium">Loading context...</span>
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

  if (!context) {
    return (
      <Card variant="outlined" className="bg-neutral-50">
        <CardContent padding="md">
          <p className="text-sm text-neutral-600">No context data available</p>
        </CardContent>
      </Card>
    );
  }

  const signals = context.signals || {};

  return (
    <Card variant="elevated">
      <CardHeader>
        <h4 className="font-semibold text-neutral-900">Correlated Context</h4>
      </CardHeader>
      <CardContent padding="md">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-neutral-600 font-semibold">Alerts:</span>
            <span className="ml-2 font-bold text-neutral-900">{context.alert_count || 0}</span>
          </div>
          <div>
            <span className="text-neutral-600 font-semibold">Executions:</span>
            <span className="ml-2 font-bold text-neutral-900">{context.execution_count || 0}</span>
          </div>
          {signals.has_active_alerts !== undefined && (
            <div>
              <span className="text-neutral-600 font-semibold">Active Alerts:</span>
              <Badge
                variant={signals.has_active_alerts ? 'error' : 'success'}
                size="sm"
                className="ml-2"
              >
                {signals.has_active_alerts ? 'Yes' : 'No'}
              </Badge>
            </div>
          )}
          {signals.recent_execution_success_rate !== null && (
            <div>
              <span className="text-neutral-600 font-semibold">Success Rate:</span>
              <span className="ml-2 font-bold text-neutral-900">
                {(signals.recent_execution_success_rate * 100).toFixed(0)}%
              </span>
            </div>
          )}
          {signals.affected_services && signals.affected_services.length > 0 && (
            <div className="col-span-2">
              <span className="text-neutral-600 font-semibold mb-2 block">Affected Services:</span>
              <div className="mt-1 flex flex-wrap gap-2">
                {signals.affected_services.map((service: string, idx: number) => (
                  <Badge key={idx} variant="primary" size="sm">
                    {service}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

