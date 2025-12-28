'use client';

import { useState, useEffect } from 'react';
import { Checkbox } from '@/components/ui/Checkbox';
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/Card';
import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';

interface Permission {
  id: number;
  name: string;
  action: string;
  resource: string;
  description: string | null;
  is_active: boolean;
}

interface PermissionSelectorProps {
  selectedPermissionIds: number[];
  onSelectionChange: (permissionIds: number[]) => void;
  token: string;
}

export function PermissionSelector({ selectedPermissionIds, onSelectionChange, token }: PermissionSelectorProps) {
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);
  const [groupedPermissions, setGroupedPermissions] = useState<Record<string, Permission[]>>({});

  useEffect(() => {
    fetchPermissions();
  }, []);

  useEffect(() => {
    // Group permissions by resource
    const grouped: Record<string, Permission[]> = {};
    permissions.forEach(perm => {
      if (!grouped[perm.resource]) {
        grouped[perm.resource] = [];
      }
      grouped[perm.resource].push(perm);
    });
    setGroupedPermissions(grouped);
  }, [permissions]);

  const fetchPermissions = async () => {
    try {
      const response = await authFetch(apiConfig.endpoints.permissions.list(), {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setPermissions(data.filter((p: Permission) => p.is_active));
      }
    } catch (error) {
      console.error('Failed to fetch permissions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePermissionToggle = (permissionId: number) => {
    const newSelection = selectedPermissionIds.includes(permissionId)
      ? selectedPermissionIds.filter(id => id !== permissionId)
      : [...selectedPermissionIds, permissionId];
    onSelectionChange(newSelection);
  };

  const handleResourceToggle = (resource: string) => {
    const resourcePerms = groupedPermissions[resource] || [];
    const resourcePermIds = resourcePerms.map(p => p.id);
    const allSelected = resourcePermIds.every(id => selectedPermissionIds.includes(id));
    
    if (allSelected) {
      // Deselect all
      onSelectionChange(selectedPermissionIds.filter(id => !resourcePermIds.includes(id)));
    } else {
      // Select all
      const newSelection = [...new Set([...selectedPermissionIds, ...resourcePermIds])];
      onSelectionChange(newSelection);
    }
  };

  if (loading) {
    return <div className="text-sm text-gray-500">Loading permissions...</div>;
  }

  const resources = Object.keys(groupedPermissions).sort();

  return (
    <div className="space-y-4">
      <div className="text-sm font-medium text-gray-700">Select Permissions</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {resources.map(resource => {
          const resourcePerms = groupedPermissions[resource];
          const resourcePermIds = resourcePerms.map(p => p.id);
          const allSelected = resourcePermIds.every(id => selectedPermissionIds.includes(id));
          const someSelected = resourcePermIds.some(id => selectedPermissionIds.includes(id));

          return (
            <Card key={resource} className="border border-gray-200">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-semibold capitalize">{resource}</CardTitle>
                  <button
                    type="button"
                    onClick={() => handleResourceToggle(resource)}
                    className="text-xs text-blue-600 hover:text-blue-800"
                  >
                    {allSelected ? 'Deselect All' : 'Select All'}
                  </button>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                {resourcePerms.map(perm => (
                  <div key={perm.id} className="flex items-start space-x-2">
                    <Checkbox
                      id={`perm-${perm.id}`}
                      checked={selectedPermissionIds.includes(perm.id)}
                      onCheckedChange={() => handlePermissionToggle(perm.id)}
                    />
                    <label
                      htmlFor={`perm-${perm.id}`}
                      className="text-sm text-gray-700 cursor-pointer flex-1"
                    >
                      <div className="font-medium">{perm.action}</div>
                      {perm.description && (
                        <div className="text-xs text-gray-500">{perm.description}</div>
                      )}
                    </label>
                  </div>
                ))}
              </CardContent>
            </Card>
          );
        })}
      </div>
      <div className="text-xs text-gray-500">
        Selected: {selectedPermissionIds.length} of {permissions.length} permissions
      </div>
    </div>
  );
}

