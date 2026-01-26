'use client';

import { useRouter } from 'next/navigation';
import {
  BuildingOfficeIcon,
  UserGroupIcon,
  CurrencyDollarIcon,
  KeyIcon,
  SparklesIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';

interface DashboardActionsProps {
  onRefresh: () => void;
}

export function DashboardActions({ onRefresh }: DashboardActionsProps) {
  const router = useRouter();

  return (
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
          onClick={onRefresh}
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
  );
}
