'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/Card';
import { Table, TableHeader, TableRow, TableHead, TableCell, TableBody } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { PlusIcon, PencilIcon, TrashIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';
import { CustomRoleCreator } from './CustomRoleCreator';

interface Role {
  id: number;
  name: string;
  display_name: string | null;
  description: string | null;
  is_system_role: boolean;
  is_custom: boolean;
  tenant_id: number | null;
  is_global: boolean;
  is_active: boolean;
  permission_count: number;
  created_at: string;
}

interface RoleManagementProps {
  token: string;
  tenantId?: number;
}

export function RoleManagement({ token, tenantId }: RoleManagementProps) {
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingRoleId, setEditingRoleId] = useState<number | null>(null);

  useEffect(() => {
    fetchRoles();
  }, [tenantId]);

  const fetchRoles = async () => {
    setLoading(true);
    setError(null);
    try {
      const url = new URL(apiConfig.endpoints.roles.list());
      if (tenantId) {
        url.searchParams.set('tenant_id', tenantId.toString());
      }
      
      const response = await authFetch(url.toString(), {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setRoles(data);
      } else {
        throw new Error('Failed to fetch roles');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch roles');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (roleId: number) => {
    if (!confirm('Are you sure you want to delete this role? Users assigned to this role will need to be reassigned.')) {
      return;
    }

    try {
      const response = await authFetch(apiConfig.endpoints.roles.delete(roleId), {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        fetchRoles();
      } else {
        const errorData = await response.json();
        alert(errorData.detail || 'Failed to delete role');
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete role');
    }
  };

  if (showCreateModal) {
    return (
      <CustomRoleCreator
        token={token}
        tenantId={tenantId}
        onSuccess={() => {
          setShowCreateModal(false);
          fetchRoles();
        }}
        onCancel={() => setShowCreateModal(false)}
      />
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Role Management</CardTitle>
          <Button onClick={() => setShowCreateModal(true)}>
            <PlusIcon className="h-4 w-4 mr-2" />
            Create Custom Role
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="text-center py-8 text-gray-500">Loading roles...</div>
        ) : error ? (
          <div className="text-center py-8 text-red-600">{error}</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Display Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Permissions</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {roles.map(role => (
                <TableRow key={role.id}>
                  <TableCell className="font-mono text-sm">{role.name}</TableCell>
                  <TableCell>{role.display_name || role.name}</TableCell>
                  <TableCell>
                    <Badge variant={role.is_system_role ? 'default' : 'secondary'}>
                      {role.is_system_role ? 'System' : 'Custom'}
                    </Badge>
                  </TableCell>
                  <TableCell>{role.permission_count}</TableCell>
                  <TableCell>
                    <Badge variant={role.is_active ? 'success' : 'destructive'}>
                      {role.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex space-x-2">
                      {!role.is_system_role && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setEditingRoleId(role.id)}
                          >
                            <PencilIcon className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(role.id)}
                          >
                            <TrashIcon className="h-4 w-4" />
                          </Button>
                        </>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

