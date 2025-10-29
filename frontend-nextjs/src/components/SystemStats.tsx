'use client';

import { useState, useEffect } from 'react';
import { 
  DocumentTextIcon, 
  ChartBarIcon, 
  Cog6ToothIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';

interface SystemStatsProps {
  stats: any;
}

export function SystemStats({ stats }: SystemStatsProps) {
  const [healthStatus, setHealthStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const checkHealth = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/test/health-detailed');
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
        <h2 className="text-2xl font-bold text-gray-900 mb-2">System Statistics</h2>
        <p className="text-gray-600">Monitor your AI troubleshooting system performance and data</p>
      </div>

      {/* Health Status */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">System Health</h3>
          <button
            onClick={checkHealth}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Checking...' : 'Refresh'}
          </button>
        </div>
        
        {healthStatus ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="flex items-center">
                <CheckCircleIcon className="h-8 w-8 text-green-600" />
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-500">Status</p>
                  <p className="text-lg font-semibold text-green-600 capitalize">
                    {healthStatus.status}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="flex items-center">
                <Cog6ToothIcon className="h-8 w-8 text-blue-600" />
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-500">Database</p>
                  <p className="text-lg font-semibold text-green-600 capitalize">
                    {healthStatus.database}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="flex items-center">
                <DocumentTextIcon className="h-8 w-8 text-purple-600" />
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-500">Tables</p>
                  <p className="text-lg font-semibold text-green-600 capitalize">
                    {healthStatus.tables}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="flex items-center">
                <ChartBarIcon className="h-8 w-8 text-orange-600" />
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-500">Vector Extension</p>
                  <p className="text-lg font-semibold text-green-600 capitalize">
                    {healthStatus.vector_extension}
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex">
              <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
              <div className="ml-3">
                <p className="text-sm text-yellow-800">
                  Unable to fetch health status. Please check if the backend is running.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Knowledge Base Statistics */}
      {stats && (
        <div className="space-y-6">
          <h3 className="text-lg font-semibold text-gray-900">Knowledge Base Statistics</h3>
          
          {/* Overall Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="flex items-center">
                <DocumentTextIcon className="h-8 w-8 text-blue-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Documents</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {stats.total_documents}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="flex items-center">
                <ChartBarIcon className="h-8 w-8 text-green-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Chunks</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {stats.total_chunks}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="flex items-center">
                <Cog6ToothIcon className="h-8 w-8 text-purple-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Processing Status</p>
                  <p className="text-2xl font-semibold text-green-600">
                    Active
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Source Type Breakdown */}
          <div>
            <h4 className="text-md font-medium text-gray-900 mb-4">Documents by Source Type</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(sourceTypeStats).map(([sourceType, count]) => (
                <div key={sourceType} className="bg-white p-4 rounded-lg border border-gray-200">
                  <div className="text-center">
                    <p className="text-2xl font-semibold text-gray-900">{count as number}</p>
                    <p className="text-sm text-gray-500 capitalize">{sourceType}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-gray-50 p-6 rounded-lg">
            <h4 className="text-md font-medium text-gray-900 mb-4">Quick Actions</h4>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => window.open('http://localhost:8000/test', '_blank')}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
              >
                Open Test Interface
              </button>
              <button
                onClick={() => window.open('http://localhost:8000/docs', '_blank')}
                className="px-4 py-2 bg-gray-600 text-white text-sm font-medium rounded-lg hover:bg-gray-700"
              >
                View API Docs
              </button>
              <button
                onClick={() => window.open('http://localhost:8000/health', '_blank')}
                className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700"
              >
                Health Check
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
