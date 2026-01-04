'use client';

import { PlusIcon, LinkIcon, SignalIcon } from '@heroicons/react/24/outline';
import type { MonitoringConnection } from '../types';
import { useState, useEffect } from 'react';
import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';
import { PencilIcon, TrashIcon } from '@heroicons/react/24/solid';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

interface MonitoringConnectionsSectionProps {
  connections: MonitoringConnection[];
  onRefresh: () => void;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
}

interface MonitoringToolInfo {
  type: string;
  name: string;
  description: string;
  status: string;
  webhook_supported?: boolean;
  api_supported?: boolean;
}

export function MonitoringConnectionsSection({
  connections,
  onRefresh,
  onSuccess,
  onError,
}: MonitoringConnectionsSectionProps) {
  const [availableMonitoringTools, setAvailableMonitoringTools] = useState<
    MonitoringToolInfo[]
  >([]);
  const [showAdd, setShowAdd] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [toolName, setToolName] = useState('datadog');
  const [apiBaseUrl, setApiBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [applicationKey, setApplicationKey] = useState('');
  // SolarWinds specific fields
  const [authMethod, setAuthMethod] = useState<'basic' | 'api_key' | 'oauth'>('basic');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');

  useEffect(() => {
    const fetchMonitoringTools = async () => {
      try {
        const res = await authFetch(apiConfig.endpoints.connectors.monitoringConnectors());
        if (!res.ok) {
          throw new Error('Failed to fetch monitoring connectors');
        }
        const data = await res.json();
        const connectors = data.available_connectors || [];
        // Remove duplicates by type (in case backend returns duplicates)
        const uniqueConnectors = connectors.filter((tool: MonitoringToolInfo, index: number, self: MonitoringToolInfo[]) =>
          index === self.findIndex((t: MonitoringToolInfo) => t.type === tool.type)
        );
        setAvailableMonitoringTools(uniqueConnectors);
      } catch (err) {
        console.error('Failed to fetch monitoring connectors:', err);
      }
    };
    fetchMonitoringTools();
  }, []);

  const handleCreate = async () => {
    try {
      setSaving(true);
      const isEdit = editingId !== null;

      const body: any = {
        tool_name: toolName,
        connection_type: 'api',
        api_base_url: apiBaseUrl || undefined,
      };
      
      // Datadog specific fields
      if (toolName === 'datadog') {
        body.api_key = apiKey || undefined;
        body.application_key = applicationKey || undefined;
      }
      // SolarWinds specific fields
      else if (toolName === 'solarwinds') {
        if (authMethod === 'basic') {
          body.api_username = username || undefined;
          body.api_password = password || undefined;
        } else if (authMethod === 'api_key') {
          body.api_key = apiKey || undefined;
        } else if (authMethod === 'oauth') {
          body.meta_data = {
            client_id: clientId || undefined,
            client_secret: clientSecret || undefined,
          };
        }
      }
      // Other tools
      else {
        body.api_key = apiKey || undefined;
      }

      const url = isEdit
        ? `${apiConfig.endpoints
            .connectors
            .monitoringConnections()}/${editingId}`
        : apiConfig.endpoints.connectors.monitoringConnections();

      const method = isEdit ? 'PUT' : 'POST';

      const res = await authFetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(
          isEdit
            ? {
                // Update payload (only send fields we allow editing)
                api_base_url: apiBaseUrl || undefined,
                ...(toolName === 'datadog' ? {
                  api_key: apiKey || undefined,
                  application_key: applicationKey || undefined,
                } : toolName === 'solarwinds' ? {
                  ...(authMethod === 'basic' ? {
                    api_username: username || undefined,
                    api_password: password || undefined,
                  } : authMethod === 'api_key' ? {
                    api_key: apiKey || undefined,
                  } : {
                    meta_data: {
                      client_id: clientId || undefined,
                      client_secret: clientSecret || undefined,
                    },
                  }),
                } : {
                  api_key: apiKey || undefined,
                }),
              }
            : body
        ),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(
          errData.detail ||
            errData.message ||
            `Failed to create monitoring connection (${res.status})`
        );
      }

      await res.json();
      setShowAdd(false);
      setEditingId(null);
      setApiBaseUrl('');
      setApiKey('');
      setApplicationKey('');
      setUsername('');
      setPassword('');
      setClientId('');
      setClientSecret('');
      setAuthMethod('basic');
      onRefresh();
      onSuccess(
        isEdit
          ? 'Monitoring connection updated successfully'
          : 'Monitoring connection added successfully'
      );
    } catch (err) {
      console.error('Failed to create monitoring connection:', err);
      onError(
        err instanceof Error
          ? err.message
          : 'Failed to create monitoring connection'
      );
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (conn: MonitoringConnection) => {
    setEditingId(conn.id);
    setShowAdd(true);
    setToolName(conn.tool_name);
    setApiBaseUrl(conn.api_base_url || '');
    // For security, we do not pre-fill keys; user must re-enter if changing
    setApiKey('');
    setApplicationKey('');
    setUsername('');
    setPassword('');
    setClientId('');
    setClientSecret('');
    setAuthMethod('basic');
  };

  const handleDelete = async (id: number) => {
    try {
      const res = await authFetch(
        `${apiConfig.endpoints.connectors.monitoringConnections()}/${id}`,
        {
          method: 'DELETE',
        }
      );
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(
          errData.detail ||
            errData.message ||
            `Failed to delete monitoring connection (${res.status})`
        );
      }
      onRefresh();
      onSuccess('Monitoring connection deleted successfully');
    } catch (err) {
      console.error('Failed to delete monitoring connection:', err);
      onError(
        err instanceof Error
          ? err.message
          : 'Failed to delete monitoring connection'
      );
    }
  };

  return (
    <Card variant="elevated">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-neutral-900 mb-1 flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary-100">
                <SignalIcon className="h-5 w-5 text-primary-600" />
              </div>
              Monitoring Connections
            </h3>
            <p className="text-sm text-neutral-600">
              Configure connections to monitoring tools (Datadog, Prometheus, Azure Monitor, Splunk) for two-way alert updates.
            </p>
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowAdd(true)}
            leftIcon={<PlusIcon className="h-5 w-5" />}
          >
            Add Monitoring Connection
          </Button>
        </div>
      </CardHeader>
      <CardContent padding="md">
        {connections.length === 0 ? (
          <div className="text-center py-12">
            <div className="mx-auto w-16 h-16 rounded-full bg-neutral-100 flex items-center justify-center mb-4">
              <LinkIcon className="h-8 w-8 text-neutral-400" />
            </div>
            <p className="text-neutral-700 font-medium mb-1">No monitoring connections configured</p>
            <p className="text-sm text-neutral-500">
              Click &quot;Add Monitoring Connection&quot; to connect Datadog and other monitoring tools.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {connections.map((conn) => (
              <Card key={conn.id} variant="default">
                <CardContent padding="md">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-3 flex-wrap">
                        <h4 className="font-semibold text-neutral-900 capitalize">
                          {conn.tool_name.replace('_', ' ')}
                        </h4>
                        <Badge variant={conn.is_active ? 'success' : 'secondary'} size="sm">
                          {conn.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                        <Badge variant="primary" size="sm">
                          {conn.connection_type}
                        </Badge>
                      </div>
                      {conn.api_base_url && (
                        <p className="text-sm text-neutral-600 mb-2">
                          API:{' '}
                          <code className="bg-neutral-100 px-2 py-1 rounded text-xs font-mono">
                            {conn.api_base_url}
                          </code>
                        </p>
                      )}
                      {conn.last_sync_status && (
                        <p className="text-xs text-neutral-500 mt-2">
                          Last sync status: {conn.last_sync_status}
                        </p>
                      )}
                      {conn.last_error && (
                        <p className="text-xs text-error-600 mt-2 font-medium">
                          Error: {conn.last_error}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => startEdit(conn)}
                        leftIcon={<PencilIcon className="h-4 w-4" />}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleDelete(conn.id)}
                        leftIcon={<TrashIcon className="h-4 w-4" />}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {showAdd && (
          <Card variant="outlined" className="mt-6 border-t-2 border-neutral-200">
            <CardHeader>
              <h4 className="text-lg font-semibold text-neutral-900">
                {editingId !== null ? 'Edit Monitoring Connection' : 'New Monitoring Connection'}
              </h4>
            </CardHeader>
            <CardContent padding="md">
              <div className="space-y-4">
                <div className="flex flex-col md:flex-row gap-4">
                  <div className="flex-1">
                    <label className="block text-sm font-semibold text-neutral-700 mb-2">
                      Monitoring Tool
                    </label>
                    <select
                      value={toolName}
                      onChange={(e) => setToolName(e.target.value)}
                      className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    >
                      {availableMonitoringTools.map((tool, index) => (
                        <option key={`${tool.type}-${index}`} value={tool.type}>
                          {tool.name}
                        </option>
                      ))}
                      {availableMonitoringTools.length === 0 && (
                        <option value="datadog">Datadog</option>
                      )}
                    </select>
                  </div>
                  <div className="flex-1">
                    <label className="block text-sm font-semibold text-neutral-700 mb-2">
                      API Base URL
                    </label>
                    <input
                      type="text"
                      value={apiBaseUrl}
                      onChange={(e) => setApiBaseUrl(e.target.value)}
                      placeholder={
                        toolName === 'datadog'
                          ? 'https://api.datadoghq.com'
                          : toolName === 'prometheus'
                          ? 'http://alertmanager:9093'
                          : toolName === 'azure_monitor'
                          ? 'https://management.azure.com'
                          : toolName === 'solarwinds'
                          ? 'https://your-instance.solarwinds.com'
                          : 'https://splunk.example.com:8089'
                      }
                      className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    />
                  </div>
                </div>

                {toolName === 'datadog' && (
                  <div className="flex flex-col md:flex-row gap-4">
                    <div className="flex-1">
                      <label className="block text-sm font-semibold text-neutral-700 mb-2">
                        API Key
                      </label>
                      <input
                        type="password"
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="block text-sm font-semibold text-neutral-700 mb-2">
                        Application Key
                      </label>
                      <input
                        type="password"
                        value={applicationKey}
                        onChange={(e) => setApplicationKey(e.target.value)}
                        className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                      />
                    </div>
                  </div>
                )}

                {toolName === 'solarwinds' && (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-semibold text-neutral-700 mb-2">
                        Authentication Method
                      </label>
                      <select
                        value={authMethod}
                        onChange={(e) => setAuthMethod(e.target.value as 'basic' | 'api_key' | 'oauth')}
                        className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                      >
                        <option value="basic">Basic Auth (Username/Password)</option>
                        <option value="api_key">API Key</option>
                        <option value="oauth">OAuth 2.0</option>
                      </select>
                    </div>

                    {authMethod === 'basic' && (
                      <div className="flex flex-col md:flex-row gap-4">
                        <div className="flex-1">
                          <label className="block text-sm font-semibold text-neutral-700 mb-2">
                            Username
                          </label>
                          <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                          />
                        </div>
                        <div className="flex-1">
                          <label className="block text-sm font-semibold text-neutral-700 mb-2">
                            Password
                          </label>
                          <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                          />
                        </div>
                      </div>
                    )}

                    {authMethod === 'api_key' && (
                      <div>
                        <label className="block text-sm font-semibold text-neutral-700 mb-2">
                          API Key
                        </label>
                        <input
                          type="password"
                          value={apiKey}
                          onChange={(e) => setApiKey(e.target.value)}
                          className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                        />
                      </div>
                    )}

                    {authMethod === 'oauth' && (
                      <div className="flex flex-col md:flex-row gap-4">
                        <div className="flex-1">
                          <label className="block text-sm font-semibold text-neutral-700 mb-2">
                            Client ID
                          </label>
                          <input
                            type="text"
                            value={clientId}
                            onChange={(e) => setClientId(e.target.value)}
                            className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                          />
                        </div>
                        <div className="flex-1">
                          <label className="block text-sm font-semibold text-neutral-700 mb-2">
                            Client Secret
                          </label>
                          <input
                            type="password"
                            value={clientSecret}
                            onChange={(e) => setClientSecret(e.target.value)}
                            className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {toolName !== 'datadog' && toolName !== 'solarwinds' && (
                  <div>
                    <label className="block text-sm font-semibold text-neutral-700 mb-2">
                      API Key
                    </label>
                    <input
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    />
                  </div>
                )}

                <div className="flex items-center justify-end gap-3 pt-2">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowAdd(false);
                      setEditingId(null);
                      setApiBaseUrl('');
                      setApiKey('');
                      setApplicationKey('');
                      setUsername('');
                      setPassword('');
                      setClientId('');
                      setClientSecret('');
                      setAuthMethod('basic');
                    }}
                    disabled={saving}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="primary"
                    onClick={handleCreate}
                    disabled={saving}
                    isLoading={saving}
                  >
                    {saving
                      ? 'Saving...'
                      : editingId !== null
                      ? 'Update Connection'
                      : 'Save Connection'}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </CardContent>
    </Card>
  );
}


