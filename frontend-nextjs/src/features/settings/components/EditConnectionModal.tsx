'use client';

import { useState, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';
import type { TicketingConnection, TicketingTool } from '../types';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

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
  // ManageEngine specific: allow choosing between:
  // - v2: OAuth2 client (Client ID / Secret / Redirect URI)
  // - v3: API key / authtoken mode
  const [manageEngineVersion, setManageEngineVersion] = useState<'v2' | 'v3'>('v2');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isManageEngine = connection.tool_name === 'manageengine';
  const isZoho = connection.tool_name === 'zoho';

  useEffect(() => {
    if (connection.meta_data) {
      try {
        const meta = typeof connection.meta_data === 'string' 
          ? JSON.parse(connection.meta_data) 
          : connection.meta_data;

        let version: 'v2' | 'v3' = 'v2';
        if (isManageEngine && meta.version) {
          version = meta.version === 'v3' ? 'v3' : 'v2';
        }
        if (isManageEngine) {
          setManageEngineVersion(version);
        }

        const useOAuthForThisConnection =
          isZoho || (isManageEngine && version === 'v2');

        if (useOAuthForThisConnection) {
          setClientId(meta.client_id || '');
          setClientSecret(meta.client_secret ? '••••••••' : '');
          const defaultRedirect = typeof window !== 'undefined'
            ? `${window.location.origin}/oauth/callback`
            : 'http://localhost:8000/oauth/callback';
          setRedirectUri(meta.redirect_uri || defaultRedirect);
        } else {
          setApiSecret(meta.api_secret ? '••••••••' : '');
          // For ServiceNow, load username/password from meta_data or connection fields
          if (connection.tool_name === 'servicenow') {
            setApiUsername(meta.username || connection.api_username || '');
            const hasPassword = meta.password || (connection.api_password && connection.api_password.length > 0);
            setApiPassword(hasPassword ? '••••••••' : '');
            setAuthMethod('username'); // ServiceNow uses username/password (Basic Auth)
          } else {
            if (meta.api_key || connection.api_key) {
              setAuthMethod('api_key');
            } else if (meta.api_username || connection.api_username) {
              setAuthMethod('username');
            }
          }
        }
      } catch (e) {
        // Ignore parse errors
      }
    }
    // Only depend on specific properties that matter, not the entire connection object
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connection.id, connection.tool_name, connection.meta_data, connection.api_username, connection.api_password, connection.api_key]);

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

      const useOAuthForThisConnection =
        isZoho || (isManageEngine && manageEngineVersion === 'v2');

      if (useOAuthForThisConnection) {
        const meta: any = {};
        if (clientId) meta.client_id = clientId;
        if (clientSecret && clientSecret !== '••••••••') {
          meta.client_secret = clientSecret;
        }
        if (redirectUri) meta.redirect_uri = redirectUri;
        // Persist selected API version for ManageEngine so backend/fetcher
        // can differentiate behaviour if needed.
        if (isManageEngine) {
          meta.version = manageEngineVersion || 'v2';
        }
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
          if (apiPassword && apiPassword !== '••••••••') {
            payload.api_password = apiPassword;
          }
          // For ServiceNow, also store credentials in meta_data for consistency
          if (connection.tool_name === 'servicenow') {
            if (apiUsername) meta.username = apiUsername;
            if (apiPassword && apiPassword !== '••••••••') {
              meta.password = apiPassword;
            }
          }
        }
        // For ManageEngine v3 specifically, also store the API version flag in meta_data.
        if (isManageEngine) {
          meta.version = manageEngineVersion || 'v3';
        }
        if (Object.keys(meta).length > 0) {
          payload.meta_data = meta;
        }
      }

      const response = await authFetch(
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
    <div className="fixed inset-0 z-[9999] overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div
        onClick={(e) => e.stopPropagation()}
        className="max-w-2xl w-full max-h-[90vh] overflow-y-auto"
      >
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-bold text-neutral-900">Edit Connection - {connection.tool_name}</h3>
              <Button variant="ghost" size="sm" onClick={onClose}>
                <XMarkIcon className="h-6 w-6" />
              </Button>
            </div>
          </CardHeader>
          <CardContent padding="md">

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-neutral-700 mb-2">
                  API Base URL *
                </label>
                <input
                  type="text"
                  value={apiBaseUrl}
                  onChange={(e) => setApiBaseUrl(e.target.value)}
                  className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-neutral-700 mb-2">
                  Sync Interval (minutes)
                </label>
                <input
                  type="number"
                  value={syncIntervalMinutes}
                  onChange={(e) => setSyncIntervalMinutes(parseInt(e.target.value) || 5)}
                  min="1"
                  className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                />
              </div>

              {(connection.tool_name === 'zoho' || connection.tool_name === 'manageengine') ? (
                <>
                  {/* ManageEngine: allow choosing between Cloud (OAuth) and On‑Prem (API key) */}
                  {connection.tool_name === 'manageengine' && (
                    <div>
                      <label className="block text-sm font-semibold text-neutral-700 mb-2">
                        ManageEngine API Version
                      </label>
                      <select
                        value={manageEngineVersion}
                        onChange={(e) => setManageEngineVersion(e.target.value as 'v2' | 'v3')}
                        className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                      >
                        <option value="v2">ServiceDesk Plus Cloud (OAuth – Client ID / Secret / Redirect URI)</option>
                        <option value="v3">ServiceDesk Plus On-Prem (API key / authtoken)</option>
                      </select>
                      <p className="text-xs text-neutral-500 mt-1">
                        Cloud uses the OAuth authorization code flow (Client ID / Secret / Redirect URI, then Authorize). On‑Prem uses only a technician API key / authtoken.
                      </p>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-semibold text-neutral-700 mb-2">
                      Client ID
                    </label>
                    <input
                      type="text"
                      value={clientId}
                      onChange={(e) => setClientId(e.target.value)}
                      placeholder={`Your ${connection.tool_name === 'zoho' ? 'Zoho' : 'ManageEngine'} OAuth Client ID`}
                      className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-neutral-700 mb-2">
                      Client Secret
                    </label>
                    <input
                      type="password"
                      value={clientSecret}
                      onChange={(e) => setClientSecret(e.target.value)}
                      placeholder="Leave blank to keep existing"
                      className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    />
                    <p className="text-xs text-neutral-500 mt-1">
                      Leave blank to keep existing secret
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-neutral-700 mb-2">
                      Redirect URI
                    </label>
                    <input
                      type="text"
                      value={redirectUri}
                      onChange={(e) => setRedirectUri(e.target.value)}
                      className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    />
                    <p className="text-xs text-neutral-500 mt-1">
                      Must match the URI registered in ManageEngine/Zoho. SaaS: https://resolvify.tech/oauth/callback. PAAS: https://&lt;your-host&gt;/oauth/callback.
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="block text-sm font-semibold text-neutral-700 mb-2">
                      Authentication Method *
                    </label>
                    <select
                      value={authMethod}
                      onChange={(e) => setAuthMethod(e.target.value as 'api_key' | 'username')}
                      className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    >
                      <option value="api_key">API Key / Secret</option>
                      <option value="username">Username / Password</option>
                    </select>
                  </div>
                  {authMethod === 'api_key' ? (
                    <>
                      <div>
                        <label className="block text-sm font-semibold text-neutral-700 mb-2">
                          API Key
                        </label>
                        <input
                          type="text"
                          value={apiKey}
                          onChange={(e) => setApiKey(e.target.value)}
                          className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-semibold text-neutral-700 mb-2">
                          API Secret
                        </label>
                        <input
                          type="password"
                          value={apiSecret}
                          onChange={(e) => setApiSecret(e.target.value)}
                          placeholder="Leave blank to keep existing"
                          className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                        />
                        <p className="text-xs text-neutral-500 mt-1">
                          Leave blank to keep existing secret
                        </p>
                      </div>
                    </>
                  ) : (
                    <>
                      <div>
                        <label className="block text-sm font-semibold text-neutral-700 mb-2">
                          Username
                        </label>
                        <input
                          type="text"
                          value={apiUsername}
                          onChange={(e) => setApiUsername(e.target.value)}
                          className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-semibold text-neutral-700 mb-2">
                          Password
                        </label>
                        <input
                          type="password"
                          value={apiPassword}
                          onChange={(e) => setApiPassword(e.target.value)}
                          placeholder="Leave blank to keep existing"
                          className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                        />
                        <p className="text-xs text-neutral-500 mt-1">
                          Leave blank to keep existing password
                        </p>
                      </div>
                    </>
                  )}
                </>
              )}

              {error && (
                <Card variant="outlined" className="border-error-200 bg-error-50">
                  <CardContent padding="sm">
                    <p className="text-sm text-error-800 font-medium">{error}</p>
                  </CardContent>
                </Card>
              )}

              <div className="flex justify-end gap-3 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={onClose}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  disabled={saving}
                  isLoading={saving}
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}



