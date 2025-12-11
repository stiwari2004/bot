'use client';

import { useState, useEffect } from 'react';
import { 
  DocumentTextIcon, 
  ChartBarIcon, 
  Cog6ToothIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface SystemStatsProps {
  stats: any;
}

export function SystemStats({ stats }: SystemStatsProps) {
  const [healthStatus, setHealthStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const checkHealth = async () => {
    setLoading(true);
    try {
      const response = await fetch(apiConfig.endpoints.system.healthDetailed());
      const data = await response.json();
      setHealthStatus(data);
    } catch (error) {
      console.error('Health check failed:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  const sourceTypeStats = stats?.by_source_type || {};

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-neutral-900 mb-2">System Statistics</h2>
        <p className="text-neutral-600">Monitor your AI troubleshooting system performance and data</p>
      </div>

      {/* Health Status */}
      <Card variant="elevated" className="mb-8">
        <CardHeader>
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-neutral-900">System Health</h3>
            <Button
              variant="secondary"
              size="sm"
              onClick={checkHealth}
              disabled={loading}
              isLoading={loading}
            >
              {loading ? 'Checking...' : 'Refresh'}
            </Button>
          </div>
        </CardHeader>
        <CardContent padding="md">
          {healthStatus ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card variant="default">
                <CardContent padding="md">
                  <div className="flex items-center">
                    <div className="p-2 rounded-lg bg-success-100">
                      <CheckCircleIcon className="h-6 w-6 text-success-600" />
                    </div>
                    <div className="ml-3">
                      <p className="text-sm font-semibold text-neutral-500">Status</p>
                      <p className="text-lg font-bold text-success-600 capitalize">
                        {healthStatus.status}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              
              <Card variant="default">
                <CardContent padding="md">
                  <div className="flex items-center">
                    <div className="p-2 rounded-lg bg-primary-100">
                      <Cog6ToothIcon className="h-6 w-6 text-primary-600" />
                    </div>
                    <div className="ml-3">
                      <p className="text-sm font-semibold text-neutral-500">Database</p>
                      <p className="text-lg font-bold text-success-600 capitalize">
                        {healthStatus.database}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              
              <Card variant="default">
                <CardContent padding="md">
                  <div className="flex items-center">
                    <div className="p-2 rounded-lg bg-warning-100">
                      <DocumentTextIcon className="h-6 w-6 text-warning-600" />
                    </div>
                    <div className="ml-3">
                      <p className="text-sm font-semibold text-neutral-500">Tables</p>
                      <p className="text-lg font-bold text-success-600 capitalize">
                        {healthStatus.tables}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              
              <Card variant="default">
                <CardContent padding="md">
                  <div className="flex items-center">
                    <div className="p-2 rounded-lg bg-error-100">
                      <ChartBarIcon className="h-6 w-6 text-error-600" />
                    </div>
                    <div className="ml-3">
                      <p className="text-sm font-semibold text-neutral-500">Vector Extension</p>
                      <p className="text-lg font-bold text-success-600 capitalize">
                        {healthStatus.vector_extension}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card variant="outlined" className="border-warning-200 bg-warning-50">
              <CardContent padding="sm">
                <div className="flex items-center gap-2">
                  <ExclamationTriangleIcon className="h-5 w-5 text-warning-600" />
                  <p className="text-sm text-warning-800 font-medium">
                    Unable to fetch health status. Please check if the backend is running.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </CardContent>
      </Card>

      {/* Knowledge Base Statistics */}
      {stats && (
        <div className="space-y-6">
          <Card variant="elevated">
            <CardHeader>
              <h3 className="text-lg font-semibold text-neutral-900">Knowledge Base Statistics</h3>
            </CardHeader>
            <CardContent padding="md">
              {/* Overall Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <Card variant="default">
                  <CardContent padding="md">
                    <div className="flex items-center">
                      <div className="p-2 rounded-lg bg-primary-100">
                        <DocumentTextIcon className="h-6 w-6 text-primary-600" />
                      </div>
                      <div className="ml-4">
                        <p className="text-sm font-semibold text-neutral-500">Total Documents</p>
                        <p className="text-2xl font-bold text-neutral-900">
                          {stats.total_documents}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card variant="default">
                  <CardContent padding="md">
                    <div className="flex items-center">
                      <div className="p-2 rounded-lg bg-success-100">
                        <ChartBarIcon className="h-6 w-6 text-success-600" />
                      </div>
                      <div className="ml-4">
                        <p className="text-sm font-semibold text-neutral-500">Total Chunks</p>
                        <p className="text-2xl font-bold text-neutral-900">
                          {stats.total_chunks}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card variant="default">
                  <CardContent padding="md">
                    <div className="flex items-center">
                      <div className="p-2 rounded-lg bg-warning-100">
                        <Cog6ToothIcon className="h-6 w-6 text-warning-600" />
                      </div>
                      <div className="ml-4">
                        <p className="text-sm font-semibold text-neutral-500">Processing Status</p>
                        <Badge variant="status" status="completed" size="sm" className="mt-1">
                          Active
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Source Type Breakdown */}
              <div>
                <h4 className="text-md font-semibold text-neutral-900 mb-4">Documents by Source Type</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(sourceTypeStats).map(([sourceType, count]) => (
                    <Card key={sourceType} variant="default">
                      <CardContent padding="md" className="text-center">
                        <p className="text-2xl font-bold text-neutral-900">{count as number}</p>
                        <p className="text-sm text-neutral-600 capitalize mt-1">{sourceType}</p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card variant="elevated">
            <CardHeader>
              <h4 className="text-md font-semibold text-neutral-900">Quick Actions</h4>
            </CardHeader>
            <CardContent padding="md">
              <div className="flex flex-wrap gap-3">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => window.open(apiConfig.endpoints.system.testUi(), '_blank')}
                >
                  Open Test Interface
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => window.open(apiConfig.endpoints.system.docs(), '_blank')}
                >
                  View API Docs
                </Button>
                <Button
                  variant="success"
                  size="sm"
                  onClick={() => window.open(apiConfig.endpoints.system.health(), '_blank')}
                >
                  Health Check
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
