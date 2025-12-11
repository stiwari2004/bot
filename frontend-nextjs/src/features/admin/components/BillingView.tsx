'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useState, useEffect } from 'react';
import { apiConfig } from '@/lib/api-config';
import { Card, CardContent } from '@/components/ui/Card';
import { CurrencyDollarIcon } from '@heroicons/react/24/outline';

interface BillingData {
  tenant_id: number;
  tenant_name: string;
  billing_config: {
    fixed_monthly_cost: number;
    per_node_enabled: boolean;
    per_node_cost: number;
    billing_cycle: string;
    is_active: boolean;
  } | null;
  subscription: {
    subscription_name: string | null;
    max_seats: number;
    max_nodes: number;
    monthly_price: number;
    status: string;
    expires_at: string | null;
  } | null;
  current_usage: {
    seats_used: number;
    seats_limit: number;
    nodes_used: number;
    nodes_limit: number;
  } | null;
}

export function BillingView() {
  const { token } = useAuth();
  const [billing, setBilling] = useState<BillingData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchBilling = async () => {
    if (!token) return;
    
    setLoading(true);
    try {
      const response = await fetch(apiConfig.endpoints.clientAdmin.billing(), {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setBilling(data);
      }
    } catch (error) {
      console.error('Failed to fetch billing:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchBilling();
    }
  }, [token]);

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-neutral-900 mb-6">Billing & Subscription</h2>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : billing ? (
        <div className="space-y-6">
          {/* Subscription Info */}
          {billing.subscription && (
            <Card>
              <CardContent padding="md">
                <div className="flex items-center space-x-3 mb-4">
                  <CurrencyDollarIcon className="h-6 w-6 text-green-500" />
                  <h3 className="text-xl font-bold text-neutral-900">Subscription</h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-neutral-600">Subscription Name</p>
                    <p className="text-lg font-semibold text-neutral-900">
                      {billing.subscription.subscription_name || 'Default Subscription'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600">Status</p>
                    <span className={`px-2 py-1 rounded text-sm font-medium ${
                      billing.subscription.status === 'active' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {billing.subscription.status}
                    </span>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600">Monthly Price</p>
                    <p className="text-lg font-semibold text-neutral-900">
                      ${billing.subscription.monthly_price.toFixed(2)}
                    </p>
                  </div>
                  {billing.subscription.expires_at && (
                    <div>
                      <p className="text-sm text-neutral-600">Expires At</p>
                      <p className="text-lg font-semibold text-neutral-900">
                        {new Date(billing.subscription.expires_at).toLocaleDateString()}
                      </p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Usage Stats */}
          {billing.current_usage && (
            <Card>
              <CardContent padding="md">
                <h3 className="text-xl font-bold text-neutral-900 mb-4">Current Usage</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <p className="text-sm text-neutral-600 mb-2">Seats</p>
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 bg-neutral-200 rounded-full h-4">
                        <div
                          className="bg-blue-500 h-4 rounded-full"
                          style={{
                            width: `${Math.min(100, (billing.current_usage.seats_used / billing.current_usage.seats_limit) * 100)}%`,
                          }}
                        />
                      </div>
                      <span className="text-sm font-semibold text-neutral-900">
                        {billing.current_usage.seats_used} / {billing.current_usage.seats_limit}
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600 mb-2">Nodes</p>
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 bg-neutral-200 rounded-full h-4">
                        <div
                          className="bg-green-500 h-4 rounded-full"
                          style={{
                            width: `${Math.min(100, (billing.current_usage.nodes_used / billing.current_usage.nodes_limit) * 100)}%`,
                          }}
                        />
                      </div>
                      <span className="text-sm font-semibold text-neutral-900">
                        {billing.current_usage.nodes_used} / {billing.current_usage.nodes_limit}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Billing Config */}
          {billing.billing_config && (
            <Card>
              <CardContent padding="md">
                <h3 className="text-xl font-bold text-neutral-900 mb-4">Billing Configuration</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-neutral-600">Fixed Monthly Cost</p>
                    <p className="text-lg font-semibold text-neutral-900">
                      ${billing.billing_config.fixed_monthly_cost.toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600">Billing Cycle</p>
                    <p className="text-lg font-semibold text-neutral-900 capitalize">
                      {billing.billing_config.billing_cycle}
                    </p>
                  </div>
                  {billing.billing_config.per_node_enabled && (
                    <div>
                      <p className="text-sm text-neutral-600">Per Node Cost</p>
                      <p className="text-lg font-semibold text-neutral-900">
                        ${billing.billing_config.per_node_cost.toFixed(2)} per node
                      </p>
                    </div>
                  )}
                  <div>
                    <p className="text-sm text-neutral-600">Status</p>
                    <span className={`px-2 py-1 rounded text-sm font-medium ${
                      billing.billing_config.is_active 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {billing.billing_config.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {!billing.subscription && !billing.billing_config && (
            <Card>
              <CardContent padding="md">
                <p className="text-neutral-600">No billing configuration found. Please contact your administrator.</p>
              </CardContent>
            </Card>
          )}
        </div>
      ) : (
        <Card>
          <CardContent padding="md">
            <p className="text-neutral-600">Failed to load billing information</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

