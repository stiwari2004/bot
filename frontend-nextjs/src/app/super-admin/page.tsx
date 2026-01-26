'use client';

import { useSuperAdminAuth } from '@/contexts/SuperAdminAuthContext';
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { apiConfig } from '@/lib/api-config';
import { useDashboardWebSocket } from '@/hooks/useDashboardWebSocket';
import { useDashboardPreferences } from '@/hooks/useDashboardPreferences';
import { 
  ShieldCheckIcon, 
  BuildingOfficeIcon, 
  UserGroupIcon,
  ChartBarIcon,
  ArrowRightOnRectangleIcon,
  CurrencyDollarIcon,
  KeyIcon,
  SparklesIcon,
  ExclamationTriangleIcon,
  ServerIcon,
  BoltIcon,
  ArrowDownTrayIcon,
  WifiIcon,
  SignalSlashIcon,
  Cog6ToothIcon,
  DocumentTextIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  PlayIcon,
  CalendarIcon,
  ClockIcon,
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
    estimated_llm_costs?: number;
    estimated_total_costs?: number;
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
  timestamp: string;
}

export default function SuperAdminDashboard() {
  const router = useRouter();
  const { admin, logout, token, isAuthenticated } = useSuperAdminAuth();
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'analytics' | 'actions' | 'reports'>('analytics');
  const [exporting, setExporting] = useState<string | null>(null);
  const [showPreferences, setShowPreferences] = useState(false);
  
  // Reporting state
  const [scheduledReports, setScheduledReports] = useState<any[]>([]);
  const [showCreateReportModal, setShowCreateReportModal] = useState(false);
  const [editingReport, setEditingReport] = useState<any | null>(null);
  const [customReportFilters, setCustomReportFilters] = useState({
    reportType: 'overview',
    format: 'pdf',
    dateRange: { start: '', end: '' },
    tenantIds: [] as number[],
    plan: '',
    status: '',
  });
  
  const { preferences, savePreferences } = useDashboardPreferences(token);
  
  const { isConnected, lastUpdate, sendRefresh } = useDashboardWebSocket({
    token,
    enabled: preferences?.auto_refresh ?? true,
    onUpdate: (data) => {
      setOverview(data);
      setLoading(false);
    },
    onError: (err) => {
      // WebSocket errors are non-critical - dashboard still works with polling
      console.warn('WebSocket connection unavailable, using polling instead:', err.message);
    },
  });

  const fetchOverview = useCallback(async () => {
    if (!token) {
      setError('Not authenticated');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.dashboard.overview(), {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        if (response.status === 401) {
          logout();
          router.push('/super-admin/login');
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

  const handleExport = async (type: 'overview' | 'tenants' | 'revenue', format: 'csv' | 'pdf') => {
    if (!token) return;

    const exportKey = `${type}_${format}`;
    setExporting(exportKey);
    
    try {
      let url: string;
      switch (type) {
        case 'overview':
          url = apiConfig.endpoints.superAdmin.dashboard.exportOverview(format);
          break;
        case 'tenants':
          url = apiConfig.endpoints.superAdmin.dashboard.exportTenants(format);
          break;
        case 'revenue':
          url = apiConfig.endpoints.superAdmin.dashboard.exportRevenue(format);
          break;
        default:
          return;
      }

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
      link.download = `${type}_export_${new Date().toISOString().split('T')[0]}.${format}`;
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

  // Fetch scheduled reports
  const fetchScheduledReports = useCallback(async () => {
    if (!token) return;
    
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.reporting.scheduledReports(), {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setScheduledReports(data);
      }
    } catch (error) {
      console.error('Error fetching scheduled reports:', error);
    }
  }, [token]);

  // Generate custom report
  const handleGenerateCustomReport = async () => {
    if (!token) return;
    
    setExporting('custom');
    try {
      const filters: any = {};
      if (customReportFilters.dateRange.start) filters.date_range = customReportFilters.dateRange;
      if (customReportFilters.tenantIds.length > 0) filters.tenant_ids = customReportFilters.tenantIds;
      if (customReportFilters.plan) filters.plan = customReportFilters.plan;
      if (customReportFilters.status) filters.status = customReportFilters.status;
      
      const response = await fetch(apiConfig.endpoints.superAdmin.reporting.generateCustom(), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          report_type: customReportFilters.reportType,
          format: customReportFilters.format,
          filters: Object.keys(filters).length > 0 ? filters : undefined,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Report generation failed: ${response.status}`);
      }
      
      // For now, trigger the export endpoint
      await handleExport(customReportFilters.reportType as any, customReportFilters.format as 'csv' | 'pdf');
    } catch (error) {
      console.error('Custom report error:', error);
      setError(error instanceof Error ? error.message : 'Custom report generation failed');
    } finally {
      setExporting(null);
    }
  };

  // Polling fallback when WebSocket is not connected
  useEffect(() => {
    if (!isAuthenticated || !token || !preferences?.auto_refresh) {
      return;
    }

    // Only set up polling if WebSocket is not connected
    if (!isConnected) {
      const pollInterval = preferences.refresh_interval || 30000;
      const intervalId = setInterval(() => {
        fetchOverview();
      }, pollInterval);
      
      return () => clearInterval(intervalId);
    }
  }, [isAuthenticated, token, preferences?.auto_refresh, preferences?.refresh_interval, isConnected, fetchOverview]);

  // Fetch scheduled reports when reports tab is active
  useEffect(() => {
    if (activeTab === 'reports' && token) {
      fetchScheduledReports();
    }
  }, [activeTab, token, fetchScheduledReports]);

  // Initial fetch
  useEffect(() => {
    if (isAuthenticated && token) {
      fetchOverview();
    }
  }, [isAuthenticated, token, fetchOverview]);

  if (!isAuthenticated) {
    return null; // Layout will handle redirect
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
                  <ShieldCheckIcon className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-neutral-900">Super Admin Dashboard</h1>
                  <p className="text-sm text-neutral-600">Platform Administration & Analytics</p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {/* Connection Status - Only show if WebSocket is enabled */}
              {preferences?.auto_refresh && (
                <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-neutral-50" title={isConnected ? 'Real-time updates active' : 'Real-time updates unavailable, using polling'}>
                  {isConnected ? (
                    <>
                      <WifiIcon className="h-4 w-4 text-success-600" />
                      <span className="text-xs text-neutral-600">Live</span>
                    </>
                  ) : (
                    <>
                      <SignalSlashIcon className="h-4 w-4 text-neutral-400" />
                      <span className="text-xs text-neutral-500">Polling</span>
                    </>
                  )}
                </div>
              )}
              
              {/* Export Menu */}
              <div className="relative group">
                <button className="flex items-center space-x-2 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-100 rounded-lg transition">
                  <ArrowDownTrayIcon className="h-5 w-5" />
                  <span>Export</span>
                </button>
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-neutral-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
                  <div className="py-1">
                    <div className="px-3 py-2 text-xs font-semibold text-neutral-500 uppercase">Overview</div>
                    <button
                      onClick={() => handleExport('overview', 'csv')}
                      disabled={!!exporting}
                      className="w-full text-left px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
                    >
                      Export as CSV
                    </button>
                    <button
                      onClick={() => handleExport('overview', 'pdf')}
                      disabled={!!exporting}
                      className="w-full text-left px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
                    >
                      Export as PDF
                    </button>
                    <div className="px-3 py-2 text-xs font-semibold text-neutral-500 uppercase mt-2">Tenants</div>
                    <button
                      onClick={() => handleExport('tenants', 'csv')}
                      disabled={!!exporting}
                      className="w-full text-left px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
                    >
                      Export as CSV
                    </button>
                    <button
                      onClick={() => handleExport('tenants', 'pdf')}
                      disabled={!!exporting}
                      className="w-full text-left px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
                    >
                      Export as PDF
                    </button>
                    <div className="px-3 py-2 text-xs font-semibold text-neutral-500 uppercase mt-2">Revenue</div>
                    <button
                      onClick={() => handleExport('revenue', 'csv')}
                      disabled={!!exporting}
                      className="w-full text-left px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
                    >
                      Export as CSV
                    </button>
                    <button
                      onClick={() => handleExport('revenue', 'pdf')}
                      disabled={!!exporting}
                      className="w-full text-left px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
                    >
                      Export as PDF
                    </button>
                  </div>
                </div>
              </div>
              
              {/* Preferences Button */}
              <button
                onClick={() => setShowPreferences(!showPreferences)}
                className={`flex items-center space-x-2 px-4 py-2 text-sm rounded-lg transition ${
                  showPreferences 
                    ? 'bg-primary-100 text-primary-700' 
                    : 'text-neutral-700 hover:bg-neutral-100'
                }`}
                title="Dashboard Settings"
              >
                <Cog6ToothIcon className="h-5 w-5" />
                <span className="hidden sm:inline">Settings</span>
              </button>
              
              <div className="text-right">
                <p className="text-sm font-medium text-neutral-900">{admin?.email}</p>
                <p className="text-xs text-neutral-600">Super Administrator</p>
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
        {/* Preferences Panel */}
        {showPreferences && (
          <div className="mb-6 bg-white border border-neutral-200 rounded-lg p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-neutral-900">Dashboard Settings</h3>
              <button
                onClick={() => setShowPreferences(false)}
                className="text-neutral-500 hover:text-neutral-700 text-xl leading-none"
                aria-label="Close settings"
              >
                ×
              </button>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between py-2">
                <div className="flex-1">
                  <label className="text-sm font-medium text-neutral-700">Auto Refresh</label>
                  <p className="text-xs text-neutral-500 mt-1">Enable real-time updates via WebSocket</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={preferences?.auto_refresh ?? true}
                    onChange={(e) => savePreferences({ auto_refresh: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-neutral-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-neutral-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                </label>
              </div>
              <div className="flex items-center justify-between py-2">
                <div className="flex-1">
                  <label className="text-sm font-medium text-neutral-700">Refresh Interval</label>
                  <p className="text-xs text-neutral-500 mt-1">Time between updates (milliseconds)</p>
                </div>
                <input
                  type="number"
                  value={preferences?.refresh_interval ?? 30000}
                  onChange={(e) => savePreferences({ refresh_interval: parseInt(e.target.value) || 30000 })}
                  className="w-32 px-3 py-1.5 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  min="5000"
                  step="5000"
                />
              </div>
              {preferences?.widgets && (
                <div className="pt-4 border-t border-neutral-200">
                  <p className="text-sm font-medium text-neutral-700 mb-3">Widget Visibility</p>
                  <div className="space-y-2">
                    {Object.entries(preferences.widgets).map(([key, widget]: [string, any]) => (
                      <div key={key} className="flex items-center justify-between py-1">
                        <label className="text-sm text-neutral-600 capitalize">{key.replace(/_/g, ' ')}</label>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={widget.enabled}
                            onChange={(e) => {
                              const newWidgets = { ...preferences.widgets };
                              newWidgets[key] = { ...widget, enabled: e.target.checked };
                              savePreferences({ widgets: newWidgets });
                            }}
                            className="sr-only peer"
                          />
                          <div className="w-9 h-5 bg-neutral-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-neutral-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-600"></div>
                        </label>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
        
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

        {/* Tabs */}
        <div className="mb-6 border-b border-neutral-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('analytics')}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm transition-colors
                ${
                  activeTab === 'analytics'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300'
                }
              `}
            >
              <div className="flex items-center space-x-2">
                <ChartBarIcon className="h-5 w-5" />
                <span>Analytics</span>
              </div>
            </button>
            <button
              onClick={() => setActiveTab('actions')}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm transition-colors
                ${
                  activeTab === 'actions'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300'
                }
              `}
            >
              <div className="flex items-center space-x-2">
                <BoltIcon className="h-5 w-5" />
                <span>Actions</span>
              </div>
            </button>
            <button
              onClick={() => setActiveTab('reports')}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm transition-colors
                ${
                  activeTab === 'reports'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300'
                }
              `}
            >
              <div className="flex items-center space-x-2">
                <DocumentTextIcon className="h-5 w-5" />
                <span>Reports</span>
              </div>
            </button>
          </nav>
        </div>

        {/* Analytics Tab Content */}
        {activeTab === 'analytics' && (
          <>
            {/* Overview Stats */}
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-neutral-600">Loading platform overview...</p>
          </div>
        ) : overview ? (
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
        ) : null}
          </>
        )}

        {/* Actions Tab Content */}
        {activeTab === 'actions' && (
          <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={() => router.push('/super-admin/tenants')}
              className="flex items-center space-x-3 p-4 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition text-left"
            >
              <BuildingOfficeIcon className="h-6 w-6 text-primary-600" />
              <div>
                <p className="font-medium text-neutral-900">Manage Tenants</p>
                <p className="text-sm text-neutral-600">View, create, and edit tenants</p>
              </div>
            </button>
            <button
              onClick={() => router.push('/super-admin/users')}
              className="flex items-center space-x-3 p-4 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition text-left"
            >
              <UserGroupIcon className="h-6 w-6 text-primary-600" />
              <div>
                <p className="font-medium text-neutral-900">User Management</p>
                <p className="text-sm text-neutral-600">Manage users across tenants</p>
              </div>
            </button>
            <button
              onClick={() => router.push('/super-admin/billing')}
              className="flex items-center space-x-3 p-4 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition text-left"
            >
              <CurrencyDollarIcon className="h-6 w-6 text-primary-600" />
              <div>
                <p className="font-medium text-neutral-900">Billing Management</p>
                <p className="text-sm text-neutral-600">Configure tenant billing</p>
              </div>
            </button>
            <button
              onClick={() => router.push('/super-admin/subscriptions')}
              className="flex items-center space-x-3 p-4 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition text-left"
            >
              <KeyIcon className="h-6 w-6 text-primary-600" />
              <div>
                <p className="font-medium text-neutral-900">Subscription Management</p>
                <p className="text-sm text-neutral-600">Manage seat and node limits</p>
              </div>
            </button>
            <button
              onClick={() => router.push('/super-admin/license-plans')}
              className="flex items-center space-x-3 p-4 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition text-left"
            >
              <SparklesIcon className="h-6 w-6 text-primary-600" />
              <div>
                <p className="font-medium text-neutral-900">License Plans</p>
                <p className="text-sm text-neutral-600">Create and manage subscription plans</p>
              </div>
            </button>
            <button
              onClick={() => {
                sendRefresh();
                fetchOverview();
              }}
              className="flex items-center space-x-3 p-4 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition text-left"
            >
              <ChartBarIcon className="h-6 w-6 text-primary-600" />
              <div>
                <p className="font-medium text-neutral-900">Refresh Dashboard</p>
                <p className="text-sm text-neutral-600">Reload platform statistics</p>
              </div>
            </button>
          </div>
          </div>
        )}

        {/* Reports Tab Content */}
        {activeTab === 'reports' && (
          <div className="space-y-6">
            {/* Quick Export Section */}
            <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-neutral-900 mb-4">Quick Export</h2>
              <p className="text-sm text-neutral-600 mb-6">
                Generate standard reports instantly with default settings.
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="border border-neutral-200 rounded-lg p-4 hover:border-primary-300 transition">
                  <h3 className="font-medium text-neutral-900 mb-2">Platform Overview</h3>
                  <p className="text-sm text-neutral-600 mb-4">Complete platform statistics and metrics</p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleExport('overview', 'pdf')}
                      disabled={!!exporting}
                      className="flex-1 px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition"
                    >
                      PDF
                    </button>
                    <button
                      onClick={() => handleExport('overview', 'csv')}
                      disabled={!!exporting}
                      className="flex-1 px-3 py-2 text-sm bg-neutral-100 text-neutral-700 rounded-lg hover:bg-neutral-200 disabled:opacity-50 transition"
                    >
                      CSV
                    </button>
                  </div>
                </div>
                
                <div className="border border-neutral-200 rounded-lg p-4 hover:border-primary-300 transition">
                  <h3 className="font-medium text-neutral-900 mb-2">Tenant Report</h3>
                  <p className="text-sm text-neutral-600 mb-4">All tenants with usage and billing data</p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleExport('tenants', 'pdf')}
                      disabled={!!exporting}
                      className="flex-1 px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition"
                    >
                      PDF
                    </button>
                    <button
                      onClick={() => handleExport('tenants', 'csv')}
                      disabled={!!exporting}
                      className="flex-1 px-3 py-2 text-sm bg-neutral-100 text-neutral-700 rounded-lg hover:bg-neutral-200 disabled:opacity-50 transition"
                    >
                      CSV
                    </button>
                  </div>
                </div>
                
                <div className="border border-neutral-200 rounded-lg p-4 hover:border-primary-300 transition">
                  <h3 className="font-medium text-neutral-900 mb-2">Revenue Report</h3>
                  <p className="text-sm text-neutral-600 mb-4">Revenue analytics and trends</p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleExport('revenue', 'pdf')}
                      disabled={!!exporting}
                      className="flex-1 px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition"
                    >
                      PDF
                    </button>
                    <button
                      onClick={() => handleExport('revenue', 'csv')}
                      disabled={!!exporting}
                      className="flex-1 px-3 py-2 text-sm bg-neutral-100 text-neutral-700 rounded-lg hover:bg-neutral-200 disabled:opacity-50 transition"
                    >
                      CSV
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Custom Report Builder */}
            <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-neutral-900 mb-4">Custom Report Builder</h2>
              <p className="text-sm text-neutral-600 mb-6">
                Create custom reports with advanced filters and options.
              </p>
              
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">Report Type</label>
                    <select
                      value={customReportFilters.reportType}
                      onChange={(e) => setCustomReportFilters({ ...customReportFilters, reportType: e.target.value })}
                      className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="overview">Platform Overview</option>
                      <option value="tenants">Tenants</option>
                      <option value="revenue">Revenue</option>
                      <option value="usage">Usage Metrics</option>
                      <option value="custom">Custom (Multiple)</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">Format</label>
                    <select
                      value={customReportFilters.format}
                      onChange={(e) => setCustomReportFilters({ ...customReportFilters, format: e.target.value })}
                      className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="pdf">PDF</option>
                      <option value="csv">CSV</option>
                    </select>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">Start Date</label>
                    <input
                      type="date"
                      value={customReportFilters.dateRange.start}
                      onChange={(e) => setCustomReportFilters({
                        ...customReportFilters,
                        dateRange: { ...customReportFilters.dateRange, start: e.target.value }
                      })}
                      className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">End Date</label>
                    <input
                      type="date"
                      value={customReportFilters.dateRange.end}
                      onChange={(e) => setCustomReportFilters({
                        ...customReportFilters,
                        dateRange: { ...customReportFilters.dateRange, end: e.target.value }
                      })}
                      className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                </div>
                
                <div className="flex justify-end gap-2">
                  <button
                    onClick={handleGenerateCustomReport}
                    disabled={!!exporting}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition"
                  >
                    {exporting === 'custom' ? 'Generating...' : 'Generate Report'}
                  </button>
                </div>
              </div>
            </div>
            
            {/* Scheduled Reports */}
            <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-semibold text-neutral-900">Scheduled Reports</h2>
                  <p className="text-sm text-neutral-600 mt-1">
                    Automated reports sent via email on a schedule.
                  </p>
                </div>
                <button
                  onClick={() => {
                    setEditingReport(null);
                    setShowCreateReportModal(true);
                  }}
                  className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
                >
                  <PlusIcon className="h-5 w-5" />
                  <span>Create Schedule</span>
                </button>
              </div>
              
              {scheduledReports.length === 0 ? (
                <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-8 text-center">
                  <CalendarIcon className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
                  <p className="text-sm text-neutral-600 mb-2">No scheduled reports yet</p>
                  <p className="text-xs text-neutral-500">Create your first scheduled report to automate report generation and delivery.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {scheduledReports.map((report) => (
                    <div key={report.id} className="border border-neutral-200 rounded-lg p-4 hover:border-primary-300 transition">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-2">
                            <h3 className="font-medium text-neutral-900">{report.name}</h3>
                            <span className={`px-2 py-1 text-xs rounded-full ${
                              report.is_active 
                                ? 'bg-success-100 text-success-700' 
                                : 'bg-neutral-100 text-neutral-600'
                            }`}>
                              {report.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </div>
                          {report.description && (
                            <p className="text-sm text-neutral-600 mb-2">{report.description}</p>
                          )}
                          <div className="flex flex-wrap gap-4 text-xs text-neutral-500">
                            <span className="flex items-center space-x-1">
                              <DocumentTextIcon className="h-4 w-4" />
                              <span>{report.report_type}</span>
                            </span>
                            <span className="flex items-center space-x-1">
                              <ClockIcon className="h-4 w-4" />
                              <span>{report.frequency}</span>
                            </span>
                            {report.next_run_at && (
                              <span className="flex items-center space-x-1">
                                <CalendarIcon className="h-4 w-4" />
                                <span>Next: {new Date(report.next_run_at).toLocaleDateString()}</span>
                              </span>
                            )}
                            <span>{report.recipients.length} recipient{report.recipients.length !== 1 ? 's' : ''}</span>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => {
                              // Execute report manually
                              if (token) {
                                fetch(apiConfig.endpoints.superAdmin.reporting.executeScheduled(report.id), {
                                  method: 'POST',
                                  headers: { 'Authorization': `Bearer ${token}` },
                                }).then(() => fetchScheduledReports());
                              }
                            }}
                            className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg transition"
                            title="Execute Now"
                          >
                            <PlayIcon className="h-5 w-5" />
                          </button>
                          <button
                            onClick={() => {
                              setEditingReport(report);
                              setShowCreateReportModal(true);
                            }}
                            className="p-2 text-neutral-600 hover:bg-neutral-50 rounded-lg transition"
                            title="Edit"
                          >
                            <PencilIcon className="h-5 w-5" />
                          </button>
                          <button
                            onClick={() => {
                              if (confirm('Are you sure you want to delete this scheduled report?')) {
                                if (token) {
                                  fetch(apiConfig.endpoints.superAdmin.reporting.deleteScheduled(report.id), {
                                    method: 'DELETE',
                                    headers: { 'Authorization': `Bearer ${token}` },
                                  }).then(() => fetchScheduledReports());
                                }
                              }
                            }}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                            title="Delete"
                          >
                            <TrashIcon className="h-5 w-5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Create/Edit Scheduled Report Modal */}
            {showCreateReportModal && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                  <div className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-neutral-900">
                        {editingReport ? 'Edit Scheduled Report' : 'Create Scheduled Report'}
                      </h3>
                      <button
                        onClick={() => {
                          setShowCreateReportModal(false);
                          setEditingReport(null);
                        }}
                        className="text-neutral-500 hover:text-neutral-700"
                      >
                        ×
                      </button>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">Report Name</label>
                        <input
                          type="text"
                          defaultValue={editingReport?.name || ''}
                          className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                          placeholder="e.g., Weekly Revenue Report"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">Description</label>
                        <textarea
                          defaultValue={editingReport?.description || ''}
                          className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                          rows={2}
                          placeholder="Optional description"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 mb-2">Report Type</label>
                          <select
                            defaultValue={editingReport?.report_type || 'overview'}
                            className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                          >
                            <option value="overview">Overview</option>
                            <option value="tenants">Tenants</option>
                            <option value="revenue">Revenue</option>
                            <option value="usage">Usage</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 mb-2">Format</label>
                          <select
                            defaultValue={editingReport?.format || 'pdf'}
                            className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                          >
                            <option value="pdf">PDF</option>
                            <option value="csv">CSV</option>
                          </select>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 mb-2">Frequency</label>
                          <select
                            defaultValue={editingReport?.frequency || 'weekly'}
                            className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                          >
                            <option value="daily">Daily</option>
                            <option value="weekly">Weekly</option>
                            <option value="monthly">Monthly</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 mb-2">Time</label>
                          <input
                            type="time"
                            defaultValue={editingReport?.schedule_config?.time || '09:00'}
                            className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">Recipients (Email addresses, one per line)</label>
                        <textarea
                          defaultValue={editingReport?.recipients?.join('\n') || ''}
                          className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                          rows={3}
                          placeholder="admin@example.com&#10;manager@example.com"
                        />
                      </div>
                      <div className="flex justify-end gap-2 pt-4 border-t">
                        <button
                          onClick={() => {
                            setShowCreateReportModal(false);
                            setEditingReport(null);
                          }}
                          className="px-4 py-2 border border-neutral-300 rounded-lg hover:bg-neutral-50 transition"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={async () => {
                            // Get form values and create/update scheduled report
                            const form = document.querySelector('.bg-white.rounded-xl.max-w-2xl') as HTMLElement;
                            const name = (form.querySelector('input[type="text"]') as HTMLInputElement)?.value || '';
                            const description = (form.querySelector('textarea') as HTMLTextAreaElement)?.value || '';
                            const reportType = (form.querySelectorAll('select')[0] as HTMLSelectElement)?.value || 'overview';
                            const format = (form.querySelectorAll('select')[1] as HTMLSelectElement)?.value || 'pdf';
                            const frequency = (form.querySelectorAll('select')[2] as HTMLSelectElement)?.value || 'weekly';
                            const time = (form.querySelector('input[type="time"]') as HTMLInputElement)?.value || '09:00';
                            const recipientsText = (form.querySelectorAll('textarea')[1] as HTMLTextAreaElement)?.value || '';
                            const recipients = recipientsText.split('\n').filter(email => email.trim());
                            
                            if (!name || recipients.length === 0) {
                              alert('Please provide a name and at least one recipient email');
                              return;
                            }
                            
                            try {
                              const url = editingReport
                                ? apiConfig.endpoints.superAdmin.reporting.updateScheduled(editingReport.id)
                                : apiConfig.endpoints.superAdmin.reporting.createScheduled();
                              
                              const method = editingReport ? 'PUT' : 'POST';
                              
                              const response = await fetch(url, {
                                method,
                                headers: {
                                  'Authorization': `Bearer ${token}`,
                                  'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                  name,
                                  description: description || undefined,
                                  report_type: reportType,
                                  format,
                                  frequency,
                                  schedule_config: { time, timezone: 'UTC' },
                                  recipients,
                                }),
                              });
                              
                              if (response.ok) {
                                setShowCreateReportModal(false);
                                setEditingReport(null);
                                fetchScheduledReports();
                              } else {
                                const error = await response.json();
                                alert(`Failed to ${editingReport ? 'update' : 'create'} scheduled report: ${error.detail || 'Unknown error'}`);
                              }
                            } catch (error) {
                              console.error('Error saving scheduled report:', error);
                              alert('Failed to save scheduled report');
                            }
                          }}
                          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
                        >
                          {editingReport ? 'Update' : 'Create'} Schedule
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
