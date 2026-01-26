'use client';

import {
  BuildingOfficeIcon,
  UserGroupIcon,
  ServerIcon,
  SparklesIcon,
  CurrencyDollarIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

interface DashboardOverview {
  summary: {
    total_tenants: number;
    active_tenants: number;
    inactive_tenants: number;
    trial_tenants: number;
    paid_tenants: number;
    total_users: number;
    active_users: number;
    total_nodes: number;
    tenant_growth_percent: number;
    user_growth_percent: number;
    node_growth_percent: number;
  };
  revenue: {
    total_revenue: number;
    fixed_revenue: number;
    node_overage_revenue: number;
    llm_overage_revenue: number;
    estimated_margin_percent?: number;
  };
  usage: {
    total_executions: number;
    total_tickets: number;
    total_llm_tokens: number;
    total_api_calls: number;
  };
  plan_distribution: Record<string, number>;
  alerts: Array<{
    type: string;
    severity: string;
    message: string;
    tenant_id?: number;
  }>;
}

interface DashboardAnalyticsProps {
  overview: DashboardOverview | null;
  loading: boolean;
}

export function DashboardAnalytics({ overview, loading }: DashboardAnalyticsProps) {
  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
        <p className="mt-4 text-neutral-600">Loading platform overview...</p>
      </div>
    );
  }

  if (!overview) {
    return null;
  }

  return (
    <>
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Total Tenants */}
        <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-primary-100 rounded-lg">
              <BuildingOfficeIcon className="h-6 w-6 text-primary-600" />
            </div>
            {overview.summary?.tenant_growth_percent !== undefined && overview.summary.tenant_growth_percent !== 0 && (
              <span className={`text-sm font-medium ${overview.summary.tenant_growth_percent > 0 ? 'text-success-600' : 'text-warning-600'}`}>
                {overview.summary.tenant_growth_percent > 0 ? '+' : ''}{overview.summary.tenant_growth_percent.toFixed(1)}%
              </span>
            )}
          </div>
          <h3 className="text-sm font-medium text-neutral-600 mb-1">Total Tenants</h3>
          <p className="text-3xl font-bold text-neutral-900">{overview.summary?.total_tenants || 0}</p>
          <p className="text-xs text-neutral-500 mt-2">
            {overview.summary?.active_tenants || 0} active, {overview.summary?.inactive_tenants || 0} inactive
          </p>
        </div>

        {/* Trial vs Paid */}
        <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-success-100 rounded-lg">
              <SparklesIcon className="h-6 w-6 text-success-600" />
            </div>
          </div>
          <h3 className="text-sm font-medium text-neutral-600 mb-1">Trial Tenants</h3>
          <p className="text-3xl font-bold text-neutral-900">{overview.summary?.trial_tenants || 0}</p>
          <p className="text-xs text-neutral-500 mt-2">
            {overview.summary?.paid_tenants || 0} paid tenants
          </p>
        </div>

        {/* Total Users */}
        <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-secondary-100 rounded-lg">
              <UserGroupIcon className="h-6 w-6 text-secondary-600" />
            </div>
            {overview.summary?.user_growth_percent !== undefined && overview.summary.user_growth_percent !== 0 && (
              <span className={`text-sm font-medium ${overview.summary.user_growth_percent > 0 ? 'text-success-600' : 'text-warning-600'}`}>
                {overview.summary.user_growth_percent > 0 ? '+' : ''}{overview.summary.user_growth_percent.toFixed(1)}%
              </span>
            )}
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
            {overview.summary?.node_growth_percent !== undefined && overview.summary.node_growth_percent !== 0 && (
              <span className={`text-sm font-medium ${overview.summary.node_growth_percent > 0 ? 'text-success-600' : 'text-warning-600'}`}>
                {overview.summary.node_growth_percent > 0 ? '+' : ''}{overview.summary.node_growth_percent.toFixed(1)}%
              </span>
            )}
          </div>
          <h3 className="text-sm font-medium text-neutral-600 mb-1">Total Nodes</h3>
          <p className="text-3xl font-bold text-neutral-900">{overview.summary?.total_nodes || 0}</p>
          <p className="text-xs text-neutral-500 mt-2">Managed infrastructure</p>
        </div>
      </div>

      {/* Revenue Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-neutral-900">Revenue Analytics</h2>
            <CurrencyDollarIcon className="h-6 w-6 text-success-600" />
          </div>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-neutral-600">Current Month Total</p>
              <p className="text-2xl font-bold text-neutral-900">
                ${(overview.revenue?.total_revenue || 0).toFixed(2)}
              </p>
              {overview.revenue?.estimated_margin_percent !== undefined && (
                <p className={`text-sm mt-1 ${overview.revenue.estimated_margin_percent > 0 ? 'text-success-600' : 'text-warning-600'}`}>
                  Margin: {overview.revenue.estimated_margin_percent.toFixed(1)}%
                </p>
              )}
            </div>
            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-neutral-200">
              <div>
                <p className="text-xs text-neutral-600">Fixed Revenue</p>
                <p className="text-lg font-semibold text-neutral-900">
                  ${(overview.revenue?.fixed_revenue || 0).toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-xs text-neutral-600">Node Overage</p>
                <p className="text-lg font-semibold text-neutral-900">
                  ${(overview.revenue?.node_overage_revenue || 0).toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-xs text-neutral-600">LLM Overage</p>
                <p className="text-lg font-semibold text-neutral-900">
                  ${(overview.revenue?.llm_overage_revenue || 0).toFixed(2)}
                </p>
              </div>
            </div>
          </div>
        </div>

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
      </div>

      {/* Alerts Section */}
      {overview.alerts && Array.isArray(overview.alerts) && overview.alerts.length > 0 && (
        <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-neutral-900">Critical Alerts</h2>
            <ExclamationTriangleIcon className="h-6 w-6 text-warning-600" />
          </div>
          <div className="space-y-2">
            {overview.alerts.map((alert, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-lg border ${
                  alert.severity === 'critical'
                    ? 'bg-red-50 border-red-200'
                    : alert.severity === 'warning'
                    ? 'bg-yellow-50 border-yellow-200'
                    : 'bg-blue-50 border-blue-200'
                }`}
              >
                <p className="font-medium text-neutral-900">{alert.message}</p>
                {alert.tenant_id && (
                  <p className="text-sm text-neutral-600 mt-1">Tenant ID: {alert.tenant_id}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Plan Distribution */}
      {overview.plan_distribution && Object.keys(overview.plan_distribution).length > 0 && (
        <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm mb-8">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">Plan Distribution</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(overview.plan_distribution).map(([plan, count]) => (
              <div key={plan} className="text-center p-4 bg-neutral-50 rounded-lg">
                <p className="text-2xl font-bold text-neutral-900">{count}</p>
                <p className="text-sm text-neutral-600 capitalize">{plan}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
