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
import { useMspAdminAuth } from '@/contexts/MspAdminAuthContext';
import { apiConfig } from '@/lib/api-config';
import {
  KeyIcon,
  ArrowLeftIcon,
  PlusIcon,
  PencilIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

interface Customer {
  id: number;
  name: string;
}

interface Subscription {
  id: number;
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
  status: string;
  is_enforced: boolean;
  is_active: boolean;
  has_subscription: boolean;
}

export default function SubscriptionsPage() {
  const router = useRouter();
  const { token } = useMspAdminAuth();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [subscriptions, setSubscriptions] = useState<Map<number, Subscription>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCustomer, setSelectedCustomer] = useState<number | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [formData, setFormData] = useState({
    max_seats: 5,
    max_nodes: 20,
    subscription_name: '',
    monthly_price: 0,
    seat_overage_rate: 0,
    node_overage_rate: 0,
    is_enforced: true,
    auto_renew: true,
    notes: '',
  });

  const fetchCustomers = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(apiConfig.endpoints.tenantAdmin.customers(), {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch customers');
      }
      const data = await response.json();
      setCustomers(data);
      
      // Fetch subscriptions for all customers
      const subsMap = new Map<number, Subscription>();
      for (const customer of data) {
        try {
          const subResponse = await fetch(apiConfig.endpoints.tenantAdmin.customerSubscription(customer.id), {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });
          if (subResponse.ok) {
            const subData = await subResponse.json();
            if (subData.has_subscription !== false) {
              subsMap.set(customer.id, subData);
            }
          }
        } catch (err) {
          console.error(`Failed to fetch subscription for customer ${customer.id}:`, err);
        }
      }
      setSubscriptions(subsMap);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch customers');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchCustomers();
    }
  }, [token]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCustomer || !token) return;
    setError(null);
    try {
      const response = await fetch(apiConfig.endpoints.tenantAdmin.customerSubscription(selectedCustomer), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to create subscription' }));
        throw new Error(errorData.detail || 'Failed to create subscription');
      }

      setShowCreateModal(false);
      setSelectedCustomer(null);
      fetchCustomers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create subscription');
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCustomer || !token) return;
    setError(null);
    try {
      const response = await fetch(apiConfig.endpoints.tenantAdmin.customerSubscription(selectedCustomer), {
        method: 'POST', // Backend uses POST for create/update
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to update subscription' }));
        throw new Error(errorData.detail || 'Failed to update subscription');
      }

      setShowEditModal(false);
      setSelectedCustomer(null);
      fetchCustomers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update subscription');
    }
  };

  const startCreate = (customerId: number) => {
    setSelectedCustomer(customerId);
    setFormData({
      max_seats: 5,
      max_nodes: 20,
      subscription_name: '',
      monthly_price: 0,
      seat_overage_rate: 0,
      node_overage_rate: 0,
      is_enforced: true,
      auto_renew: true,
      notes: '',
    });
    setShowCreateModal(true);
  };

  const startEdit = (customerId: number) => {
    const subscription = subscriptions.get(customerId);
    if (!subscription) return;
    
    setSelectedCustomer(customerId);
    setFormData({
      max_seats: subscription.max_seats,
      max_nodes: subscription.max_nodes,
      subscription_name: subscription.subscription_name || '',
      monthly_price: subscription.monthly_price,
      seat_overage_rate: 0, // Backend might not return this
      node_overage_rate: 0, // Backend might not return this
      is_enforced: subscription.is_enforced,
      auto_renew: true,
      notes: '',
    });
    setShowEditModal(true);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-neutral-50">
      {/* Header */}
      <header className="bg-white border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.push('/tenant-admin')}
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
                  <p className="text-sm text-neutral-600">Manage subscriptions for your customers</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <Card variant="outlined" className="border-error-200 bg-error-50 mb-6">
            <CardContent padding="md">
              <p className="text-error-800">{error}</p>
            </CardContent>
          </Card>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-neutral-600">Loading subscriptions...</p>
          </div>
        ) : (
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-neutral-900">Customer Subscriptions</h2>
            </CardHeader>
            <CardContent>
              {customers.length === 0 ? (
                <div className="text-center py-12">
                  <KeyIcon className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
                  <p className="text-neutral-600 mb-4">No customers yet</p>
                  <Button variant="primary" onClick={() => router.push('/tenant-admin/customers')}>
                    Create Your First Customer
                  </Button>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Customer</TableHead>
                      <TableHead>Subscription</TableHead>
                      <TableHead>Seats</TableHead>
                      <TableHead>Nodes</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {customers.map((customer) => {
                      const subscription = subscriptions.get(customer.id);
                      return (
                        <TableRow key={customer.id}>
                          <TableCell className="font-medium">{customer.name}</TableCell>
                          <TableCell>
                            {subscription ? (
                              <span>{subscription.subscription_name || 'Default'}</span>
                            ) : (
                              <Badge variant="secondary">No Subscription</Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            {subscription ? (
                              <div>
                                <span className={subscription.seats_exceeded ? 'text-error-600 font-semibold' : ''}>
                                  {subscription.current_seats} / {subscription.max_seats}
                                </span>
                                {subscription.seats_exceeded && (
                                  <span className="ml-2 text-xs text-error-600">(Exceeded)</span>
                                )}
                              </div>
                            ) : (
                              '-'
                            )}
                          </TableCell>
                          <TableCell>
                            {subscription ? (
                              <div>
                                <span className={subscription.nodes_exceeded ? 'text-error-600 font-semibold' : ''}>
                                  {subscription.current_nodes} / {subscription.max_nodes}
                                </span>
                                {subscription.nodes_exceeded && (
                                  <span className="ml-2 text-xs text-error-600">(Exceeded)</span>
                                )}
                              </div>
                            ) : (
                              '-'
                            )}
                          </TableCell>
                          <TableCell>
                            {subscription ? (
                              <div className="flex items-center space-x-2">
                                {subscription.is_active ? (
                                  <CheckCircleIcon className="h-5 w-5 text-success-600" />
                                ) : (
                                  <XCircleIcon className="h-5 w-5 text-error-600" />
                                )}
                                <Badge variant={subscription.is_active ? 'success' : 'error'}>
                                  {subscription.status}
                                </Badge>
                              </div>
                            ) : (
                              <Badge variant="secondary">No Subscription</Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end space-x-2">
                              {subscription ? (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => startEdit(customer.id)}
                                >
                                  <PencilIcon className="h-4 w-4" />
                                </Button>
                              ) : (
                                <Button
                                  variant="primary"
                                  size="sm"
                                  onClick={() => startCreate(customer.id)}
                                >
                                  <PlusIcon className="h-4 w-4 mr-1" />
                                  Create
                                </Button>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        )}

        {/* Create Subscription Modal */}
        {showCreateModal && selectedCustomer && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <Card className="max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-bold text-neutral-900">Create Subscription</h2>
                  <button
                    onClick={() => setShowCreateModal(false)}
                    className="text-neutral-500 hover:text-neutral-700"
                  >
                    ×
                  </button>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreate} className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Subscription Name
                    </label>
                    <Input
                      value={formData.subscription_name}
                      onChange={(e) => setFormData({ ...formData, subscription_name: e.target.value })}
                      placeholder="Starter Plan"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Max Seats *
                      </label>
                      <Input
                        type="number"
                        value={formData.max_seats}
                        onChange={(e) => setFormData({ ...formData, max_seats: parseInt(e.target.value) || 0 })}
                        required
                        min="1"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Max Nodes *
                      </label>
                      <Input
                        type="number"
                        value={formData.max_nodes}
                        onChange={(e) => setFormData({ ...formData, max_nodes: parseInt(e.target.value) || 0 })}
                        required
                        min="1"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Monthly Price
                      </label>
                      <Input
                        type="number"
                        value={formData.monthly_price}
                        onChange={(e) => setFormData({ ...formData, monthly_price: parseFloat(e.target.value) || 0 })}
                        step="0.01"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Seat Overage Rate
                      </label>
                      <Input
                        type="number"
                        value={formData.seat_overage_rate}
                        onChange={(e) => setFormData({ ...formData, seat_overage_rate: parseFloat(e.target.value) || 0 })}
                        step="0.01"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Node Overage Rate
                    </label>
                    <Input
                      type="number"
                      value={formData.node_overage_rate}
                      onChange={(e) => setFormData({ ...formData, node_overage_rate: parseFloat(e.target.value) || 0 })}
                      step="0.01"
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
                      placeholder="Additional notes about this subscription"
                    />
                  </div>

                  <div className="flex items-center space-x-4">
                    <label className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={formData.is_enforced}
                        onChange={(e) => setFormData({ ...formData, is_enforced: e.target.checked })}
                        className="rounded border-neutral-300"
                      />
                      <span className="text-sm text-neutral-700">Enforce Limits</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={formData.auto_renew}
                        onChange={(e) => setFormData({ ...formData, auto_renew: e.target.checked })}
                        className="rounded border-neutral-300"
                      />
                      <span className="text-sm text-neutral-700">Auto Renew</span>
                    </label>
                  </div>

                  <div className="flex items-center justify-end space-x-3 pt-4 border-t border-neutral-200">
                    <Button
                      type="button"
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

        {/* Edit Subscription Modal */}
        {showEditModal && selectedCustomer && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <Card className="max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-bold text-neutral-900">Edit Subscription</h2>
                  <button
                    onClick={() => setShowEditModal(false)}
                    className="text-neutral-500 hover:text-neutral-700"
                  >
                    ×
                  </button>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleUpdate} className="space-y-6">
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
                        value={formData.max_seats}
                        onChange={(e) => setFormData({ ...formData, max_seats: parseInt(e.target.value) || 0 })}
                        required
                        min="1"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Max Nodes *
                      </label>
                      <Input
                        type="number"
                        value={formData.max_nodes}
                        onChange={(e) => setFormData({ ...formData, max_nodes: parseInt(e.target.value) || 0 })}
                        required
                        min="1"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Monthly Price
                      </label>
                      <Input
                        type="number"
                        value={formData.monthly_price}
                        onChange={(e) => setFormData({ ...formData, monthly_price: parseFloat(e.target.value) || 0 })}
                        step="0.01"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Seat Overage Rate
                      </label>
                      <Input
                        type="number"
                        value={formData.seat_overage_rate}
                        onChange={(e) => setFormData({ ...formData, seat_overage_rate: parseFloat(e.target.value) || 0 })}
                        step="0.01"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Node Overage Rate
                    </label>
                    <Input
                      type="number"
                      value={formData.node_overage_rate}
                      onChange={(e) => setFormData({ ...formData, node_overage_rate: parseFloat(e.target.value) || 0 })}
                      step="0.01"
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

                  <div className="flex items-center space-x-4">
                    <label className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={formData.is_enforced}
                        onChange={(e) => setFormData({ ...formData, is_enforced: e.target.checked })}
                        className="rounded border-neutral-300"
                      />
                      <span className="text-sm text-neutral-700">Enforce Limits</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={formData.auto_renew}
                        onChange={(e) => setFormData({ ...formData, auto_renew: e.target.checked })}
                        className="rounded border-neutral-300"
                      />
                      <span className="text-sm text-neutral-700">Auto Renew</span>
                    </label>
                  </div>

                  <div className="flex items-center justify-end space-x-3 pt-4 border-t border-neutral-200">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setShowEditModal(false)}
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

