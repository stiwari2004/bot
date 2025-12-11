'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardHeader, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/Select';
import { Table, TableHeader, TableRow, TableHead, TableCell, TableBody } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { useMspAdminAuth } from '@/contexts/MspAdminAuthContext';
import { apiConfig } from '@/lib/api-config';
import {
  UserGroupIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ArrowLeftIcon,
  BuildingOfficeIcon,
} from '@heroicons/react/24/outline';

interface Customer {
  id: number;
  name: string;
}

interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  created_at: string | null;
}

export default function UsersPage() {
  const router = useRouter();
  const { token, admin } = useMspAdminAuth();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState<number | null>(null);
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
      // Only show customer tenants (sub-tenants), NOT the MSP's own tenant
      // MSP admins should only create users for customers, not for their own MSP tenant
      setCustomers(data);
      if (!selectedCustomerId && data.length > 0) {
        setSelectedCustomerId(data[0]?.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch customers');
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async (customerId: number) => {
    if (!token) return;
    setUsersLoading(true);
    setError(null);
    try {
      // If it's the MSP's own tenant, we need a different endpoint or handle it differently
      // For now, use customer users endpoint for all
      const response = await fetch(apiConfig.endpoints.tenantAdmin.customerUsers(customerId), {
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
    if (token && admin) {
      fetchCustomers();
    }
  }, [token, admin]);

  useEffect(() => {
    if (selectedCustomerId && token) {
      fetchUsers(selectedCustomerId);
    }
  }, [selectedCustomerId, token]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCustomerId || !token) return;
    setError(null);
    try {
      if (editUserId) {
        // Update existing user
        const payload: any = {
          full_name: formData.full_name || null,
          role: formData.role,
        };
        if (formData.password) {
          payload.password = formData.password;
        }
        
        const response = await fetch(apiConfig.endpoints.tenantAdmin.customerUser(selectedCustomerId, editUserId), {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Failed to update user' }));
          throw new Error(errorData.detail || 'Failed to update user');
        }
      } else {
        // Create new user
        const response = await fetch(apiConfig.endpoints.tenantAdmin.customerUsers(selectedCustomerId), {
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
      fetchUsers(selectedCustomerId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save user');
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!selectedCustomerId || !token) return;
    if (!confirm('Are you sure you want to deactivate this user?')) return;
    
    try {
      const response = await fetch(apiConfig.endpoints.tenantAdmin.customerUser(selectedCustomerId, userId), {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to deactivate user');
      }

      fetchUsers(selectedCustomerId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deactivate user');
    }
  };

  const startEdit = (user: User) => {
    setEditUserId(user.id);
    setFormData({
      email: user.email,
      password: '',
      full_name: user.full_name || '',
      role: user.role,
    });
    setShowCreateModal(true);
  };

  const startCreate = () => {
    setEditUserId(null);
    setFormData({
      email: '',
      password: '',
      full_name: '',
      role: 'user',
    });
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
                  <UserGroupIcon className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-neutral-900">User Management</h1>
                  <p className="text-sm text-neutral-600">Manage users across customers</p>
                </div>
              </div>
            </div>
            {selectedCustomerId && (
              <Button
                variant="primary"
                onClick={startCreate}
                className="flex items-center space-x-2"
              >
                <PlusIcon className="h-5 w-5" />
                <span>Create User</span>
              </Button>
            )}
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

        {/* Customer Selector */}
        <Card className="mb-6">
          <CardContent padding="md">
            {customers.length === 0 ? (
              <div className="text-center py-4">
                <BuildingOfficeIcon className="h-12 w-12 text-neutral-400 mx-auto mb-3" />
                <p className="text-neutral-600 mb-2">No customers found</p>
                <p className="text-sm text-neutral-500 mb-4">
                  You need to create a customer first before you can manage users.
                </p>
                <Button
                  variant="primary"
                  onClick={() => router.push('/tenant-admin/customers')}
                >
                  Go to Customers
                </Button>
              </div>
            ) : (
              <div className="flex items-center space-x-4">
                <label className="text-sm font-medium text-neutral-700">Select Customer:</label>
                <Select
                  value={selectedCustomerId?.toString() || ''}
                  onValueChange={(value) => setSelectedCustomerId(parseInt(value))}
                >
                  <SelectTrigger className="w-64">
                    <SelectValue placeholder="Select a customer" />
                  </SelectTrigger>
                  <SelectContent>
                    {customers.map((customer) => (
                      <SelectItem key={customer.id} value={customer.id.toString()}>
                        {customer.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </CardContent>
        </Card>

        {selectedCustomerId && (
          <>
            {usersLoading ? (
              <div className="text-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
                <p className="mt-4 text-neutral-600">Loading users...</p>
              </div>
            ) : (
              <Card>
                <CardHeader>
                  <h2 className="text-lg font-semibold text-neutral-900">Users</h2>
                </CardHeader>
                <CardContent>
                  {users.length === 0 ? (
                    <div className="text-center py-12">
                      <UserGroupIcon className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
                      <p className="text-neutral-600 mb-4">No users found</p>
                      <Button variant="primary" onClick={startCreate}>
                        Create First User
                      </Button>
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Email</TableHead>
                          <TableHead>Full Name</TableHead>
                          <TableHead>Role</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Created</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {users.map((user) => (
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
                              {user.created_at
                                ? new Date(user.created_at).toLocaleDateString()
                                : '-'}
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex items-center justify-end space-x-2">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => startEdit(user)}
                                >
                                  <PencilIcon className="h-4 w-4" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleDeleteUser(user.id)}
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
          </>
        )}

        {/* Create/Edit User Modal */}
        {showCreateModal && selectedCustomerId && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <Card className="max-w-md w-full">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-bold text-neutral-900">
                    {editUserId ? 'Edit User' : 'Create User'}
                  </h2>
                  <button
                    onClick={() => setShowCreateModal(false)}
                    className="text-neutral-500 hover:text-neutral-700"
                  >
                    ×
                  </button>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateUser} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Email *
                    </label>
                    <Input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      required
                      disabled={!!editUserId}
                      placeholder="user@example.com"
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

                  {!editUserId && (
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Password *
                      </label>
                      <Input
                        type="password"
                        value={formData.password}
                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                        required
                        placeholder="••••••••"
                      />
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Role *
                    </label>
                    <Select
                      value={formData.role}
                      onValueChange={(value) => setFormData({ ...formData, role: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="user">User</SelectItem>
                        <SelectItem value="viewer">Viewer</SelectItem>
                        <SelectItem value="admin">Tenant Admin</SelectItem>
                      </SelectContent>
                    </Select>
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
                      {editUserId ? 'Update User' : 'Create User'}
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

