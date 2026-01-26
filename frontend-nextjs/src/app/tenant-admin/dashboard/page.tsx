'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';
import { 
  BuildingOfficeIcon, 
  UserGroupIcon,
  ChartBarIcon,
  ArrowRightOnRectangleIcon,
  CurrencyDollarIcon,
  ServerIcon,
  ExclamationTriangleIcon,
  ArrowDownTrayIcon,
} from '@heroicons/react/24/outline';

interface TenantDashboardOverview {
  summary: {
    tenant_name: string;
    tenant_id: number;
    total_users: number;
    active_users: number;
    total_nodes: number;
    plan_name: string;
    plan_key: string | null;
    nodes_used: number;
    nodes_limit: number;
    seats_used: number;
    seats_limit: number;
    nodes_utilization_percent: number;
    seats_utilization_percent: number;
  };
  usage: {
    total_executions: number;
    total_tickets: number;
    total_llm_tokens: number;
    total_api_calls: number;
  };
  billing: {
    monthly_cost: number;
    node_overage_cost: number;
    llm_overage_cost: number;
    total_cost: number;
    estimated_llm_cost: number;
  };
  alerts: Array<{
    type: string;
    severity: string;
    title: string;
    message: string;
    action_required: boolean;
  }>;
  timestamp: string;
}

export default function TenantAdminDashboard() {
  const router = useRouter();
  const { user, logout, token } = useAuth();
  const [overview, setOverview] = useState<TenantDashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<string | null>(null);

  const fetchOverview = useCallback(async () => {
    if (!token) {
      setError('Not authenticated');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(apiConfig.endpoints.tenantAdmin.dashboard.overview(), {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        if (response.status === 401) {
          logout();
          router.push('/login');
          return;
        }
        const errorText = await response.text();
        setError(`Failed to load dashboard: ${response.status} ${errorText}`);
        return;
      }
      
      const data = await response.json();
      setOverview(data);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to fetch overview');
    } finally {
      setLoading(false);
    }
  }, [token, logout, router]);

  const handleExport = async (format: 'csv' | 'pdf') => {
    if (!token) return;

    setExporting(format);
    
    try {
      const url = apiConfig.endpoints.tenantAdmin.dashboard.exportOverview(format);
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Export failed: ${response.status}`);
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `tenant_dashboard_${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('Export error:', error);
      setError(error instanceof Error ? error.message : 'Export failed');
    } finally {
      setExporting(null);
    }
  };

  useEffect(() => {
    if (token) {
      fetchOverview();
    }
  }, [token, fetchOverview]);

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-neutral-50">
      {/* Header */}
      <header className="bg-white border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 p-2.5 shadow-lg">
                  <BuildingOfficeIcon className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-neutral-900">Tenant Dashboard</h1>
                  <p className="text-sm text-neutral-600">{overview?.summary.tenant_name || 'Loading...'}</p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {/* Export Menu */}
              <div className="relative group">
                <button className="flex items-center space-x-2 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-100 rounded-lg transition">
                  <ArrowDownTrayIcon className="h-5 w-5" />
                  <span>Export</span>
                </button>
                <div className="absolute right-0 mt-2 w-40 bg-white rounded-lg shadow-lg border border-neutral-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
                  <div className="py-1">
                    <button
                      onClick={() => handleExport('csv')}
                      disabled={!!exporting}
                      className="w-full text-left px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
                    >
                      Export as CSV
                    </button>
                    <button
                      onClick={() => handleExport('pdf')}
                      disabled={!!exporting}
                      className="w-full text-left px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
                    >
                      Export as PDF
                    </button>
                  </div>
                </div>
              </div>
              
              <div className="text-right">
                <p className="text-sm font-medium text-neutral-900">{user.email}</p>
                <p className="text-xs text-neutral-600">Tenant Administrator</p>
              </div>
              <button
                onClick={logout}
                className="flex items-center space-x-2 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-100 rounded-lg transition"
              >
                <ArrowRightOnRectangleIcon className="h-5 w-5" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
            <button
              onClick={fetchOverview}
              className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
            >
              Retry
            </button>
          </div>
        )}

        {/* Export Status */}
        {exporting && (
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-blue-800">Exporting as {exporting.toUpperCase()}...</p>
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-neutral-600">Loading dashboard...</p>
          </div>
        ) : overview ? (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {/* Total Users */}
              <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <div className="p-3 bg-primary-100 rounded-lg">
                    <UserGroupIcon className="h-6 w-6 text-primary-600" />
                  </div>
                </div>
                <h3 className="text-sm font-medium text-neutral-600 mb-1">Total Users</h3>
                <p className="text-3xl font-bold text-neutral-900">{overview.summary?.total_users || 0}</p>
                <p className="text-xs text-neutral-500 mt-2">
                  {overview.summary?.active_users || 0} active users
                </p>
              </div>

              {/* Total Nodes */}
              <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <div className="p-3 bg-warning-100 rounded-lg">
                    <ServerIcon className="h-6 w-6 text-warning-600" />
                  </div>
                  <span className="text-sm font-medium text-neutral-600">
                    {overview.summary?.nodes_utilization_percent || 0}%
                  </span>
                </div>
                <h3 className="text-sm font-medium text-neutral-600 mb-1">Nodes</h3>
                <p className="text-3xl font-bold text-neutral-900">
                  {overview.summary?.nodes_used || 0} / {overview.summary?.nodes_limit || 0}
                </p>
                <p className="text-xs text-neutral-500 mt-2">Infrastructure nodes</p>
              </div>

              {/* Seats */}
              <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <div className="p-3 bg-success-100 rounded-lg">
                    <UserGroupIcon className="h-6 w-6 text-success-600" />
                  </div>
                  <span className="text-sm font-medium text-neutral-600">
                    {overview.summary?.seats_utilization_percent || 0}%
                  </span>
                </div>
                <h3 className="text-sm font-medium text-neutral-600 mb-1">Seats</h3>
                <p className="text-3xl font-bold text-neutral-900">
                  {overview.summary?.seats_used || 0} / {overview.summary?.seats_limit || 0}
                </p>
                <p className="text-xs text-neutral-500 mt-2">User seats</p>
              </div>

              {/* Plan */}
              <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <div className="p-3 bg-secondary-100 rounded-lg">
                    <ChartBarIcon className="h-6 w-6 text-secondary-600" />
                  </div>
                </div>
                <h3 className="text-sm font-medium text-neutral-600 mb-1">Current Plan</h3>
                <p className="text-2xl font-bold text-neutral-900">{overview.summary?.plan_name || 'N/A'}</p>
                <p className="text-xs text-neutral-500 mt-2">Subscription plan</p>
              </div>
            </div>

            {/* Usage and Billing Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              {/* Usage Metrics */}
              <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-neutral-900">Usage Metrics</h2>
                  <ChartBarIcon className="h-6 w-6 text-primary-600" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-neutral-600">Executions</p>
                    <p className="text-2xl font-bold text-neutral-900">{(overview.usage?.total_executions || 0).toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600">Tickets</p>
                    <p className="text-2xl font-bold text-neutral-900">{(overview.usage?.total_tickets || 0).toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600">LLM Tokens</p>
                    <p className="text-2xl font-bold text-neutral-900">{(overview.usage?.total_llm_tokens || 0).toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600">API Calls</p>
                    <p className="text-2xl font-bold text-neutral-900">{(overview.usage?.total_api_calls || 0).toLocaleString()}</p>
                  </div>
                </div>
              </div>

              {/* Billing */}
              <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-neutral-900">Billing</h2>
                  <CurrencyDollarIcon className="h-6 w-6 text-success-600" />
                </div>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-neutral-600">Current Month Total</p>
                    <p className="text-2xl font-bold text-neutral-900">
                      ${(overview.billing?.total_cost || 0).toFixed(2)}
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-4 pt-4 border-t border-neutral-200">
                    <div>
                      <p className="text-xs text-neutral-600">Monthly Cost</p>
                      <p className="text-lg font-semibold text-neutral-900">
                        ${(overview.billing?.monthly_cost || 0).toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-neutral-600">Overage Cost</p>
                      <p className="text-lg font-semibold text-neutral-900">
                        ${((overview.billing?.node_overage_cost || 0) + (overview.billing?.llm_overage_cost || 0)).toFixed(2)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Alerts Section */}
            {overview.alerts && Array.isArray(overview.alerts) && overview.alerts.length > 0 && (
              <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm mb-8">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-neutral-900">Alerts</h2>
                  <ExclamationTriangleIcon className="h-6 w-6 text-warning-600" />
                </div>
                <div className="space-y-2">
                  {overview.alerts.map((alert, idx) => (
                    <div
                      key={idx}
                      className={`p-4 rounded-lg border ${
                        alert.severity === 'critical' || alert.severity === 'high'
                          ? 'bg-red-50 border-red-200'
                          : alert.severity === 'warning' || alert.severity === 'medium'
                          ? 'bg-yellow-50 border-yellow-200'
                          : 'bg-blue-50 border-blue-200'
                      }`}
                    >
                      <p className="font-medium text-neutral-900">{alert.title}</p>
                      <p className="text-sm text-neutral-600 mt-1">{alert.message}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : null}
      </main>
    </div>
  );
}
