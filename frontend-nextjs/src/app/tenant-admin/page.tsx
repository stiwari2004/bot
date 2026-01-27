'use client';

import { useMspAdminAuth } from '@/contexts/MspAdminAuthContext';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  BuildingOfficeIcon, 
  UserGroupIcon,
  ChartBarIcon,
  ArrowRightOnRectangleIcon,
  KeyIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';

interface DashboardStats {
  msp_tenant: {
    id: number;
    name: string;
  };
  customers: {
    total: number;
    active: number;
  };
  users: {
    total: number;
    seats_used: number;
    seats_limit: number;
  };
  nodes: {
    total: number;
    nodes_used: number;
    nodes_limit: number;
  };
  subscriptions: {
    total: number;
    active: number;
  };
}

export default function MspAdminDashboard() {
  const router = useRouter();
  const { admin, logout, token } = useMspAdminAuth();
  const [overview, setOverview] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchOverview = async () => {
    if (!token) return;
    
    setLoading(true);
    try {
      const response = await fetch(apiConfig.endpoints.tenantAdmin.dashboard.overview(), {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setOverview(data);
      }
    } catch (error) {
      console.error('Failed to fetch overview:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchOverview();
    }
  }, [token]);

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
                  <h1 className="text-xl font-bold text-neutral-900">MSP Admin</h1>
                  <p className="text-sm text-neutral-600">{admin?.tenant?.name || 'MSP Tenant'}</p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-sm font-medium text-neutral-900">{admin?.email}</p>
                <p className="text-xs text-neutral-600">MSP Administrator</p>
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
        {/* Overview Stats */}
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-neutral-600">Loading MSP overview...</p>
          </div>
        ) : overview ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {/* Total Customers */}
            <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-primary-100 rounded-lg">
                  <BuildingOfficeIcon className="h-6 w-6 text-primary-600" />
                </div>
              </div>
              <h3 className="text-sm font-medium text-neutral-600 mb-1">Total Customers</h3>
              <p className="text-3xl font-bold text-neutral-900">{overview.customers?.total || 0}</p>
              <p className="text-xs text-neutral-500 mt-2">
                {overview.customers?.active || 0} active
              </p>
            </div>

            {/* Total Users */}
            <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-secondary-100 rounded-lg">
                  <UserGroupIcon className="h-6 w-6 text-secondary-600" />
                </div>
              </div>
              <h3 className="text-sm font-medium text-neutral-600 mb-1">Total Users</h3>
              <p className="text-3xl font-bold text-neutral-900">{overview.users?.total || 0}</p>
              <p className="text-xs text-neutral-500 mt-2">
                {overview.users?.seats_used || 0} / {overview.users?.seats_limit || 0} seats
              </p>
            </div>

            {/* Total Nodes */}
            <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-success-100 rounded-lg">
                  <KeyIcon className="h-6 w-6 text-success-600" />
                </div>
              </div>
              <h3 className="text-sm font-medium text-neutral-600 mb-1">Total Nodes</h3>
              <p className="text-3xl font-bold text-neutral-900">{overview.nodes?.total || 0}</p>
              <p className="text-xs text-neutral-500 mt-2">
                {overview.nodes?.nodes_used || 0} / {overview.nodes?.nodes_limit || 0} nodes
              </p>
            </div>

            {/* Active Subscriptions */}
            <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-warning-100 rounded-lg">
                  <ChartBarIcon className="h-6 w-6 text-warning-600" />
                </div>
              </div>
              <h3 className="text-sm font-medium text-neutral-600 mb-1">Subscriptions</h3>
              <p className="text-3xl font-bold text-neutral-900">{overview.subscriptions?.active || 0}</p>
              <p className="text-xs text-neutral-500 mt-2">
                {overview.subscriptions?.total || 0} total
              </p>
            </div>
          </div>
        ) : null}

        {/* Quick Actions */}
        <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={() => router.push('/tenant-admin/customers')}
              className="flex items-center space-x-3 p-4 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition text-left"
            >
              <BuildingOfficeIcon className="h-6 w-6 text-primary-600" />
              <div>
                <p className="font-medium text-neutral-900">Manage Customers</p>
                <p className="text-sm text-neutral-600">View, create, and edit client tenants</p>
              </div>
            </button>
            <button
              onClick={() => router.push('/tenant-admin/users')}
              className="flex items-center space-x-3 p-4 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition text-left"
            >
              <UserGroupIcon className="h-6 w-6 text-primary-600" />
              <div>
                <p className="font-medium text-neutral-900">User Management</p>
                <p className="text-sm text-neutral-600">Manage users across customers</p>
              </div>
            </button>
            <button
              onClick={() => router.push('/tenant-admin/subscriptions')}
              className="flex items-center space-x-3 p-4 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition text-left"
            >
              <KeyIcon className="h-6 w-6 text-primary-600" />
              <div>
                <p className="font-medium text-neutral-900">Subscription Management</p>
                <p className="text-sm text-neutral-600">Manage seat and node limits</p>
              </div>
            </button>
            <button
              onClick={fetchOverview}
              className="flex items-center space-x-3 p-4 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition text-left"
            >
              <ChartBarIcon className="h-6 w-6 text-primary-600" />
              <div>
                <p className="font-medium text-neutral-900">Refresh Overview</p>
                <p className="text-sm text-neutral-600">Reload MSP statistics</p>
              </div>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

