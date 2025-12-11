'use client';

import { useState, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import type { TicketingTool } from '../types';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

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
    <div className="fixed inset-0 z-[9999] overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div
        onClick={(e) => e.stopPropagation()}
        className="max-w-2xl w-full max-h-[90vh] overflow-y-auto"
      >
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-bold text-neutral-900">Add Ticketing Tool Connection</h3>
              <Button variant="ghost" size="sm" onClick={onClose}>
                <XMarkIcon className="h-6 w-6" />
              </Button>
            </div>
          </CardHeader>
          <CardContent padding="md">

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-neutral-700 mb-2">
                  Ticketing Tool *
                </label>
                <select
                  value={selectedTool}
                  onChange={(e) => setSelectedTool(e.target.value)}
                  className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
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
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Connection Type *
                  </label>
                  <select
                    value={connectionType}
                    onChange={(e) => setConnectionType(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
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
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
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
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                  />
                  <p className="text-xs text-neutral-500 mt-1">
                    Configure this URL in your ticketing tool's webhook settings
                  </p>
                </div>
              )}

              {connectionType === 'api_poll' && (
                <>
                  <div>
                    <label className="block text-sm font-semibold text-neutral-700 mb-2">
                      API Base URL *
                    </label>
                    <input
                      type="text"
                      value={apiBaseUrl}
                      onChange={(e) => setApiBaseUrl(e.target.value)}
                      placeholder={selectedTool === 'manageengine' ? 'https://sdpondemand.manageengine.in' : 'https://your-instance.service-now.com'}
                      className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                      required
                    />
                  </div>
                  
                  {(selectedTool === 'zoho' || selectedTool === 'manageengine') ? (
                    <>
                      <div>
                        <label className="block text-sm font-semibold text-neutral-700 mb-2">
                          Client ID *
                        </label>
                        <input
                          type="text"
                          value={clientId}
                          onChange={(e) => setClientId(e.target.value)}
                          placeholder={`Your ${selectedTool === 'zoho' ? 'Zoho' : 'ManageEngine'} OAuth Client ID`}
                          className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                          required
                        />
                        <p className="text-xs text-neutral-500 mt-1">
                          Register your app at {selectedTool === 'zoho' ? 'https://api-console.zoho.com' : 'https://api-console.zoho.in'} to get Client ID and Secret
                        </p>
                      </div>
                      <div>
                        <label className="block text-sm font-semibold text-neutral-700 mb-2">
                          Client Secret *
                        </label>
                        <input
                          type="password"
                          value={clientSecret}
                          onChange={(e) => setClientSecret(e.target.value)}
                          placeholder={`Your ${selectedTool === 'zoho' ? 'Zoho' : 'ManageEngine'} OAuth Client Secret`}
                          className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-semibold text-neutral-700 mb-2">
                          Redirect URI
                        </label>
                        <input
                          type="text"
                          value={redirectUri}
                          onChange={(e) => setRedirectUri(e.target.value)}
                          placeholder="http://localhost:8000/oauth/callback"
                          className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                        />
                        <p className="text-xs text-neutral-500 mt-1">
                          Configure this redirect URI in your OAuth app settings
                        </p>
                      </div>
                    </>
                  ) : (
                    <>
                      <div>
                        <label className="block text-sm font-semibold text-neutral-700 mb-2">
                          API Key / Username
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
                          API Password / Token
                        </label>
                        <input
                          type="password"
                          value={apiPassword}
                          onChange={(e) => setApiPassword(e.target.value)}
                          className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                        />
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

              <div className="flex items-center justify-end gap-3 pt-4">
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
                  disabled={saving || !selectedTool}
                  isLoading={saving}
                >
                  {saving ? 'Creating...' : 'Create Connection'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}



