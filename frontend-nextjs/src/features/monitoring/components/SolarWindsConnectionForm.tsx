'use client';

import { useState } from 'react';
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/Select';
import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';

interface SolarWindsConnectionFormProps {
  token: string;
  tenantId: number;
  onSuccess: () => void;
  onCancel: () => void;
  existingConnection?: {
    id: number;
    api_base_url: string;
    api_username?: string;
    api_key?: string;
  };
}

export function SolarWindsConnectionForm({
  token,
  tenantId,
  onSuccess,
  onCancel,
  existingConnection
}: SolarWindsConnectionFormProps) {
  const [formData, setFormData] = useState({
    api_base_url: existingConnection?.api_base_url || '',
    auth_method: 'basic' as 'basic' | 'api_key' | 'oauth',
    username: existingConnection?.api_username || '',
    password: '',
    api_key: existingConnection?.api_key || '',
    client_id: '',
    client_secret: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

  const handleTest = async () => {
    setTesting(true);
    setError(null);

    try {
      // Create temporary connection for testing
      const testPayload = {
        tool_name: 'solarwinds',
        connection_type: 'api',
        api_base_url: formData.api_base_url,
        api_username: formData.auth_method === 'basic' ? formData.username : undefined,
        api_password: formData.auth_method === 'basic' ? formData.password : undefined,
        api_key: formData.auth_method === 'api_key' ? formData.api_key : undefined,
        meta_data: formData.auth_method === 'oauth' ? {
          client_id: formData.client_id,
          client_secret: formData.client_secret,
        } : undefined,
      };

      const response = await authFetch(apiConfig.endpoints.settings.monitoringConnections(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(testPayload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Connection test failed');
      }

      const connection = await response.json();
      
      // Test the connection
      const testResponse = await authFetch(
        apiConfig.endpoints.settings.testMonitoringConnection(connection.id),
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      const testResult = await testResponse.json();

      if (testResult.success) {
        alert('✅ Connection test successful!');
        // Delete test connection
        await authFetch(
          apiConfig.endpoints.settings.deleteMonitoringConnection(connection.id),
          {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          }
        );
      } else {
        throw new Error(testResult.message || 'Connection test failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection test failed');
    } finally {
      setTesting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload: any = {
        tool_name: 'solarwinds',
        connection_type: 'api',
        api_base_url: formData.api_base_url,
      };

      const meta: any = {};
      
      if (formData.auth_method === 'basic') {
        payload.api_username = formData.username;
        payload.api_password = formData.password;
      } else if (formData.auth_method === 'api_key') {
        payload.api_key = formData.api_key;
      } else if (formData.auth_method === 'oauth') {
        meta.client_id = formData.client_id;
        meta.client_secret = formData.client_secret;
      }

      if (Object.keys(meta).length > 0) {
        payload.meta_data = meta;
      }

      const url = existingConnection
        ? apiConfig.endpoints.settings.monitoringConnection(existingConnection.id)
        : apiConfig.endpoints.settings.monitoringConnections();
      
      const method = existingConnection ? 'PUT' : 'POST';

      const response = await authFetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save connection');
      }

      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save connection');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>{existingConnection ? 'Edit' : 'Add'} SolarWinds Connection</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              SolarWinds Instance URL *
            </label>
            <Input
              type="url"
              value={formData.api_base_url}
              onChange={(e) => setFormData({ ...formData, api_base_url: e.target.value })}
              placeholder="https://your-instance.solarwinds.com"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Your SolarWinds Orion instance URL
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Authentication Method *
            </label>
            <Select
              value={formData.auth_method}
              onValueChange={(value: string) => {
                if (value === 'basic' || value === 'api_key' || value === 'oauth') {
                  setFormData({ ...formData, auth_method: value as 'basic' | 'api_key' | 'oauth' });
                }
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="basic">Basic Auth (Username/Password)</SelectItem>
                <SelectItem value="api_key">API Key</SelectItem>
                <SelectItem value="oauth">OAuth 2.0</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {formData.auth_method === 'basic' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Username *
                </label>
                <Input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Password *
                </label>
                <Input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required={!existingConnection}
                />
                {existingConnection && (
                  <p className="text-xs text-gray-500 mt-1">
                    Leave blank to keep current password
                  </p>
                )}
              </div>
            </>
          )}

          {formData.auth_method === 'api_key' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                API Key *
              </label>
              <Input
                type="password"
                value={formData.api_key}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                required={!existingConnection}
              />
            </div>
          )}

          {formData.auth_method === 'oauth' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Client ID *
                </label>
                <Input
                  type="text"
                  value={formData.client_id}
                  onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Client Secret *
                </label>
                <Input
                  type="password"
                  value={formData.client_secret}
                  onChange={(e) => setFormData({ ...formData, client_secret: e.target.value })}
                  required
                />
              </div>
            </>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div className="flex justify-end space-x-3">
            <Button type="button" variant="outline" onClick={handleTest} disabled={testing || loading}>
              {testing ? 'Testing...' : 'Test Connection'}
            </Button>
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading || testing}>
              {loading ? 'Saving...' : existingConnection ? 'Update' : 'Create'} Connection
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

