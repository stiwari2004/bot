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
  BuildingOfficeIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  EyeIcon,
  UserGroupIcon,
  ArrowLeftIcon,
} from '@heroicons/react/24/outline';

interface Tenant {
  id: number;
  name: string;
  subdomain_slug: string | null;
  description: string | null;
  deployment_type: string;
  is_active: boolean;
  onboarding_status: string;
  contact_email: string | null;
  contact_name: string | null;
  created_at: string | null;
}

interface TenantDetail extends Tenant {
  user_count?: number;
  platform_managed?: boolean;
  contact_phone?: string | null;
  config_metadata?: Record<string, any> | null;
  updated_at?: string | null;
}

interface TenantUser {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  created_at?: string | null;
}

export default function TenantsPage() {
  const router = useRouter();
  const { token } = useSuperAdminAuth();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showViewModal, setShowViewModal] = useState(false);
  const [showUsersModal, setShowUsersModal] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<TenantDetail | null>(null);
  const [tenantUsers, setTenantUsers] = useState<TenantUser[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersError, setUsersError] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] = useState<TenantUser | null>(null);
  const [userForm, setUserForm] = useState({
    full_name: '',
    role: 'user',
    password: '',
    is_active: true,
  });
  const [formData, setFormData] = useState({
    name: '',
    subdomain_slug: '',
    description: '',
    deployment_type: 'saas',
    contact_email: '',
    contact_name: '',
    contact_phone: '',
    is_msp: false,
    parent_tenant_id: null as number | null,
  });
  
  const [billingConfig, setBillingConfig] = useState({
    fixed_monthly_cost: 0,
    per_node_enabled: false,
    per_node_cost: 0,
    node_count_override: null as number | null,
    per_ticket_received_enabled: false,
    per_ticket_received_cost: 0,
    per_ticket_resolved_enabled: false,
    per_ticket_resolved_cost: 0,
    per_execution_enabled: false,
    per_execution_cost: 0,
    per_api_call_enabled: false,
    per_api_call_cost: 0,
    per_llm_token_enabled: false,
    per_llm_token_cost: 0,
    billing_cycle: 'monthly',
    billing_day: 1,
    is_active: true,
  });
  
  const [showBillingConfig, setShowBillingConfig] = useState(false);
  const [showSubscriptionConfig, setShowSubscriptionConfig] = useState(false);
  const [subscriptionConfig, setSubscriptionConfig] = useState({
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

  const fetchTenants = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.tenants(), {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch tenants');
      }
      const data = await response.json();
      setTenants(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch tenants');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchTenants();
    }
  }, [token]);

  const fetchTenantUsers = async (tenantId: number) => {
    setUsersLoading(true);
    setUsersError(null);
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.tenantUsers(tenantId), {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch users');
      }
      const data = await response.json();
      setTenantUsers(data);
    } catch (err) {
      setUsersError(err instanceof Error ? err.message : 'Failed to fetch users');
    } finally {
      setUsersLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.createTenant(), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: formData.name,
          subdomain_slug: formData.subdomain_slug || null,
          description: formData.description || null,
          deployment_type: formData.deployment_type,
          contact_email: formData.contact_email || null,
          contact_name: formData.contact_name || null,
          contact_phone: formData.contact_phone || null,
          is_msp: formData.is_msp,
          parent_tenant_id: formData.parent_tenant_id || null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to create tenant' }));
        throw new Error(errorData.detail || 'Failed to create tenant');
      }

      setShowCreateModal(false);
      setFormData({
        name: '',
        subdomain_slug: '',
        description: '',
        deployment_type: 'saas',
        contact_email: '',
        contact_name: '',
        contact_phone: '',
        is_msp: false,
        parent_tenant_id: null,
      });
      setShowBillingConfig(false);
      setShowSubscriptionConfig(false);
      setBillingConfig({
        fixed_monthly_cost: 0,
        per_node_enabled: false,
        per_node_cost: 0,
        node_count_override: null,
        per_ticket_received_enabled: false,
        per_ticket_received_cost: 0,
        per_ticket_resolved_enabled: false,
        per_ticket_resolved_cost: 0,
        per_execution_enabled: false,
        per_execution_cost: 0,
        per_api_call_enabled: false,
        per_api_call_cost: 0,
        per_llm_token_enabled: false,
        per_llm_token_cost: 0,
        billing_cycle: 'monthly',
        billing_day: 1,
        is_active: true,
      });
      setSubscriptionConfig({
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
      fetchTenants();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create tenant');
    }
  };

  const openUsersModal = async (tenant: TenantDetail) => {
    setSelectedTenant(tenant);
    setShowUsersModal(true);
    await fetchTenantUsers(tenant.id);
    setSelectedUser(null);
    setUserForm({
      full_name: '',
      role: 'user',
      password: '',
      is_active: true,
    });
  };

  const startEditUser = (user: TenantUser) => {
    setSelectedUser(user);
    setUserForm({
      full_name: user.full_name || '',
      role: user.role,
      password: '',
      is_active: user.is_active,
    });
    setUsersError(null);
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTenant || !selectedUser) return;
    setUsersError(null);
    try {
      const payload: any = {
        full_name: userForm.full_name || null,
        role: userForm.role,
        is_active: userForm.is_active,
      };
      if (userForm.password) {
        payload.password = userForm.password;
      }
      const response = await fetch(apiConfig.endpoints.superAdmin.updateTenantUser(selectedTenant.id, selectedUser.id), {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to update user');
      }
      await fetchTenantUsers(selectedTenant.id);
      setSelectedUser(null);
      setUserForm({
        full_name: '',
        role: 'user',
        password: '',
        is_active: true,
      });
      setUsersError(''); // clear any residual
    } catch (err) {
      setUsersError(err instanceof Error ? err.message : 'Failed to update user');
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!selectedTenant) return;
    if (!confirm('Deactivate this user?')) return;
    setUsersError(null);
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.deleteTenantUser(selectedTenant.id, userId), {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to deactivate user');
      }
      await fetchTenantUsers(selectedTenant.id);
      if (selectedUser && selectedUser.id === userId) {
        setSelectedUser(null);
      }
    } catch (err) {
      setUsersError(err instanceof Error ? err.message : 'Failed to deactivate user');
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTenant) return;
    setError(null);
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.updateTenant(selectedTenant.id), {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: formData.name,
          subdomain_slug: formData.subdomain_slug || null,
          description: formData.description || null,
          deployment_type: formData.deployment_type,
          contact_email: formData.contact_email || null,
          contact_name: formData.contact_name || null,
          contact_phone: formData.contact_phone || null,
          is_msp: formData.is_msp,
          parent_tenant_id: formData.parent_tenant_id || null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to update tenant' }));
        throw new Error(errorData.detail || 'Failed to update tenant');
      }

      setShowEditModal(false);
      setSelectedTenant(null);
      fetchTenants();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update tenant');
    }
  };

  const handleDelete = async (tenantId: number) => {
    if (!confirm('Are you sure you want to deactivate this tenant?')) return;
    setError(null);
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.deleteTenant(tenantId), {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to delete tenant' }));
        throw new Error(errorData.detail || 'Failed to delete tenant');
      }

      fetchTenants();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete tenant');
    }
  };

  const openEditModal = (tenant: Tenant) => {
    setSelectedTenant(tenant);
    setFormData({
      name: tenant.name,
      subdomain_slug: tenant.subdomain_slug || '',
      description: tenant.description || '',
      deployment_type: tenant.deployment_type,
      contact_email: tenant.contact_email || '',
      contact_name: tenant.contact_name || '',
      contact_phone: (tenant as any).contact_phone || '',
      is_msp: (tenant as any).is_msp || false,
      parent_tenant_id: (tenant as any).parent_tenant_id || null,
    });
    setShowEditModal(true);
  };

  const openViewModal = async (tenant: Tenant) => {
    setSelectedTenant(tenant);
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.tenant(tenant.id), {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data: TenantDetail = await response.json();
        setSelectedTenant(data);
      }
    } catch (err) {
      console.error('Failed to fetch tenant details:', err);
    }
    setShowViewModal(true);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-neutral-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              onClick={() => router.push('/super-admin')}
              leftIcon={<ArrowLeftIcon className="h-5 w-5" />}
            >
              Back to Dashboard
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-neutral-900">Tenant Management</h1>
              <p className="text-neutral-600 mt-1">Manage all platform tenants</p>
            </div>
          </div>
          <Button
            variant="primary"
            leftIcon={<PlusIcon className="h-5 w-5" />}
            onClick={() => setShowCreateModal(true)}
          >
            Create Tenant
          </Button>
        </div>

        {/* Error Message */}
        {error && (
          <Card variant="elevated" className="bg-error-50 border-error-200 mb-6">
            <CardContent padding="md">
              <p className="text-error-800">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Tenants Table */}
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-neutral-600">Loading tenants...</p>
          </div>
        ) : (
          <Card variant="elevated">
            <CardContent padding="none">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Subdomain</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Onboarding</TableHead>
                    <TableHead>Contact</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tenants.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-8 text-neutral-500">
                        No tenants found. Create your first tenant to get started.
                      </TableCell>
                    </TableRow>
                  ) : (
                    tenants.map((tenant) => (
                      <TableRow key={tenant.id}>
                        <TableCell className="font-medium">{tenant.name}</TableCell>
                        <TableCell>{tenant.subdomain_slug || '-'}</TableCell>
                        <TableCell>
                          <Badge variant={tenant.deployment_type === 'saas' ? 'success' : 'warning'}>
                            {tenant.deployment_type.toUpperCase()}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={tenant.is_active ? 'success' : 'error'}>
                            {tenant.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="primary">{tenant.onboarding_status}</Badge>
                        </TableCell>
                        <TableCell>{tenant.contact_email || '-'}</TableCell>
                        <TableCell>
                          {tenant.created_at
                            ? new Date(tenant.created_at).toLocaleDateString()
                            : '-'}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openViewModal(tenant)}
                              leftIcon={<EyeIcon className="h-4 w-4" />}
                            >
                              View
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openEditModal(tenant)}
                              leftIcon={<PencilIcon className="h-4 w-4" />}
                            >
                              Edit
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openUsersModal(tenant as TenantDetail)}
                              leftIcon={<UserGroupIcon className="h-4 w-4" />}
                            >
                              Users
                            </Button>
                            <Button
                              variant="danger"
                              size="sm"
                              onClick={() => handleDelete(tenant.id)}
                              leftIcon={<TrashIcon className="h-4 w-4" />}
                            >
                              Delete
                            </Button>
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

        {/* Users Modal */}
        {showUsersModal && selectedTenant && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <Card variant="elevated" className="w-full max-w-4xl max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-bold text-neutral-900">Users - {selectedTenant.name}</h2>
                    <p className="text-sm text-neutral-600">View, edit, or deactivate users for this tenant.</p>
                  </div>
                  <Button variant="ghost" onClick={() => { setShowUsersModal(false); setSelectedUser(null); }}>
                    ×
                  </Button>
                </div>
              </CardHeader>
              <CardContent padding="lg" className="space-y-6">
                {usersError && (
                  <div className="p-3 bg-error-50 border border-error-200 rounded-lg text-error-800">
                    {usersError}
                  </div>
                )}

                {usersLoading ? (
                  <div className="text-center py-6">
                    <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600 mx-auto"></div>
                    <p className="mt-3 text-neutral-600">Loading users...</p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Email</TableHead>
                        <TableHead>Name</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {tenantUsers.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={5} className="text-center py-6 text-neutral-500">
                            No users found for this tenant.
                          </TableCell>
                        </TableRow>
                      ) : (
                        tenantUsers.map((user) => (
                          <TableRow key={user.id}>
                            <TableCell className="font-medium">{user.email}</TableCell>
                            <TableCell>{user.full_name || '-'}</TableCell>
                            <TableCell>
                              <Badge variant="secondary">{user.role}</Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant={user.is_active ? 'success' : 'error'}>
                                {user.is_active ? 'Active' : 'Inactive'}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center space-x-2">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => startEditUser(user)}
                                  leftIcon={<PencilIcon className="h-4 w-4" />}
                                >
                                  Edit
                                </Button>
                                <Button
                                  variant="danger"
                                  size="sm"
                                  onClick={() => handleDeleteUser(user.id)}
                                  leftIcon={<TrashIcon className="h-4 w-4" />}
                                >
                                  Delete
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                )}

                {/* Edit user form */}
                {selectedUser && (
                  <div className="border-t pt-4">
                    <h3 className="text-lg font-semibold text-neutral-900 mb-2">
                      Edit User: {selectedUser.email}
                    </h3>
                    <form onSubmit={handleUpdateUser} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          Full Name
                        </label>
                        <Input
                          value={userForm.full_name}
                          onChange={(e) => setUserForm({ ...userForm, full_name: e.target.value })}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          Role
                        </label>
                        <Select
                          value={userForm.role}
                          onValueChange={(val) => setUserForm({ ...userForm, role: val })}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select role" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="admin">Admin</SelectItem>
                            <SelectItem value="user">User</SelectItem>
                            <SelectItem value="viewer">Viewer</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          New Password (optional)
                        </label>
                        <Input
                          type="password"
                          value={userForm.password}
                          onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                          placeholder="Leave blank to keep unchanged"
                        />
                      </div>
                      <div className="flex items-center space-x-2 mt-2">
                        <input
                          type="checkbox"
                          checked={userForm.is_active}
                          onChange={(e) => setUserForm({ ...userForm, is_active: e.target.checked })}
                          className="h-4 w-4"
                        />
                        <label className="text-sm text-neutral-700">Active</label>
                      </div>
                      <div className="md:col-span-2 flex justify-end space-x-3 mt-2">
                        <Button variant="outline" onClick={() => setSelectedUser(null)} type="button">
                          Cancel
                        </Button>
                        <Button type="submit" variant="primary">
                          Save Changes
                        </Button>
                      </div>
                    </form>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Create Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <Card variant="elevated" className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-bold text-neutral-900">Create New Tenant</h2>
                  <Button variant="ghost" onClick={() => setShowCreateModal(false)}>
                    ×
                  </Button>
                </div>
              </CardHeader>
              <CardContent padding="lg">
                <form onSubmit={handleCreate} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Tenant Name *
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
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Deployment Type *
                    </label>
                    <Select
                      value={formData.deployment_type}
                      onValueChange={(value) => setFormData({ ...formData, deployment_type: value })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select deployment type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="saas">SaaS (Platform Managed)</SelectItem>
                        <SelectItem value="paas">PaaS (Self-Hosted)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Description
                    </label>
                    <Textarea
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      placeholder="Brief description of the tenant"
                      rows={3}
                    />
                  </div>
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
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Contact Phone
                    </label>
                    <Input
                      value={formData.contact_phone}
                      onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                      placeholder="+1-555-0123"
                    />
                  </div>
                  
                  {/* MSP Configuration */}
                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1">
                          Is MSP (White-label Reseller)
                        </label>
                        <p className="text-xs text-neutral-500">Enable if this tenant can create sub-tenants/customers</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={formData.is_msp}
                        onChange={(e) => setFormData({ ...formData, is_msp: e.target.checked })}
                        className="h-4 w-4"
                      />
                    </div>
                    {formData.is_msp && (
                      <div className="ml-6 p-3 bg-primary-50 rounded-lg">
                        <p className="text-sm text-primary-800">
                          This tenant will be able to create and manage their own customers through the Tenant Admin interface.
                        </p>
                      </div>
                    )}
                  </div>
                  
                  {/* Billing Configuration */}
                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1">
                          Configure Billing Now
                        </label>
                        <p className="text-xs text-neutral-500">Set up billing configuration during tenant creation</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={showBillingConfig}
                        onChange={(e) => setShowBillingConfig(e.target.checked)}
                        className="h-4 w-4"
                      />
                    </div>
                    
                    {showBillingConfig && (
                      <div className="ml-6 space-y-4 p-4 bg-neutral-50 rounded-lg border border-neutral-200">
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 mb-2">
                            Fixed Monthly Cost (₹)
                          </label>
                          <Input
                            type="number"
                            step="0.01"
                            value={billingConfig.fixed_monthly_cost}
                            onChange={(e) => setBillingConfig({ ...billingConfig, fixed_monthly_cost: parseFloat(e.target.value) || 0 })}
                          />
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <label className="text-sm font-medium text-neutral-700">Per-Node Billing</label>
                              <input
                                type="checkbox"
                                checked={billingConfig.per_node_enabled}
                                onChange={(e) => setBillingConfig({ ...billingConfig, per_node_enabled: e.target.checked })}
                                className="h-4 w-4"
                              />
                            </div>
                            {billingConfig.per_node_enabled && (
                              <Input
                                type="number"
                                step="0.01"
                                value={billingConfig.per_node_cost}
                                onChange={(e) => setBillingConfig({ ...billingConfig, per_node_cost: parseFloat(e.target.value) || 0 })}
                                placeholder="Cost per node"
                              />
                            )}
                          </div>
                          
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <label className="text-sm font-medium text-neutral-700">Per-Ticket-Received</label>
                              <input
                                type="checkbox"
                                checked={billingConfig.per_ticket_received_enabled}
                                onChange={(e) => setBillingConfig({ ...billingConfig, per_ticket_received_enabled: e.target.checked })}
                                className="h-4 w-4"
                              />
                            </div>
                            {billingConfig.per_ticket_received_enabled && (
                              <Input
                                type="number"
                                step="0.01"
                                value={billingConfig.per_ticket_received_cost}
                                onChange={(e) => setBillingConfig({ ...billingConfig, per_ticket_received_cost: parseFloat(e.target.value) || 0 })}
                                placeholder="Cost per ticket"
                              />
                            )}
                          </div>
                          
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <label className="text-sm font-medium text-neutral-700">Per-Ticket-Resolved</label>
                              <input
                                type="checkbox"
                                checked={billingConfig.per_ticket_resolved_enabled}
                                onChange={(e) => setBillingConfig({ ...billingConfig, per_ticket_resolved_enabled: e.target.checked })}
                                className="h-4 w-4"
                              />
                            </div>
                            {billingConfig.per_ticket_resolved_enabled && (
                              <Input
                                type="number"
                                step="0.01"
                                value={billingConfig.per_ticket_resolved_cost}
                                onChange={(e) => setBillingConfig({ ...billingConfig, per_ticket_resolved_cost: parseFloat(e.target.value) || 0 })}
                                placeholder="Cost per ticket"
                              />
                            )}
                          </div>
                          
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <label className="text-sm font-medium text-neutral-700">Per-Execution</label>
                              <input
                                type="checkbox"
                                checked={billingConfig.per_execution_enabled}
                                onChange={(e) => setBillingConfig({ ...billingConfig, per_execution_enabled: e.target.checked })}
                                className="h-4 w-4"
                              />
                            </div>
                            {billingConfig.per_execution_enabled && (
                              <Input
                                type="number"
                                step="0.01"
                                value={billingConfig.per_execution_cost}
                                onChange={(e) => setBillingConfig({ ...billingConfig, per_execution_cost: parseFloat(e.target.value) || 0 })}
                                placeholder="Cost per execution"
                              />
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* Subscription Configuration */}
                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1">
                          Configure Subscription Now
                        </label>
                        <p className="text-xs text-neutral-500">Set up seat and node limits during tenant creation</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={showSubscriptionConfig}
                        onChange={(e) => setShowSubscriptionConfig(e.target.checked)}
                        className="h-4 w-4"
                      />
                    </div>
                    
                    {showSubscriptionConfig && (
                      <div className="ml-6 space-y-4 p-4 bg-neutral-50 rounded-lg border border-neutral-200">
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 mb-2">
                            Subscription Name (Optional)
                          </label>
                          <Input
                            value={subscriptionConfig.subscription_name}
                            onChange={(e) => setSubscriptionConfig({ ...subscriptionConfig, subscription_name: e.target.value })}
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
                              value={subscriptionConfig.max_seats}
                              onChange={(e) => setSubscriptionConfig({ ...subscriptionConfig, max_seats: parseInt(e.target.value) || 0 })}
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
                              value={subscriptionConfig.max_nodes}
                              onChange={(e) => setSubscriptionConfig({ ...subscriptionConfig, max_nodes: parseInt(e.target.value) || 0 })}
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
                            value={subscriptionConfig.monthly_price}
                            onChange={(e) => setSubscriptionConfig({ ...subscriptionConfig, monthly_price: parseFloat(e.target.value) || 0 })}
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
                              value={subscriptionConfig.seat_overage_rate}
                              onChange={(e) => setSubscriptionConfig({ ...subscriptionConfig, seat_overage_rate: parseFloat(e.target.value) || 0 })}
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
                              value={subscriptionConfig.node_overage_rate}
                              onChange={(e) => setSubscriptionConfig({ ...subscriptionConfig, node_overage_rate: parseFloat(e.target.value) || 0 })}
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
                            checked={subscriptionConfig.is_enforced}
                            onChange={(e) => setSubscriptionConfig({ ...subscriptionConfig, is_enforced: e.target.checked })}
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
                            checked={subscriptionConfig.auto_renew}
                            onChange={(e) => setSubscriptionConfig({ ...subscriptionConfig, auto_renew: e.target.checked })}
                            className="h-4 w-4"
                          />
                        </div>
                        
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 mb-2">
                            Expires At (Optional)
                          </label>
                          <Input
                            type="date"
                            value={subscriptionConfig.expires_at}
                            onChange={(e) => setSubscriptionConfig({ ...subscriptionConfig, expires_at: e.target.value })}
                          />
                        </div>
                        
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 mb-2">
                            Notes (Optional)
                          </label>
                          <Textarea
                            value={subscriptionConfig.notes}
                            onChange={(e) => setSubscriptionConfig({ ...subscriptionConfig, notes: e.target.value })}
                            rows={2}
                            placeholder="Admin notes about this subscription"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex justify-end space-x-3 pt-4">
                    <Button variant="outline" onClick={() => {
                      setShowCreateModal(false);
                      setShowBillingConfig(false);
                      setShowSubscriptionConfig(false);
                      setBillingConfig({
                        fixed_monthly_cost: 0,
                        per_node_enabled: false,
                        per_node_cost: 0,
                        node_count_override: null,
                        per_ticket_received_enabled: false,
                        per_ticket_received_cost: 0,
                        per_ticket_resolved_enabled: false,
                        per_ticket_resolved_cost: 0,
                        per_execution_enabled: false,
                        per_execution_cost: 0,
                        per_api_call_enabled: false,
                        per_api_call_cost: 0,
                        per_llm_token_enabled: false,
                        per_llm_token_cost: 0,
                        billing_cycle: 'monthly',
                        billing_day: 1,
                        is_active: true,
                      });
                      setSubscriptionConfig({
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
                    }}>
                      Cancel
                    </Button>
                    <Button type="submit" variant="primary">
                      Create Tenant
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Edit Modal */}
        {showEditModal && selectedTenant && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <Card variant="elevated" className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-bold text-neutral-900">Edit Tenant</h2>
                  <Button variant="ghost" onClick={() => setShowEditModal(false)}>
                    ×
                  </Button>
                </div>
              </CardHeader>
              <CardContent padding="lg">
                <form onSubmit={handleUpdate} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Tenant Name *
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
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Deployment Type *
                    </label>
                    <Select
                      value={formData.deployment_type}
                      onValueChange={(value) => setFormData({ ...formData, deployment_type: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="saas">SaaS (Platform Managed)</SelectItem>
                        <SelectItem value="paas">PaaS (Self-Hosted)</SelectItem>
                      </SelectContent>
                    </Select>
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
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Contact Phone
                    </label>
                    <Input
                      value={formData.contact_phone}
                      onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                    />
                  </div>
                  <div className="flex justify-end space-x-3 pt-4">
                    <Button variant="outline" onClick={() => setShowEditModal(false)}>
                      Cancel
                    </Button>
                    <Button type="submit" variant="primary">
                      Update Tenant
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        )}

        {/* View Modal */}
        {showViewModal && selectedTenant && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <Card variant="elevated" className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-bold text-neutral-900">Tenant Details</h2>
                  <Button variant="ghost" onClick={() => setShowViewModal(false)}>
                    ×
                  </Button>
                </div>
              </CardHeader>
              <CardContent padding="lg">
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1">Name</label>
                    <p className="text-neutral-900">{selectedTenant.name}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1">Subdomain</label>
                    <p className="text-neutral-900">{selectedTenant.subdomain_slug || '-'}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1">Deployment Type</label>
                    <Badge variant={selectedTenant.deployment_type === 'saas' ? 'success' : 'warning'}>
                      {selectedTenant.deployment_type.toUpperCase()}
                    </Badge>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1">Status</label>
                    <Badge variant={selectedTenant.is_active ? 'success' : 'error'}>
                      {selectedTenant.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1">Onboarding Status</label>
                    <Badge variant="primary">{selectedTenant.onboarding_status}</Badge>
                  </div>
                  {selectedTenant.description && (
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">Description</label>
                      <p className="text-neutral-900">{selectedTenant.description}</p>
                    </div>
                  )}
                  {selectedTenant.contact_email && (
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">Contact Email</label>
                      <p className="text-neutral-900">{selectedTenant.contact_email}</p>
                    </div>
                  )}
                  {selectedTenant.contact_name && (
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">Contact Name</label>
                      <p className="text-neutral-900">{selectedTenant.contact_name}</p>
                    </div>
                  )}
                  {selectedTenant.user_count !== undefined && (
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">User Count</label>
                      <p className="text-neutral-900">{selectedTenant.user_count}</p>
                    </div>
                  )}
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1">Created At</label>
                    <p className="text-neutral-900">
                      {selectedTenant.created_at
                        ? new Date(selectedTenant.created_at).toLocaleString()
                        : '-'}
                    </p>
                  </div>
                  <div className="flex justify-end pt-4">
                    <Button variant="outline" onClick={() => setShowViewModal(false)}>
                      Close
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

