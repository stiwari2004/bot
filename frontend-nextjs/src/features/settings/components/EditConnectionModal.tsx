'use client';

import { useState, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import type { TicketingConnection, TicketingTool } from '../types';

interface EditConnectionModalProps {
  connection: TicketingConnection;
  availableTools: TicketingTool[];
  onClose: () => void;
  onSuccess: () => void;
}

export function EditConnectionModal({ connection, availableTools, onClose, onSuccess }: EditConnectionModalProps) {
  const [apiBaseUrl, setApiBaseUrl] = useState(connection.api_base_url || '');
  const [apiKey, setApiKey] = useState(connection.api_key || '');
  const [apiSecret, setApiSecret] = useState('');
  const [apiUsername, setApiUsername] = useState(connection.api_username || '');
  const [apiPassword, setApiPassword] = useState('');
  const [authMethod, setAuthMethod] = useState<'api_key' | 'username'>('api_key');
  const [syncIntervalMinutes, setSyncIntervalMinutes] = useState(connection.sync_interval_minutes || 5);
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [redirectUri, setRedirectUri] = useState('http://localhost:8000/oauth/callback');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (connection.meta_data) {
      try {
        const meta = typeof connection.meta_data === 'string' 
          ? JSON.parse(connection.meta_data) 
          : connection.meta_data;
        
        if (connection.tool_name === 'zoho' || connection.tool_name === 'manageengine') {
          setClientId(meta.client_id || '');
          setClientSecret(meta.client_secret ? '••••••••' : '');
          setRedirectUri(meta.redirect_uri || 'http://localhost:8000/oauth/callback');
        } else {
          setApiSecret(meta.api_secret ? '••••••••' : '');
          if (meta.api_key || connection.api_key) {
            setAuthMethod('api_key');
          } else if (meta.api_username || connection.api_username) {
            setAuthMethod('username');
          }
        }
      } catch (e) {
        // Ignore parse errors
      }
    }
  }, [connection]);

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      const payload: any = {
        api_base_url: apiBaseUrl,
        sync_interval_minutes: syncIntervalMinutes,
      };

      if (connection.tool_name === 'zoho' || connection.tool_name === 'manageengine') {
        const meta: any = {};
        if (clientId) meta.client_id = clientId;
        if (clientSecret && clientSecret !== '••••••••') {
          meta.client_secret = clientSecret;
        }
        if (redirectUri) meta.redirect_uri = redirectUri;
        if (Object.keys(meta).length > 0) {
          payload.meta_data = meta;
        }
      } else {
        const meta: any = {};
        if (authMethod === 'api_key') {
          if (apiKey) payload.api_key = apiKey;
          if (apiSecret && apiSecret !== '••••••••') {
            meta.api_secret = apiSecret;
          }
        } else {
          if (apiUsername) payload.api_username = apiUsername;
          if (apiPassword) payload.api_password = apiPassword;
        }
        if (Object.keys(meta).length > 0) {
          payload.meta_data = meta;
        }
      }

      const response = await fetch(
        apiConfig.endpoints.settings.ticketingConnection(connection.id),
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update connection');
      }

      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update connection');
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
              <h3 className="text-xl font-semibold text-gray-900">Edit Connection - {connection.tool_name}</h3>
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
                  API Base URL *
                </label>
                <input
                  type="text"
                  value={apiBaseUrl}
                  onChange={(e) => setApiBaseUrl(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Sync Interval (minutes)
                </label>
                <input
                  type="number"
                  value={syncIntervalMinutes}
                  onChange={(e) => setSyncIntervalMinutes(parseInt(e.target.value) || 5)}
                  min="1"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                />
              </div>

              {(connection.tool_name === 'zoho' || connection.tool_name === 'manageengine') ? (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Client ID
                    </label>
                    <input
                      type="text"
                      value={clientId}
                      onChange={(e) => setClientId(e.target.value)}
                      placeholder={`Your ${connection.tool_name === 'zoho' ? 'Zoho' : 'ManageEngine'} OAuth Client ID`}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Client Secret
                    </label>
                    <input
                      type="password"
                      value={clientSecret}
                      onChange={(e) => setClientSecret(e.target.value)}
                      placeholder="Leave blank to keep existing"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Leave blank to keep existing secret
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Redirect URI
                    </label>
                    <input
                      type="text"
                      value={redirectUri}
                      onChange={(e) => setRedirectUri(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Authentication Method *
                    </label>
                    <select
                      value={authMethod}
                      onChange={(e) => setAuthMethod(e.target.value as 'api_key' | 'username')}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                    >
                      <option value="api_key">API Key / Secret</option>
                      <option value="username">Username / Password</option>
                    </select>
                  </div>
                  {authMethod === 'api_key' ? (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          API Key
                        </label>
                        <input
                          type="text"
                          value={apiKey}
                          onChange={(e) => setApiKey(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          API Secret
                        </label>
                        <input
                          type="password"
                          value={apiSecret}
                          onChange={(e) => setApiSecret(e.target.value)}
                          placeholder="Leave blank to keep existing"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Leave blank to keep existing secret
                        </p>
                      </div>
                    </>
                  ) : (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Username
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
                          Password
                        </label>
                        <input
                          type="password"
                          value={apiPassword}
                          onChange={(e) => setApiPassword(e.target.value)}
                          placeholder="Leave blank to keep existing"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Leave blank to keep existing password
                        </p>
                      </div>
                    </>
                  )}
                </>
              )}

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                  {error}
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}



