'use client';

import { useState, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import type { TicketingTool } from '../types';

interface AddConnectionModalProps {
  availableTools: TicketingTool[];
  onClose: () => void;
  onSuccess: () => void;
}

export function AddConnectionModal({ availableTools, onClose, onSuccess }: AddConnectionModalProps) {
  const [selectedTool, setSelectedTool] = useState('');
  const [connectionType, setConnectionType] = useState('webhook');
  const [webhookUrl, setWebhookUrl] = useState('');
  const [apiBaseUrl, setApiBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [apiUsername, setApiUsername] = useState('');
  const [apiPassword, setApiPassword] = useState('');
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [redirectUri, setRedirectUri] = useState('http://localhost:8000/oauth/callback');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        
        if (selectedTool === 'zoho' || selectedTool === 'manageengine') {
          const meta: any = {};
          if (clientId) meta.client_id = clientId;
          if (clientSecret) meta.client_secret = clientSecret;
          if (redirectUri) meta.redirect_uri = redirectUri;
          if (Object.keys(meta).length > 0) {
            payload.meta_data = meta;
          }
        } else {
          payload.api_key = apiKey;
          payload.api_username = apiUsername;
          payload.api_password = apiPassword;
        }
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
                      placeholder={selectedTool === 'manageengine' ? 'https://sdpondemand.manageengine.in' : 'https://your-instance.service-now.com'}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                      required
                    />
                  </div>
                  
                  {(selectedTool === 'zoho' || selectedTool === 'manageengine') ? (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Client ID *
                        </label>
                        <input
                          type="text"
                          value={clientId}
                          onChange={(e) => setClientId(e.target.value)}
                          placeholder={`Your ${selectedTool === 'zoho' ? 'Zoho' : 'ManageEngine'} OAuth Client ID`}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                          required
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Register your app at {selectedTool === 'zoho' ? 'https://api-console.zoho.com' : 'https://api-console.zoho.in'} to get Client ID and Secret
                        </p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Client Secret *
                        </label>
                        <input
                          type="password"
                          value={clientSecret}
                          onChange={(e) => setClientSecret(e.target.value)}
                          placeholder={`Your ${selectedTool === 'zoho' ? 'Zoho' : 'ManageEngine'} OAuth Client Secret`}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Redirect URI
                        </label>
                        <input
                          type="text"
                          value={redirectUri}
                          onChange={(e) => setRedirectUri(e.target.value)}
                          placeholder="http://localhost:8000/oauth/callback"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Configure this redirect URI in your OAuth app settings
                        </p>
                      </div>
                    </>
                  ) : (
                    <>
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

