'use client';

import { useSuperAdminAuth } from '@/contexts/SuperAdminAuthContext';
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { apiConfig } from '@/lib/api-config';
import { superAdminFetch } from '@/lib/super-admin-fetch';
import { useDashboardWebSocket } from '@/hooks/useDashboardWebSocket';
import { useDashboardPreferences } from '@/hooks/useDashboardPreferences';
import { DashboardAnalytics } from '@/components/dashboard/DashboardAnalytics';
import { DashboardActions } from '@/components/dashboard/DashboardActions';
import { DashboardReports } from '@/components/dashboard/DashboardReports';
import { PreferencesPanel } from '@/components/dashboard/PreferencesPanel';
import { DashboardErrorBoundary } from '@/components/dashboard/DashboardErrorBoundary';
import { 
  ShieldCheckIcon, 
  ChartBarIcon,
  ArrowRightOnRectangleIcon,
  ArrowDownTrayIcon,
  WifiIcon,
  SignalSlashIcon,
  Cog6ToothIcon,
  DocumentTextIcon,
  BoltIcon,
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
  
  const { preferences, savePreferences } = useDashboardPreferences(token);
  
  const { isConnected, sendRefresh } = useDashboardWebSocket({
    token,
    enabled: preferences?.auto_refresh ?? true,
    onUpdate: (data) => {
      setOverview(data);
      setLoading(false);
    },
    onError: (err) => {
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
      // Use superAdminFetch for consistent error handling and 401 management
      const response = await superAdminFetch(
        apiConfig.endpoints.superAdmin.dashboard.overview(),
        token,
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      
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

  const handleExport = useCallback(async (type: 'overview' | 'tenants' | 'revenue', format: 'csv' | 'pdf') => {
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

      // Use superAdminFetch for consistent error handling
      const response = await superAdminFetch(url, token);

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
  }, [token]);

  // Polling fallback when WebSocket is not connected
  useEffect(() => {
    if (!isAuthenticated || !token || !preferences?.auto_refresh) {
      return;
    }

    if (!isConnected) {
      const pollInterval = preferences.refresh_interval || 30000;
      const intervalId = setInterval(() => {
        fetchOverview();
      }, pollInterval);
      
      return () => clearInterval(intervalId);
    }
  }, [isAuthenticated, token, preferences?.auto_refresh, preferences?.refresh_interval, isConnected, fetchOverview]);

  // Initial fetch
  useEffect(() => {
    if (isAuthenticated && token) {
      fetchOverview();
    }
  }, [isAuthenticated, token, fetchOverview]);

  if (!isAuthenticated) {
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
                  <ShieldCheckIcon className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-neutral-900">Super Admin Dashboard</h1>
                  <p className="text-sm text-neutral-600">Platform Administration & Analytics</p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {/* Connection Status */}
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
          <PreferencesPanel
            preferences={preferences}
            onSave={savePreferences}
            onClose={() => setShowPreferences(false)}
          />
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

        {/* Tab Content with Error Boundaries for Resilience */}
        {activeTab === 'analytics' && (
          <DashboardErrorBoundary>
            <DashboardAnalytics overview={overview} loading={loading} />
          </DashboardErrorBoundary>
        )}

        {activeTab === 'actions' && (
          <DashboardErrorBoundary>
            <DashboardActions onRefresh={() => {
              sendRefresh();
              fetchOverview();
            }} />
          </DashboardErrorBoundary>
        )}

        {activeTab === 'reports' && (
          <DashboardErrorBoundary>
            <DashboardReports token={token} onExport={handleExport} />
          </DashboardErrorBoundary>
        )}
      </main>
    </div>
  );
}
