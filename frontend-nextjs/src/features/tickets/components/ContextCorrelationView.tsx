'use client';

import { useState, useEffect } from 'react';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';

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
          throw new Error(`Failed to fetch context: ${response.status}`);
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
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <span className="text-sm text-gray-600">Loading context...</span>
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

  if (!context) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <p className="text-sm text-gray-600">No context data available</p>
      </div>
    );
  }

  const signals = context.signals || {};

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
      <h4 className="font-medium text-gray-900">Correlated Context</h4>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-gray-600">Alerts:</span>
          <span className="ml-2 font-medium">{context.alert_count || 0}</span>
        </div>
        <div>
          <span className="text-gray-600">Executions:</span>
          <span className="ml-2 font-medium">{context.execution_count || 0}</span>
        </div>
        {signals.has_active_alerts !== undefined && (
          <div>
            <span className="text-gray-600">Active Alerts:</span>
            <span className={`ml-2 font-medium ${signals.has_active_alerts ? 'text-red-600' : 'text-green-600'}`}>
              {signals.has_active_alerts ? 'Yes' : 'No'}
            </span>
          </div>
        )}
        {signals.recent_execution_success_rate !== null && (
          <div>
            <span className="text-gray-600">Success Rate:</span>
            <span className="ml-2 font-medium">
              {(signals.recent_execution_success_rate * 100).toFixed(0)}%
            </span>
          </div>
        )}
        {signals.affected_services && signals.affected_services.length > 0 && (
          <div className="col-span-2">
            <span className="text-gray-600">Affected Services:</span>
            <div className="mt-1 flex flex-wrap gap-1">
              {signals.affected_services.map((service: string, idx: number) => (
                <span key={idx} className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-800">
                  {service}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

