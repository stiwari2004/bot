'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardHeader, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Table, TableHeader, TableRow, TableHead, TableCell, TableBody } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { useMspAdminAuth } from '@/contexts/MspAdminAuthContext';
import { apiConfig } from '@/lib/api-config';
import {
  BuildingOfficeIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ArrowLeftIcon,
} from '@heroicons/react/24/outline';

interface Customer {
  id: number;
  name: string;
  subdomain_slug: string | null;
  description: string | null;
  contact_email: string | null;
  is_active: boolean;
  onboarding_status: string;
  created_at: string | null;
}

export default function CustomersPage() {
  const router = useRouter();
  const { token } = useMspAdminAuth();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    subdomain_slug: '',
    description: '',
    contact_email: '',
    contact_name: '',
    contact_phone: '',
    admin_email: '',
    admin_password: '',
    admin_full_name: '',
  });
  const [showBillingConfig, setShowBillingConfig] = useState(false);
  const [showSubscriptionConfig, setShowSubscriptionConfig] = useState(false);
  const [billingConfig, setBillingConfig] = useState({
    fixed_monthly_cost: 0,
    per_node_enabled: false,
    per_node_cost: 0,
    per_ticket_received_enabled: false,
    per_ticket_received_cost: 0,
    per_ticket_resolved_enabled: false,
    per_ticket_resolved_cost: 0,
    per_execution_enabled: false,
    per_execution_cost: 0,
    billing_cycle: 'monthly',
    billing_day: 1,
    is_active: true,
  });
  const [subscriptionConfig, setSubscriptionConfig] = useState({
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
    if (!token) return;
    setError(null);
    try {
      const payload: any = {
        name: formData.name,
        subdomain_slug: formData.subdomain_slug || null,
        description: formData.description || null,
        contact_email: formData.contact_email || null,
        contact_name: formData.contact_name || null,
        contact_phone: formData.contact_phone || null,
        admin_email: formData.admin_email,
        admin_password: formData.admin_password,
        admin_full_name: formData.admin_full_name || null,
      };

      if (showBillingConfig) {
        payload.billing_config = billingConfig;
      }

      if (showSubscriptionConfig) {
        payload.subscription_config = subscriptionConfig;
      }

      const response = await fetch(apiConfig.endpoints.tenantAdmin.customers(), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to create customer' }));
        throw new Error(errorData.detail || 'Failed to create customer');
      }

      setShowCreateModal(false);
      setFormData({
        name: '',
        subdomain_slug: '',
        description: '',
        contact_email: '',
        contact_name: '',
        contact_phone: '',
        admin_email: '',
        admin_password: '',
        admin_full_name: '',
      });
      setShowBillingConfig(false);
      setShowSubscriptionConfig(false);
      fetchCustomers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create customer');
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !selectedCustomer) return;
    setError(null);
    try {
      const response = await fetch(apiConfig.endpoints.tenantAdmin.customer(selectedCustomer.id), {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: formData.name,
          subdomain_slug: formData.subdomain_slug || null,
          description: formData.description || null,
          contact_email: formData.contact_email || null,
          contact_name: formData.contact_name || null,
          contact_phone: formData.contact_phone || null,
          is_active: selectedCustomer.is_active,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to update customer' }));
        throw new Error(errorData.detail || 'Failed to update customer');
      }

      setShowEditModal(false);
      setSelectedCustomer(null);
      fetchCustomers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update customer');
    }
  };

  const handleDelete = async (customerId: number) => {
    if (!token) return;
    if (!confirm('Are you sure you want to deactivate this customer?')) return;
    
    try {
      const response = await fetch(apiConfig.endpoints.tenantAdmin.customer(customerId), {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to deactivate customer');
      }

      fetchCustomers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deactivate customer');
    }
  };

  const startEdit = (customer: Customer) => {
    setSelectedCustomer(customer);
    setFormData({
      name: customer.name,
      subdomain_slug: customer.subdomain_slug || '',
      description: customer.description || '',
      contact_email: customer.contact_email || '',
      contact_name: '',
      contact_phone: '',
      admin_email: '',
      admin_password: '',
      admin_full_name: '',
    });
    setShowEditModal(true);
  };

  const startCreate = () => {
    setSelectedCustomer(null);
    setFormData({
      name: '',
      subdomain_slug: '',
      description: '',
      contact_email: '',
      contact_name: '',
      contact_phone: '',
      admin_email: '',
      admin_password: '',
      admin_full_name: '',
    });
    setShowBillingConfig(false);
    setShowSubscriptionConfig(false);
    setShowCreateModal(true);
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
                  <BuildingOfficeIcon className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-neutral-900">Customer Management</h1>
                  <p className="text-sm text-neutral-600">Manage your client tenants</p>
                </div>
              </div>
            </div>
            <Button
              variant="primary"
              onClick={startCreate}
              className="flex items-center space-x-2"
            >
              <PlusIcon className="h-5 w-5" />
              <span>Create Customer</span>
            </Button>
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
            <p className="mt-4 text-neutral-600">Loading customers...</p>
          </div>
        ) : (
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-neutral-900">Customers</h2>
            </CardHeader>
            <CardContent>
              {customers.length === 0 ? (
                <div className="text-center py-12">
                  <BuildingOfficeIcon className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
                  <p className="text-neutral-600 mb-4">No customers yet</p>
                  <Button variant="primary" onClick={startCreate}>
                    Create Your First Customer
                  </Button>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Contact Email</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Onboarding</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {customers.map((customer) => (
                      <TableRow key={customer.id}>
                        <TableCell className="font-medium">{customer.name}</TableCell>
                        <TableCell>{customer.contact_email || '-'}</TableCell>
                        <TableCell>
                          <Badge variant={customer.is_active ? 'success' : 'error'}>
                            {customer.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{customer.onboarding_status}</Badge>
                        </TableCell>
                        <TableCell>
                          {customer.created_at
                            ? new Date(customer.created_at).toLocaleDateString()
                            : '-'}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end space-x-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => startEdit(customer)}
                            >
                              <PencilIcon className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDelete(customer.id)}
                            >
                              <TrashIcon className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        )}

        {/* Create Customer Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <Card className="max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-bold text-neutral-900">Create Customer</h2>
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
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Customer Name *
                      </label>
                      <Input
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        required
                        placeholder="Acme Corporation"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Subdomain Slug
                      </label>
                      <Input
                        value={formData.subdomain_slug}
                        onChange={(e) => setFormData({ ...formData, subdomain_slug: e.target.value })}
                        placeholder="acme"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Description
                    </label>
                    <Textarea
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      placeholder="Customer description"
                      rows={3}
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Contact Email
                      </label>
                      <Input
                        type="email"
                        value={formData.contact_email}
                        onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                        placeholder="contact@example.com"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Contact Name
                      </label>
                      <Input
                        value={formData.contact_name}
                        onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                        placeholder="John Doe"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Contact Phone
                    </label>
                    <Input
                      value={formData.contact_phone}
                      onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                      placeholder="+1 234 567 8900"
                    />
                  </div>

                  <div className="border-t border-neutral-200 pt-4">
                    <h3 className="text-lg font-semibold text-neutral-900 mb-4">Admin User</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          Admin Email *
                        </label>
                        <Input
                          type="email"
                          value={formData.admin_email}
                          onChange={(e) => setFormData({ ...formData, admin_email: e.target.value })}
                          required
                          placeholder="admin@customer.com"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          Admin Full Name
                        </label>
                        <Input
                          value={formData.admin_full_name}
                          onChange={(e) => setFormData({ ...formData, admin_full_name: e.target.value })}
                          placeholder="Admin User"
                        />
                      </div>
                    </div>
                    <div className="mt-4">
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Admin Password *
                      </label>
                      <Input
                        type="password"
                        value={formData.admin_password}
                        onChange={(e) => setFormData({ ...formData, admin_password: e.target.value })}
                        required
                        placeholder="••••••••"
                      />
                    </div>
                  </div>

                  <div className="border-t border-neutral-200 pt-4">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-lg font-semibold text-neutral-900">Billing Configuration</h3>
                        <p className="text-sm text-neutral-600">Optional - can be configured later</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setShowBillingConfig(!showBillingConfig)}
                        className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                      >
                        {showBillingConfig ? 'Hide' : 'Configure'}
                      </button>
                    </div>
                    {showBillingConfig && (
                      <div className="space-y-4 p-4 bg-neutral-50 rounded-lg">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-neutral-700 mb-2">
                              Fixed Monthly Cost
                            </label>
                            <Input
                              type="number"
                              value={billingConfig.fixed_monthly_cost}
                              onChange={(e) => setBillingConfig({ ...billingConfig, fixed_monthly_cost: parseFloat(e.target.value) || 0 })}
                              step="0.01"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-neutral-700 mb-2">
                              Per Node Cost
                            </label>
                            <Input
                              type="number"
                              value={billingConfig.per_node_cost}
                              onChange={(e) => setBillingConfig({ ...billingConfig, per_node_cost: parseFloat(e.target.value) || 0 })}
                              step="0.01"
                            />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="border-t border-neutral-200 pt-4">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-lg font-semibold text-neutral-900">Subscription Configuration</h3>
                        <p className="text-sm text-neutral-600">Optional - can be configured later</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setShowSubscriptionConfig(!showSubscriptionConfig)}
                        className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                      >
                        {showSubscriptionConfig ? 'Hide' : 'Configure'}
                      </button>
                    </div>
                    {showSubscriptionConfig && (
                      <div className="space-y-4 p-4 bg-neutral-50 rounded-lg">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-neutral-700 mb-2">
                              Max Seats
                            </label>
                            <Input
                              type="number"
                              value={subscriptionConfig.max_seats}
                              onChange={(e) => setSubscriptionConfig({ ...subscriptionConfig, max_seats: parseInt(e.target.value) || 0 })}
                              min="1"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-neutral-700 mb-2">
                              Max Nodes
                            </label>
                            <Input
                              type="number"
                              value={subscriptionConfig.max_nodes}
                              onChange={(e) => setSubscriptionConfig({ ...subscriptionConfig, max_nodes: parseInt(e.target.value) || 0 })}
                              min="1"
                            />
                          </div>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 mb-2">
                            Subscription Name
                          </label>
                          <Input
                            value={subscriptionConfig.subscription_name}
                            onChange={(e) => setSubscriptionConfig({ ...subscriptionConfig, subscription_name: e.target.value })}
                            placeholder="Starter Plan"
                          />
                        </div>
                      </div>
                    )}
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
                      Create Customer
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Edit Customer Modal */}
        {showEditModal && selectedCustomer && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <Card className="max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-bold text-neutral-900">Edit Customer</h2>
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
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Customer Name *
                      </label>
                      <Input
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Subdomain Slug
                      </label>
                      <Input
                        value={formData.subdomain_slug}
                        onChange={(e) => setFormData({ ...formData, subdomain_slug: e.target.value })}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Description
                    </label>
                    <Textarea
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      rows={3}
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Contact Email
                      </label>
                      <Input
                        type="email"
                        value={formData.contact_email}
                        onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Contact Name
                      </label>
                      <Input
                        value={formData.contact_name}
                        onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Contact Phone
                    </label>
                    <Input
                      value={formData.contact_phone}
                      onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                    />
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
                      Update Customer
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

