'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/Card';
import { PermissionSelector } from './PermissionSelector';
import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';

interface CustomRoleCreatorProps {
  token: string;
  tenantId?: number;
  onSuccess: () => void;
  onCancel: () => void;
}

export function CustomRoleCreator({ token, tenantId, onSuccess, onCancel }: CustomRoleCreatorProps) {
  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    description: '',
  });
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const roleData = {
        name: formData.name,
        display_name: formData.display_name || formData.name,
        description: formData.description,
        tenant_id: tenantId || null,
        permission_ids: selectedPermissionIds,
      };

      const response = await authFetch(apiConfig.endpoints.roles.create(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(roleData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create role');
      }

      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create role');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle>Create Custom Role</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                Role Name (unique identifier)
              </label>
              <Input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="custom_role_1"
                required
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">Lowercase, underscores only (e.g., custom_role_1)</p>
            </div>

            <div>
              <label htmlFor="display_name" className="block text-sm font-medium text-gray-700 mb-1">
                Display Name
              </label>
              <Input
                id="display_name"
                type="text"
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                placeholder="Custom Role 1"
                className="w-full"
              />
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Describe what this role can do..."
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <PermissionSelector
              selectedPermissionIds={selectedPermissionIds}
              onSelectionChange={setSelectedPermissionIds}
              token={token}
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div className="flex justify-end space-x-3">
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading || !formData.name || selectedPermissionIds.length === 0}>
              {loading ? 'Creating...' : 'Create Role'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}



