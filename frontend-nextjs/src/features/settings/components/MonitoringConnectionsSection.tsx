'use client';

import { PlusIcon, LinkIcon, SignalIcon } from '@heroicons/react/24/outline';
import type { MonitoringConnection } from '../types';
import { useState, useEffect } from 'react';
import { apiConfig } from '@/lib/api-config';
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

  useEffect(() => {
    const fetchMonitoringTools = async () => {
      try {
        const res = await fetch(apiConfig.endpoints.connectors.monitoringConnectors());
        if (!res.ok) {
          throw new Error('Failed to fetch monitoring connectors');
        }
        const data = await res.json();
        setAvailableMonitoringTools(data.available_connectors || []);
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
        api_key: apiKey || undefined,
      };
      if (toolName === 'datadog') {
        body.application_key = applicationKey || undefined;
      }

      const url = isEdit
        ? `${apiConfig.endpoints
            .connectors
            .monitoringConnections()}/${editingId}`
        : apiConfig.endpoints.connectors.monitoringConnections();

      const method = isEdit ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(
          isEdit
            ? {
                // Update payload (only send fields we allow editing)
                api_base_url: apiBaseUrl || undefined,
                api_key: apiKey || undefined,
                application_key:
                  toolName === 'datadog'
                    ? applicationKey || undefined
                    : undefined,
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
  };

  const handleDelete = async (id: number) => {
    try {
      const res = await fetch(
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
                      {availableMonitoringTools.map((tool) => (
                        <option key={tool.type} value={tool.type}>
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

                <div className="flex items-center justify-end gap-3 pt-2">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowAdd(false);
                      setEditingId(null);
                      setApiBaseUrl('');
                      setApiKey('');
                      setApplicationKey('');
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


