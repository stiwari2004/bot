'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardHeader, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/Select';
import { Table, TableHeader, TableRow, TableHead, TableCell, TableBody } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { useSuperAdminAuth } from '@/contexts/SuperAdminAuthContext';
import { apiConfig } from '@/lib/api-config';
import {
  UserGroupIcon,
  PlusIcon,
  ArrowLeftIcon,
  BuildingOfficeIcon,
} from '@heroicons/react/24/outline';

interface Tenant {
  id: number;
  name: string;
  subdomain_slug: string | null;
}

interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  last_login: string | null;
  created_at: string | null;
}

export default function UsersPage() {
  const router = useRouter();
  const { token } = useSuperAdminAuth();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<number | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [usersLoading, setUsersLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editUserId, setEditUserId] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'user',
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
      if (data.length > 0 && !selectedTenantId) {
        setSelectedTenantId(data[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch tenants');
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async (tenantId: number) => {
    setUsersLoading(true);
    setError(null);
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
      setUsers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch users');
    } finally {
      setUsersLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchTenants();
    } else {
      setError('Not authenticated. Please log in as Super Admin.');
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (selectedTenantId && token) {
      fetchUsers(selectedTenantId);
    }
  }, [selectedTenantId, token]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTenantId) return;
    setError(null);
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.createTenantUser(selectedTenantId), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          full_name: formData.full_name || null,
          role: formData.role,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to create user' }));
        throw new Error(errorData.detail || 'Failed to create user');
      }

      setShowCreateModal(false);
      setFormData({
        email: '',
        password: '',
        full_name: '',
        role: 'user',
      });
      fetchUsers(selectedTenantId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create user');
    }
  };

  const handleEditUser = (user: User) => {
    setEditUserId(user.id);
    setFormData({
      email: user.email,
      password: '',
      full_name: user.full_name || '',
      role: user.role,
    });
    setShowCreateModal(true);
  };

  const handleDeleteUser = async (userId: number) => {
    if (!selectedTenantId) return;
    if (!confirm('Deactivate this user?')) return;
    setError(null);
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.deleteTenantUser(selectedTenantId, userId), {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to deactivate user');
      }
      fetchUsers(selectedTenantId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deactivate user');
    }
  };

  const handleSubmitUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTenantId) return;
    setError(null);
    const isEdit = !!editUserId;
    try {
      if (isEdit) {
        const payload: any = {
          full_name: formData.full_name || null,
          role: formData.role,
          is_active: true,
        };
        if (formData.password) {
          payload.password = formData.password;
        }
        const response = await fetch(apiConfig.endpoints.superAdmin.updateTenantUser(selectedTenantId, editUserId!), {
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
      } else {
        const response = await fetch(apiConfig.endpoints.superAdmin.createTenantUser(selectedTenantId), {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email: formData.email,
            password: formData.password,
            full_name: formData.full_name || null,
            role: formData.role,
          }),
        });
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Failed to create user' }));
          throw new Error(errorData.detail || 'Failed to create user');
        }
      }
      setShowCreateModal(false);
      setEditUserId(null);
      setFormData({
        email: '',
        password: '',
        full_name: '',
        role: 'user',
      });
      fetchUsers(selectedTenantId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save user');
    }
  };

  const selectedTenant = tenants.find((t) => t.id === selectedTenantId);

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
              <h1 className="text-3xl font-bold text-neutral-900">User Management</h1>
              <p className="text-neutral-600 mt-1">Manage users across all tenants</p>
            </div>
          </div>
          {selectedTenantId && (
            <Button
              variant="primary"
              leftIcon={<PlusIcon className="h-5 w-5" />}
              onClick={() => {
                setEditUserId(null);
                setFormData({
                  email: '',
                  password: '',
                  full_name: '',
                  role: 'user',
                });
                setShowCreateModal(true);
              }}
            >
              Create User
            </Button>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <Card variant="elevated" className="bg-error-50 border-error-200 mb-6">
            <CardContent padding="md">
              <p className="text-error-800">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Tenant Selector */}
        <Card variant="elevated" className="mb-6">
          <CardContent padding="md">
            <div className="flex items-center space-x-4">
              <BuildingOfficeIcon className="h-5 w-5 text-neutral-600" />
              <label className="text-sm font-medium text-neutral-700">Select Tenant:</label>
              <Select
                value={selectedTenantId?.toString() || ''}
                onValueChange={(value) => setSelectedTenantId(parseInt(value))}
              >
                <SelectTrigger className="w-64">
                  <SelectValue placeholder="Select a tenant" />
                </SelectTrigger>
                <SelectContent>
                  {tenants.map((tenant) => (
                    <SelectItem key={tenant.id} value={tenant.id.toString()}>
                      {tenant.name} {tenant.subdomain_slug && `(${tenant.subdomain_slug})`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Users Table */}
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-neutral-600">Loading tenants...</p>
          </div>
        ) : !selectedTenantId ? (
          <Card variant="elevated">
            <CardContent padding="lg" className="text-center">
              <UserGroupIcon className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
              <p className="text-neutral-600">Please select a tenant to view its users</p>
            </CardContent>
          </Card>
        ) : (
          <Card variant="elevated">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-neutral-900">
                    Users for {selectedTenant?.name}
                  </h2>
                  <p className="text-sm text-neutral-600 mt-1">
                    {users.length} user{users.length !== 1 ? 's' : ''} found
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent padding="none">
              {usersLoading ? (
                <div className="text-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
                  <p className="mt-4 text-neutral-600">Loading users...</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Email</TableHead>
                      <TableHead>Full Name</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Last Login</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-8 text-neutral-500">
                          No users found for this tenant. Create your first user to get started.
                        </TableCell>
                      </TableRow>
                    ) : (
                      users.map((user) => (
                        <TableRow key={user.id}>
                          <TableCell className="font-medium">{user.email}</TableCell>
                          <TableCell>{user.full_name || '-'}</TableCell>
                          <TableCell>
                            <Badge
                              variant={
                                user.role === 'admin'
                                  ? 'warning'
                                  : user.role === 'viewer'
                                  ? 'secondary'
                                  : 'primary'
                              }
                            >
                              {user.role}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant={user.is_active ? 'success' : 'error'}>
                              {user.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {user.last_login
                              ? new Date(user.last_login).toLocaleDateString()
                              : 'Never'}
                          </TableCell>
                          <TableCell>
                            {user.created_at
                              ? new Date(user.created_at).toLocaleDateString()
                              : '-'}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center space-x-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEditUser(user)}
                              >
                                Edit
                              </Button>
                              <Button
                                variant="danger"
                                size="sm"
                                onClick={() => handleDeleteUser(user.id)}
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
            </CardContent>
          </Card>
        )}

        {/* Create/Edit User Modal */}
        {showCreateModal && selectedTenantId && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <Card variant="elevated" className="w-full max-w-md">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-bold text-neutral-900">
                    {editUserId ? 'Edit User' : 'Create New User'}
                  </h2>
                  <Button variant="ghost" onClick={() => setShowCreateModal(false)}>
                    ×
                  </Button>
                </div>
                <p className="text-sm text-neutral-600 mt-1">
                  For tenant: {selectedTenant?.name}
                </p>
              </CardHeader>
              <CardContent padding="lg">
                <form onSubmit={handleSubmitUser} className="space-y-4">
                  {!editUserId && (
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Email Address *
                      </label>
                      <Input
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        required
                        placeholder="user@example.com"
                      />
                    </div>
                  )}
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      {editUserId ? 'New Password (optional)' : 'Password *'}
                    </label>
                    <Input
                      type="password"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      required={!editUserId}
                      placeholder={
                        editUserId ? 'Leave blank to keep current password' : 'Enter password'
                      }
                      minLength={editUserId ? 0 : 6}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Full Name
                    </label>
                    <Input
                      value={formData.full_name}
                      onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                      placeholder="John Doe"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Role *
                    </label>
                    <Select
                      value={formData.role}
                      onValueChange={(value) => setFormData({ ...formData, role: value })}
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
                  <div className="flex justify-end space-x-3 pt-4">
                    <Button variant="outline" onClick={() => setShowCreateModal(false)}>
                      Cancel
                    </Button>
                    <Button type="submit" variant="primary">
                      {editUserId ? 'Save Changes' : 'Create User'}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}




