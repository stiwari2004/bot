'use client';

import { useState, useEffect } from 'react';
import { 
  CheckCircleIcon, 
  ExclamationTriangleIcon, 
  XCircleIcon,
  ServerIcon
} from '@heroicons/react/24/outline';
import { superAdminFetch } from '@/lib/super-admin-fetch';
import { apiConfig } from '@/lib/api-config';

interface ConnectorHealth {
  total_connections: number;
  healthy: number;
  degraded: number;
  failed: number;
  health_percentage: number;
  connections: Array<{
    id: number;
    name: string;
    type: string;
    status: 'healthy' | 'degraded' | 'failed';
    last_success?: string;
    error_rate_1h: number;
    error_rate_24h: number;
  }>;
  timestamp: string;
}

interface ConnectorHealthWidgetProps {
  token: string | null;
}

export function ConnectorHealthWidget({ token }: ConnectorHealthWidgetProps) {
  const [health, setHealth] = useState<ConnectorHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;

    const fetchHealth = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await superAdminFetch(
          apiConfig.endpoints.superAdmin.connectorHealth(),
          token
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch connector health: ${response.status}`);
        }

        const data = await response.json();
        setHealth(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load connector health');
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
    // Refresh every 5 minutes
    const interval = setInterval(fetchHealth, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [token]);

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
        <div className="animate-pulse">
          <div className="h-4 bg-neutral-200 rounded w-1/3 mb-4"></div>
          <div className="h-8 bg-neutral-200 rounded w-1/4"></div>
        </div>
      </div>
    );
  }

  if (error || !health) {
    return (
      <div className="bg-white rounded-xl border border-red-200 p-6 shadow-sm">
        <p className="text-sm text-red-600">Failed to load connector health</p>
      </div>
    );
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon className="h-5 w-5 text-success-600" />;
      case 'degraded':
        return <ExclamationTriangleIcon className="h-5 w-5 text-warning-600" />;
      case 'failed':
        return <XCircleIcon className="h-5 w-5 text-red-600" />;
      default:
        return <ServerIcon className="h-5 w-5 text-neutral-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-success-600 bg-success-50';
      case 'degraded':
        return 'text-warning-600 bg-warning-50';
      case 'failed':
        return 'text-red-600 bg-red-50';
      default:
        return 'text-neutral-600 bg-neutral-50';
    }
  };

  return (
    <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-neutral-900">Connector Health</h2>
        <div className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(
          health.health_percentage >= 80 ? 'healthy' : 
          health.health_percentage >= 50 ? 'degraded' : 'failed'
        )}`}>
          {health.health_percentage.toFixed(1)}% Healthy
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center">
          <p className="text-2xl font-bold text-success-600">{health.healthy}</p>
          <p className="text-xs text-neutral-600">Healthy</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-warning-600">{health.degraded}</p>
          <p className="text-xs text-neutral-600">Degraded</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-red-600">{health.failed}</p>
          <p className="text-xs text-neutral-600">Failed</p>
        </div>
      </div>

      {health.connections.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-neutral-700 mb-2">Connections</h3>
          {health.connections.slice(0, 5).map((conn) => (
            <div key={conn.id} className="flex items-center justify-between p-2 bg-neutral-50 rounded">
              <div className="flex items-center gap-2">
                {getStatusIcon(conn.status)}
                <div>
                  <p className="text-sm font-medium text-neutral-900">{conn.name}</p>
                  <p className="text-xs text-neutral-500">{conn.type}</p>
                </div>
              </div>
              {conn.error_rate_1h > 0 && (
                <span className="text-xs text-warning-600">
                  {conn.error_rate_1h.toFixed(1)}% errors
                </span>
              )}
            </div>
          ))}
          {health.connections.length > 5 && (
            <p className="text-xs text-neutral-500 text-center mt-2">
              +{health.connections.length - 5} more connections
            </p>
          )}
        </div>
      )}
    </div>
  );
}
