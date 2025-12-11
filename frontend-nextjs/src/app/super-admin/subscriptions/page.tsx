'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardHeader, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/Select';
import { Table, TableHeader, TableRow, TableHead, TableCell, TableBody } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { useSuperAdminAuth } from '@/contexts/SuperAdminAuthContext';
import { apiConfig } from '@/lib/api-config';
import {
  KeyIcon,
  ArrowLeftIcon,
  PlusIcon,
  PencilIcon,
  EyeIcon,
  XCircleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';

interface Subscription {
  id: number;
  tenant_id: number;
  tenant_name: string;
  max_seats: number;
  max_nodes: number;
  current_seats: number;
  current_nodes: number;
  seats_remaining: number;
  nodes_remaining: number;
  seats_exceeded: boolean;
  nodes_exceeded: boolean;
  subscription_name: string | null;
  monthly_price: number;
  seat_overage_rate: number;
  node_overage_rate: number;
  status: string;
  is_enforced: boolean;
  is_active: boolean;
  started_at: string;
  expires_at: string | null;
  auto_renew: boolean;
  notes: string | null;
}

interface Tenant {
  id: number;
  name: string;
}

export default function SubscriptionsPage() {
  const router = useRouter();
  const { token } = useSuperAdminAuth();
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSubscription, setSelectedSubscription] = useState<Subscription | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [formData, setFormData] = useState({
    tenant_id: 0,
    max_seats: 14,
    max_nodes: 1000,
    subscription_name: '',
    monthly_price: 0,
    seat_overage_rate: 499,
    node_overage_rate: 199,
    is_enforced: true,
    expires_at: '',
    auto_renew: true,
    notes: '',
  });

  useEffect(() => {
    fetchSubscriptions();
    fetchTenants();
  }, []);

  const fetchSubscriptions = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${apiConfig.baseURL || ''}/api/v1/subscriptions/subscriptions`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setSubscriptions(data);
      } else {
        setError('Failed to fetch subscriptions');
      }
    } catch (err) {
      setError('Error fetching subscriptions');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchTenants = async () => {
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.tenants(), {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setTenants(data);
      }
    } catch (err) {
      console.error('Failed to fetch tenants:', err);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const payload: any = {
        tenant_id: formData.tenant_id,
        max_seats: formData.max_seats,
        max_nodes: formData.max_nodes,
        monthly_price: formData.monthly_price,
        seat_overage_rate: formData.seat_overage_rate,
        node_overage_rate: formData.node_overage_rate,
        is_enforced: formData.is_enforced,
        auto_renew: formData.auto_renew,
      };
      
      if (formData.subscription_name) {
        payload.subscription_name = formData.subscription_name;
      }
      if (formData.expires_at) {
        payload.expires_at = new Date(formData.expires_at).toISOString();
      }
      if (formData.notes) {
        payload.notes = formData.notes;
      }
      
      const response = await fetch(`${apiConfig.baseURL || ''}/api/v1/subscriptions/subscriptions`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      
      if (response.ok) {
        await fetchSubscriptions();
        setShowCreateModal(false);
        setFormData({
          tenant_id: 0,
          max_seats: 14,
          max_nodes: 1000,
          subscription_name: '',
          monthly_price: 0,
          seat_overage_rate: 499,
          node_overage_rate: 199,
          is_enforced: true,
          expires_at: '',
          auto_renew: true,
          notes: '',
        });
      } else {
        const error = await response.json();
        setError(error.detail || 'Failed to create subscription');
      }
    } catch (err) {
      setError('Error creating subscription');
      console.error(err);
    }
  };

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSubscription) return;
    
    setError(null);
    try {
      const payload: any = {};
      if (formData.max_seats !== selectedSubscription.max_seats) payload.max_seats = formData.max_seats;
      if (formData.max_nodes !== selectedSubscription.max_nodes) payload.max_nodes = formData.max_nodes;
      if (formData.subscription_name !== selectedSubscription.subscription_name) payload.subscription_name = formData.subscription_name;
      if (formData.monthly_price !== selectedSubscription.monthly_price) payload.monthly_price = formData.monthly_price;
      if (formData.seat_overage_rate !== selectedSubscription.seat_overage_rate) payload.seat_overage_rate = formData.seat_overage_rate;
      if (formData.node_overage_rate !== selectedSubscription.node_overage_rate) payload.node_overage_rate = formData.node_overage_rate;
      if (formData.is_enforced !== selectedSubscription.is_enforced) payload.is_enforced = formData.is_enforced;
      if (formData.auto_renew !== selectedSubscription.auto_renew) payload.auto_renew = formData.auto_renew;
      if (formData.notes !== selectedSubscription.notes) payload.notes = formData.notes;
      
      const response = await fetch(`${apiConfig.baseURL || ''}/api/v1/subscriptions/subscriptions/${selectedSubscription.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      
      if (response.ok) {
        await fetchSubscriptions();
        setShowEditModal(false);
        setSelectedSubscription(null);
      } else {
        const error = await response.json();
        setError(error.detail || 'Failed to update subscription');
      }
    } catch (err) {
      setError('Error updating subscription');
      console.error(err);
    }
  };

  const openEditModal = (subscription: Subscription) => {
    setSelectedSubscription(subscription);
    setFormData({
      tenant_id: subscription.tenant_id,
      max_seats: subscription.max_seats,
      max_nodes: subscription.max_nodes,
      subscription_name: subscription.subscription_name || '',
      monthly_price: subscription.monthly_price,
      seat_overage_rate: subscription.seat_overage_rate,
      node_overage_rate: subscription.node_overage_rate,
      is_enforced: subscription.is_enforced,
      expires_at: subscription.expires_at ? new Date(subscription.expires_at).toISOString().split('T')[0] : '',
      auto_renew: subscription.auto_renew,
      notes: subscription.notes || '',
    });
    setShowEditModal(true);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const getUsageColor = (current: number, max: number) => {
    const percent = (current / max) * 100;
    if (percent >= 100) return 'error';
    if (percent >= 80) return 'warning';
    return 'success';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-neutral-50">
      {/* Header */}
      <header className="bg-white border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.push('/super-admin')}
                className="p-2 hover:bg-neutral-100 rounded-lg transition"
              >
                <ArrowLeftIcon className="h-5 w-5 text-neutral-600" />
              </button>
              <div className="flex items-center space-x-3">
                <div className="rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 p-2.5 shadow-lg">
                  <KeyIcon className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-neutral-900">Subscription Management</h1>
                  <p className="text-sm text-neutral-600">Manage tenant subscriptions and limits</p>
                </div>
              </div>
            </div>
            <Button
              variant="primary"
              leftIcon={<PlusIcon className="h-5 w-5" />}
              onClick={() => setShowCreateModal(true)}
            >
              Create Subscription
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 p-4 bg-error-50 border border-error-200 rounded-lg">
            <p className="text-error-800">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-neutral-600">Loading subscriptions...</p>
          </div>
        ) : (
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-neutral-900">Active Subscriptions</h2>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tenant</TableHead>
                    <TableHead>Subscription</TableHead>
                    <TableHead>Seats</TableHead>
                    <TableHead>Nodes</TableHead>
                    <TableHead>Price</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Enforced</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {subscriptions.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-8 text-neutral-500">
                        No subscriptions found. Create your first subscription to get started.
                      </TableCell>
                    </TableRow>
                  ) : (
                    subscriptions.map((sub) => (
                      <TableRow key={sub.id}>
                        <TableCell className="font-medium">{sub.tenant_name}</TableCell>
                        <TableCell>{sub.subscription_name || 'Standard Subscription'}</TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            <span className={sub.seats_exceeded ? 'text-error-600 font-semibold' : ''}>
                              {sub.current_seats}/{sub.max_seats}
                            </span>
                            {sub.seats_exceeded && (
                              <Badge variant="error">Exceeded</Badge>
                            )}
                            {!sub.seats_exceeded && sub.seats_remaining <= 2 && (
                              <Badge variant="warning">Low</Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            <span className={sub.nodes_exceeded ? 'text-error-600 font-semibold' : ''}>
                              {sub.current_nodes}/{sub.max_nodes}
                            </span>
                            {sub.nodes_exceeded && (
                              <Badge variant="error">Exceeded</Badge>
                            )}
                            {!sub.nodes_exceeded && sub.nodes_remaining <= 10 && (
                              <Badge variant="warning">Low</Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>{formatCurrency(sub.monthly_price)}/mo</TableCell>
                        <TableCell>
                          {sub.is_active ? (
                            <Badge variant="success">Active</Badge>
                          ) : (
                            <Badge variant="secondary">Inactive</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {sub.is_enforced ? (
                            <Badge variant="primary">Enforced</Badge>
                          ) : (
                            <Badge variant="secondary">Disabled</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => openEditModal(sub)}
                              className="p-2 hover:bg-neutral-100 rounded-lg transition"
                              title="Edit Subscription"
                            >
                              <PencilIcon className="h-4 w-4 text-primary-600" />
                            </button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* Create Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">Create Subscription</h2>
                  <button
                    onClick={() => setShowCreateModal(false)}
                    className="p-2 hover:bg-neutral-100 rounded-lg"
                  >
                    <XCircleIcon className="h-5 w-5" />
                  </button>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreate} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Tenant *
                    </label>
                    <Select
                      value={formData.tenant_id.toString()}
                      onValueChange={(value) => setFormData({ ...formData, tenant_id: parseInt(value) })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select tenant" />
                      </SelectTrigger>
                      <SelectContent>
                        {tenants.map((tenant) => (
                          <SelectItem key={tenant.id} value={tenant.id.toString()}>
                            {tenant.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Subscription Name (Optional)
                    </label>
                    <Input
                      value={formData.subscription_name}
                      onChange={(e) => setFormData({ ...formData, subscription_name: e.target.value })}
                      placeholder="e.g., MSP Starter Bundle"
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Max Seats (Users) *
                      </label>
                      <Input
                        type="number"
                        min="1"
                        value={formData.max_seats}
                        onChange={(e) => setFormData({ ...formData, max_seats: parseInt(e.target.value) || 0 })}
                        required
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Max Nodes (Infrastructure) *
                      </label>
                      <Input
                        type="number"
                        min="1"
                        value={formData.max_nodes}
                        onChange={(e) => setFormData({ ...formData, max_nodes: parseInt(e.target.value) || 0 })}
                        required
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Monthly Price (₹)
                    </label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.monthly_price}
                      onChange={(e) => setFormData({ ...formData, monthly_price: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Seat Overage Rate (₹/seat/month)
                      </label>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        value={formData.seat_overage_rate}
                        onChange={(e) => setFormData({ ...formData, seat_overage_rate: parseFloat(e.target.value) || 0 })}
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Node Overage Rate (₹/node/month)
                      </label>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        value={formData.node_overage_rate}
                        onChange={(e) => setFormData({ ...formData, node_overage_rate: parseFloat(e.target.value) || 0 })}
                      />
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">
                        Enforce Limits
                      </label>
                      <p className="text-xs text-neutral-500">Block actions when limits are exceeded</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={formData.is_enforced}
                      onChange={(e) => setFormData({ ...formData, is_enforced: e.target.checked })}
                      className="h-4 w-4"
                    />
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">
                        Auto Renew
                      </label>
                      <p className="text-xs text-neutral-500">Automatically renew subscription</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={formData.auto_renew}
                      onChange={(e) => setFormData({ ...formData, auto_renew: e.target.checked })}
                      className="h-4 w-4"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Expires At (Optional)
                    </label>
                    <Input
                      type="date"
                      value={formData.expires_at}
                      onChange={(e) => setFormData({ ...formData, expires_at: e.target.value })}
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Notes (Optional)
                    </label>
                    <Textarea
                      value={formData.notes}
                      onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                      rows={3}
                      placeholder="Admin notes about this subscription"
                    />
                  </div>
                  
                  <div className="flex justify-end space-x-4 pt-4 border-t">
                    <Button
                      variant="outline"
                      onClick={() => setShowCreateModal(false)}
                    >
                      Cancel
                    </Button>
                    <Button type="submit" variant="primary">
                      Create Subscription
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Edit Modal */}
        {showEditModal && selectedSubscription && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">Edit Subscription</h2>
                  <button
                    onClick={() => {
                      setShowEditModal(false);
                      setSelectedSubscription(null);
                    }}
                    className="p-2 hover:bg-neutral-100 rounded-lg"
                  >
                    <XCircleIcon className="h-5 w-5" />
                  </button>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleEdit} className="space-y-4">
                  <div className="p-4 bg-neutral-50 rounded-lg">
                    <p className="text-sm text-neutral-600 mb-2">Tenant: <span className="font-medium">{selectedSubscription.tenant_name}</span></p>
                    <p className="text-sm text-neutral-600">Current Usage: {selectedSubscription.current_seats} seats, {selectedSubscription.current_nodes} nodes</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Subscription Name
                    </label>
                    <Input
                      value={formData.subscription_name}
                      onChange={(e) => setFormData({ ...formData, subscription_name: e.target.value })}
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Max Seats *
                      </label>
                      <Input
                        type="number"
                        min="1"
                        value={formData.max_seats}
                        onChange={(e) => setFormData({ ...formData, max_seats: parseInt(e.target.value) || 0 })}
                        required
                      />
                      {formData.max_seats < selectedSubscription.current_seats && (
                        <p className="text-xs text-error-600 mt-1">Warning: Current usage ({selectedSubscription.current_seats}) exceeds new limit</p>
                      )}
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Max Nodes *
                      </label>
                      <Input
                        type="number"
                        min="1"
                        value={formData.max_nodes}
                        onChange={(e) => setFormData({ ...formData, max_nodes: parseInt(e.target.value) || 0 })}
                        required
                      />
                      {formData.max_nodes < selectedSubscription.current_nodes && (
                        <p className="text-xs text-error-600 mt-1">Warning: Current usage ({selectedSubscription.current_nodes}) exceeds new limit</p>
                      )}
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Monthly Price (₹)
                    </label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.monthly_price}
                      onChange={(e) => setFormData({ ...formData, monthly_price: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Seat Overage Rate (₹/seat/month)
                      </label>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        value={formData.seat_overage_rate}
                        onChange={(e) => setFormData({ ...formData, seat_overage_rate: parseFloat(e.target.value) || 0 })}
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Node Overage Rate (₹/node/month)
                      </label>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        value={formData.node_overage_rate}
                        onChange={(e) => setFormData({ ...formData, node_overage_rate: parseFloat(e.target.value) || 0 })}
                      />
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">
                        Enforce Limits
                      </label>
                    </div>
                    <input
                      type="checkbox"
                      checked={formData.is_enforced}
                      onChange={(e) => setFormData({ ...formData, is_enforced: e.target.checked })}
                      className="h-4 w-4"
                    />
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">
                        Auto Renew
                      </label>
                    </div>
                    <input
                      type="checkbox"
                      checked={formData.auto_renew}
                      onChange={(e) => setFormData({ ...formData, auto_renew: e.target.checked })}
                      className="h-4 w-4"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Notes
                    </label>
                    <Textarea
                      value={formData.notes}
                      onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                      rows={3}
                    />
                  </div>
                  
                  <div className="flex justify-end space-x-4 pt-4 border-t">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setShowEditModal(false);
                        setSelectedSubscription(null);
                      }}
                    >
                      Cancel
                    </Button>
                    <Button type="submit" variant="primary">
                      Update Subscription
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        )}
      </main>
    </div>
  );
}


