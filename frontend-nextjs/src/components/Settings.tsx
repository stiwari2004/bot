'use client';

import { useState, useEffect } from 'react';
import {
  Cog6ToothIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  PlusIcon,
  XMarkIcon,
  LinkIcon,
  WrenchScrewdriverIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';

interface ExecutionMode {
  mode: string;
  description: string;
}

interface TicketingConnection {
  id: number;
  tool_name: string;
  connection_type: string;
  is_active: boolean;
  webhook_url: string | null;
  api_base_url: string | null;
  last_sync_at: string | null;
  last_sync_status: string | null;
  last_error: string | null;
}

interface TicketingTool {
  name: string;
  display_name: string;
  connection_types: string[];
  description: string;
}

export function Settings() {
  const [executionMode, setExecutionMode] = useState<ExecutionMode | null>(null);
  const [ticketingConnections, setTicketingConnections] = useState<TicketingConnection[]>([]);
  const [availableTools, setAvailableTools] = useState<TicketingTool[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showAddConnection, setShowAddConnection] = useState(false);
  const [selectedTool, setSelectedTool] = useState<string>('');

  useEffect(() => {
    fetchExecutionMode();
    fetchTicketingConnections();
    fetchAvailableTools();
  }, []);

  const fetchExecutionMode = async () => {
    try {
      const response = await fetch(apiConfig.endpoints.settings.executionMode());
      if (!response.ok) {
        throw new Error('Failed to fetch execution mode');
      }
      const data = await response.json();
      setExecutionMode(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch execution mode');
    } finally {
      setLoading(false);
    }
  };

  const fetchTicketingConnections = async () => {
    try {
      const response = await fetch(apiConfig.endpoints.settings.ticketingConnections());
      if (!response.ok) {
        throw new Error('Failed to fetch ticketing connections');
      }
      const data = await response.json();
      setTicketingConnections(data.connections || []);
    } catch (err) {
      console.error('Failed to fetch ticketing connections:', err);
    }
  };

  const fetchAvailableTools = async () => {
    try {
      const response = await fetch(apiConfig.endpoints.settings.ticketingTools());
      if (!response.ok) {
        throw new Error('Failed to fetch available tools');
      }
      const data = await response.json();
      setAvailableTools(data.tools || []);
    } catch (err) {
      console.error('Failed to fetch available tools:', err);
    }
  };

  const handleModeChange = async (mode: 'hil' | 'auto') => {
    if (executionMode?.mode === mode) return;

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch(apiConfig.endpoints.settings.executionMode(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mode }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update execution mode');
      }

      const data = await response.json();
      setExecutionMode(data);
      setSuccess(`Execution mode updated to ${mode === 'hil' ? 'Human-in-the-Loop' : 'Auto'}`);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update execution mode');
      console.error('Mode change error:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async (connectionId: number) => {
    try {
      const response = await fetch(
        apiConfig.endpoints.settings.ticketingConnectionTest(connectionId),
        {
          method: 'POST',
        }
      );

      if (!response.ok) {
        throw new Error('Connection test failed');
      }

      setSuccess('Connection test successful');
      setTimeout(() => setSuccess(null), 3000);
      await fetchTicketingConnections(); // Refresh connections
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection test failed');
    }
  };

  const handleToggleConnection = async (connectionId: number, isActive: boolean) => {
    try {
      const response = await fetch(
        apiConfig.endpoints.settings.ticketingConnection(connectionId),
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ is_active: !isActive }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to update connection');
      }

      setSuccess(`Connection ${!isActive ? 'activated' : 'deactivated'}`);
      setTimeout(() => setSuccess(null), 3000);
      await fetchTicketingConnections();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update connection');
    }
  };

  const getStatusColor = (status: string | null) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-gray-600">Loading settings...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2 flex items-center">
          <Cog6ToothIcon className="h-7 w-7 mr-2 text-blue-600" />
          Settings & Connections
        </h2>
        <p className="text-gray-600">Configure system behavior and connect to ticketing tools</p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />
            <p className="text-red-800 font-medium">Error</p>
          </div>
          <p className="text-red-700 mt-2 text-sm">{error}</p>
        </div>
      )}

      {success && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center gap-2">
            <CheckCircleIcon className="h-5 w-5 text-green-600" />
            <p className="text-green-800 font-medium">{success}</p>
          </div>
        </div>
      )}

      {/* Execution Mode Setting */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm mb-6">
        <div className="p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Execution Mode
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Control how runbooks are executed when matched to tickets
            </p>
          </div>

          <div className="space-y-4">
            <div
              className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
                executionMode?.mode === 'hil'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => handleModeChange('hil')}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <input
                      type="radio"
                      name="execution-mode"
                      checked={executionMode?.mode === 'hil'}
                      onChange={() => handleModeChange('hil')}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500"
                      disabled={saving}
                    />
                    <h4 className="font-medium text-gray-900">
                      Human-in-the-Loop (HIL) Mode
                    </h4>
                  </div>
                  <p className="text-sm text-gray-600 ml-7">
                    Always require manual approval before executing any runbook step.
                  </p>
                </div>
                {executionMode?.mode === 'hil' && (
                  <CheckCircleIcon className="h-6 w-6 text-blue-600 flex-shrink-0 ml-4" />
                )}
              </div>
            </div>

            <div
              className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
                executionMode?.mode === 'auto'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => handleModeChange('auto')}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <input
                      type="radio"
                      name="execution-mode"
                      checked={executionMode?.mode === 'auto'}
                      onChange={() => handleModeChange('auto')}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500"
                      disabled={saving}
                    />
                    <h4 className="font-medium text-gray-900">
                      Auto Mode
                    </h4>
                  </div>
                  <p className="text-sm text-gray-600 ml-7">
                    Automatically execute runbooks when confidence score is ≥0.8.
                  </p>
                </div>
                {executionMode?.mode === 'auto' && (
                  <CheckCircleIcon className="h-6 w-6 text-blue-600 flex-shrink-0 ml-4" />
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Ticketing Tool Connections */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm mb-6">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Ticketing Tool Connections
              </h3>
              <p className="text-sm text-gray-600">
                Connect to external ticketing tools to receive tickets automatically
              </p>
            </div>
            <button
              onClick={() => setShowAddConnection(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <PlusIcon className="h-5 w-5" />
              Add Connection
            </button>
          </div>

          {ticketingConnections.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <LinkIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p>No ticketing tool connections configured</p>
              <p className="text-sm mt-2">Click "Add Connection" to connect to ServiceNow, Zendesk, Jira, etc.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {ticketingConnections.map((connection) => (
                <div
                  key={connection.id}
                  className="border border-gray-200 rounded-lg p-4"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h4 className="font-medium text-gray-900 capitalize">
                          {connection.tool_name.replace('_', ' ')}
                        </h4>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          connection.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}>
                          {connection.is_active ? 'Active' : 'Inactive'}
                        </span>
                        <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {connection.connection_type}
                        </span>
                        {connection.last_sync_status && (
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(connection.last_sync_status)}`}>
                            {connection.last_sync_status}
                          </span>
                        )}
                      </div>
                      {connection.webhook_url && (
                        <p className="text-sm text-gray-600 mb-1">
                          Webhook: <code className="bg-gray-100 px-2 py-1 rounded text-xs">{connection.webhook_url}</code>
                        </p>
                      )}
                      {connection.api_base_url && (
                        <p className="text-sm text-gray-600 mb-1">
                          API: <code className="bg-gray-100 px-2 py-1 rounded text-xs">{connection.api_base_url}</code>
                        </p>
                      )}
                      {connection.last_sync_at && (
                        <p className="text-xs text-gray-500 mt-2">
                          Last sync: {new Date(connection.last_sync_at).toLocaleString()}
                        </p>
                      )}
                      {connection.last_error && (
                        <p className="text-xs text-red-600 mt-1">
                          Error: {connection.last_error}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      <button
                        onClick={() => handleTestConnection(connection.id)}
                        className="px-3 py-1 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                        title="Test Connection"
                      >
                        Test
                      </button>
                      <button
                        onClick={() => handleToggleConnection(connection.id, connection.is_active)}
                        className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                          connection.is_active
                            ? 'bg-red-100 text-red-800 hover:bg-red-200'
                            : 'bg-green-100 text-green-800 hover:bg-green-200'
                        }`}
                      >
                        {connection.is_active ? 'Disable' : 'Enable'}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Add Connection Modal */}
      {showAddConnection && (
        <AddConnectionModal
          availableTools={availableTools}
          onClose={() => setShowAddConnection(false)}
          onSuccess={() => {
            setShowAddConnection(false);
            fetchTicketingConnections();
            setSuccess('Connection added successfully');
            setTimeout(() => setSuccess(null), 3000);
          }}
        />
      )}
    </div>
  );
}

interface AddConnectionModalProps {
  availableTools: TicketingTool[];
  onClose: () => void;
  onSuccess: () => void;
}

function AddConnectionModal({ availableTools, onClose, onSuccess }: AddConnectionModalProps) {
  const [selectedTool, setSelectedTool] = useState('');
  const [connectionType, setConnectionType] = useState('webhook');
  const [webhookUrl, setWebhookUrl] = useState('');
  const [apiBaseUrl, setApiBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [apiUsername, setApiUsername] = useState('');
  const [apiPassword, setApiPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Prevent body scroll when modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  const selectedToolInfo = availableTools.find(t => t.name === selectedTool);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTool) {
      setError('Please select a ticketing tool');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const payload: any = {
        tool_name: selectedTool,
        connection_type: connectionType,
      };

      if (connectionType === 'webhook') {
        payload.webhook_url =
          webhookUrl || apiConfig.endpoints.tickets.webhook(selectedTool);
      } else {
        payload.api_base_url = apiBaseUrl;
        payload.api_key = apiKey;
        payload.api_username = apiUsername;
        payload.api_password = apiPassword;
      }

      const response = await fetch(apiConfig.endpoints.settings.ticketingConnections(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create connection');
      }

      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create connection');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] overflow-y-auto" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0 }}>
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={onClose}
        />
        
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full z-10 relative">
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold text-gray-900">Add Ticketing Tool Connection</h3>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-500"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Ticketing Tool *
                </label>
                <select
                  value={selectedTool}
                  onChange={(e) => setSelectedTool(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                  required
                >
                  <option value="">Select a tool...</option>
                  {availableTools.map((tool) => (
                    <option key={tool.name} value={tool.name}>
                      {tool.display_name} - {tool.description}
                    </option>
                  ))}
                </select>
              </div>

              {selectedToolInfo && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Connection Type *
                  </label>
                  <select
                    value={connectionType}
                    onChange={(e) => setConnectionType(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                    required
                  >
                    {selectedToolInfo.connection_types.map((type) => (
                      <option key={type} value={type}>
                        {type === 'webhook' ? 'Webhook (Recommended)' : type === 'api_poll' ? 'API Polling' : type}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {connectionType === 'webhook' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Webhook URL
                  </label>
                  <input
                    type="text"
                    value={webhookUrl}
                    onChange={(e) => setWebhookUrl(e.target.value)}
                    placeholder={
                      selectedTool
                        ? apiConfig.endpoints.tickets.webhook(selectedTool)
                        : ''
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Configure this URL in your ticketing tool's webhook settings
                  </p>
                </div>
              )}

              {connectionType === 'api_poll' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      API Base URL *
                    </label>
                    <input
                      type="text"
                      value={apiBaseUrl}
                      onChange={(e) => setApiBaseUrl(e.target.value)}
                      placeholder="https://your-instance.service-now.com"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      API Key / Username
                    </label>
                    <input
                      type="text"
                      value={apiUsername}
                      onChange={(e) => setApiUsername(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      API Password / Token
                    </label>
                    <input
                      type="password"
                      value={apiPassword}
                      onChange={(e) => setApiPassword(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                </>
              )}

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving || !selectedTool}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {saving ? 'Creating...' : 'Create Connection'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
