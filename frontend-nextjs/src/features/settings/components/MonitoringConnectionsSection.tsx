'use client';

import { PlusIcon, LinkIcon, SignalIcon } from '@heroicons/react/24/outline';
import type { MonitoringConnection } from '../types';
import { useState, useEffect } from 'react';
import { apiConfig } from '@/lib/api-config';
import { PencilIcon, TrashIcon } from '@heroicons/react/24/solid';

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

const statusColor = (isActive: boolean) =>
  isActive ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800';

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
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm mb-6">
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-1 flex items-center gap-2">
              <SignalIcon className="h-5 w-5 text-blue-600" />
              Monitoring Connections
            </h3>
            <p className="text-sm text-gray-600">
              Configure connections to monitoring tools (Datadog, Prometheus, Azure Monitor, Splunk) for two-way alert updates.
            </p>
          </div>
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <PlusIcon className="h-5 w-5" />
            Add Monitoring Connection
          </button>
        </div>

        {connections.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <LinkIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p>No monitoring connections configured</p>
            <p className="text-sm mt-2">
              Click &quot;Add Monitoring Connection&quot; to connect Datadog and other monitoring tools.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {connections.map((conn) => (
              <div
                key={conn.id}
                className="border border-gray-200 rounded-lg p-4 flex items-start justify-between"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h4 className="font-medium text-gray-900 capitalize">
                      {conn.tool_name.replace('_', ' ')}
                    </h4>
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${statusColor(
                        conn.is_active
                      )}`}
                    >
                      {conn.is_active ? 'Active' : 'Inactive'}
                    </span>
                    <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {conn.connection_type}
                    </span>
                  </div>
                  {conn.api_base_url && (
                    <p className="text-sm text-gray-600 mb-1">
                      API:{' '}
                      <code className="bg-gray-100 px-2 py-1 rounded text-xs">
                        {conn.api_base_url}
                      </code>
                    </p>
                  )}
                  {conn.last_sync_status && (
                    <p className="text-xs text-gray-500 mt-1">
                      Last sync status: {conn.last_sync_status}
                    </p>
                  )}
                  {conn.last_error && (
                    <p className="text-xs text-red-600 mt-1">
                      Error: {conn.last_error}
                    </p>
                  )}
                </div>
                <div className="flex flex-col items-end gap-2 ml-4">
                  <button
                    type="button"
                    onClick={() => startEdit(conn)}
                    className="inline-flex items-center gap-1 px-3 py-1 text-xs rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50"
                  >
                    <PencilIcon className="h-4 w-4" />
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(conn.id)}
                    className="inline-flex items-center gap-1 px-3 py-1 text-xs rounded-md border border-red-300 text-red-700 hover:bg-red-50"
                  >
                    <TrashIcon className="h-4 w-4" />
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {showAdd && (
          <div className="mt-6 border-t border-gray-200 pt-4">
            <h4 className="text-md font-semibold text-gray-900 mb-3">
              New Monitoring Connection
            </h4>
            <div className="space-y-4">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Monitoring Tool
                  </label>
                  <select
                    value={toolName}
                    onChange={(e) => setToolName(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              {toolName === 'datadog' && (
                <div className="flex flex-col md:flex-row gap-4">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      API Key
                    </label>
                    <input
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Application Key
                    </label>
                    <input
                      type="password"
                      value={applicationKey}
                      onChange={(e) => setApplicationKey(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>
              )}

              <div className="flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowAdd(false);
                    setEditingId(null);
                    setApiBaseUrl('');
                    setApiKey('');
                    setApplicationKey('');
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleCreate}
                  disabled={saving}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {saving
                    ? 'Saving...'
                    : editingId !== null
                    ? 'Update Connection'
                    : 'Save Connection'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


