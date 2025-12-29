'use client';

import { useSuperAdminAuth } from '@/contexts/SuperAdminAuthContext';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  ShieldCheckIcon, 
  BuildingOfficeIcon, 
  UserGroupIcon,
  ChartBarIcon,
  ArrowRightOnRectangleIcon,
  CurrencyDollarIcon,
  KeyIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';

export default function SuperAdminDashboard() {
  const router = useRouter();
  const { admin, logout } = useSuperAdminAuth();
  const [overview, setOverview] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchOverview = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('super_admin_token');
      const response = await fetch('/api/v1/super-admin/overview', {
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
    fetchOverview();
  }, []);

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
                  <h1 className="text-xl font-bold text-neutral-900">Super Admin</h1>
                  <p className="text-sm text-neutral-600">Platform Administration</p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-4">
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
        {/* Overview Stats */}
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-neutral-600">Loading platform overview...</p>
          </div>
        ) : overview ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {/* Total Tenants */}
            <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-primary-100 rounded-lg">
                  <BuildingOfficeIcon className="h-6 w-6 text-primary-600" />
                </div>
              </div>
              <h3 className="text-sm font-medium text-neutral-600 mb-1">Total Tenants</h3>
              <p className="text-3xl font-bold text-neutral-900">{overview.tenants?.total || 0}</p>
              <p className="text-xs text-neutral-500 mt-2">
                {overview.tenants?.active || 0} active
              </p>
            </div>

            {/* SaaS Tenants */}
            <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-success-100 rounded-lg">
                  <BuildingOfficeIcon className="h-6 w-6 text-success-600" />
                </div>
              </div>
              <h3 className="text-sm font-medium text-neutral-600 mb-1">SaaS Tenants</h3>
              <p className="text-3xl font-bold text-neutral-900">{overview.tenants?.saas || 0}</p>
              <p className="text-xs text-neutral-500 mt-2">Platform managed</p>
            </div>

            {/* PaaS Tenants */}
            <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-warning-100 rounded-lg">
                  <BuildingOfficeIcon className="h-6 w-6 text-warning-600" />
                </div>
              </div>
              <h3 className="text-sm font-medium text-neutral-600 mb-1">PaaS Tenants</h3>
              <p className="text-3xl font-bold text-neutral-900">{overview.tenants?.paas || 0}</p>
              <p className="text-xs text-neutral-500 mt-2">Self-hosted</p>
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
              <p className="text-xs text-neutral-500 mt-2">Across all tenants</p>
            </div>
          </div>
        ) : null}

        {/* Quick Actions */}
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
              onClick={fetchOverview}
              className="flex items-center space-x-3 p-4 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition text-left"
            >
              <ChartBarIcon className="h-6 w-6 text-primary-600" />
              <div>
                <p className="font-medium text-neutral-900">Refresh Overview</p>
                <p className="text-sm text-neutral-600">Reload platform statistics</p>
              </div>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}



