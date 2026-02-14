'use client';

import { useState, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface AddCredentialModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

export function AddCredentialModal({ onClose, onSuccess }: AddCredentialModalProps) {
  const [credentialType, setCredentialType] = useState<string>('ssh');
  const [name, setName] = useState('');
  const [environment, setEnvironment] = useState('prod');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [host, setHost] = useState('');
  const [port, setPort] = useState('');
  const [databaseName, setDatabaseName] = useState('');
  const [tenantId, setTenantId] = useState('');
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [subscriptionId, setSubscriptionId] = useState('');
  const [serviceAccountKey, setServiceAccountKey] = useState('');
  const [projectId, setProjectId] = useState('');
  const [accessKeyId, setAccessKeyId] = useState('');
  const [secretAccessKey, setSecretAccessKey] = useState('');
  const [region, setRegion] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        name,
        credential_type: credentialType,
        environment,
      };

      if (credentialType === 'azure') {
        payload.tenant_id = tenantId;
        payload.client_id = clientId;
        payload.client_secret = clientSecret;
        payload.subscription_id = subscriptionId;
      } else if (credentialType === 'gcp') {
        payload.service_account_key = serviceAccountKey;
        payload.project_id = projectId;
      } else if (credentialType === 'aws') {
        payload.access_key_id = accessKeyId;
        payload.secret_access_key = secretAccessKey;
        payload.region = region;
      } else {
        payload.username = username;
        if (password) payload.password = password;
        if (apiKey) payload.api_key = apiKey;
        if (host) payload.host = host;
        if (port) payload.port = parseInt(port);
        if (databaseName) payload.database_name = databaseName;
      }

      const response = await authFetch(apiConfig.endpoints.connectors.credentials(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create credential');
      }

      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create credential');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div
        onClick={(e) => e.stopPropagation()}
        className="max-w-2xl w-full max-h-[90vh] overflow-y-auto"
      >
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-bold text-neutral-900">Add Credential</h3>
              <Button variant="ghost" size="sm" onClick={onClose}>
                <XMarkIcon className="h-6 w-6" />
              </Button>
            </div>
          </CardHeader>
          <CardContent padding="md">
            {error && (
              <Card variant="outlined" className="mb-4 border-error-200 bg-error-50">
                <CardContent padding="sm">
                  <p className="text-sm text-error-800 font-medium">{error}</p>
                </CardContent>
              </Card>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-neutral-700 mb-2">
                Credential Type *
              </label>
              <select
                value={credentialType}
                onChange={(e) => setCredentialType(e.target.value)}
                className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                required
              >
                <option value="ssh">SSH</option>
                <option value="database">Database</option>
                <option value="api_key">API Key</option>
                <option value="azure">Azure</option>
                <option value="gcp">GCP</option>
                <option value="aws">AWS</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold text-neutral-700 mb-2">
                Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                required
                placeholder="e.g., Azure-Prod-Account"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-neutral-700 mb-2">
                Environment *
              </label>
              <select
                value={environment}
                onChange={(e) => setEnvironment(e.target.value)}
                className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                required
              >
                <option value="prod">Production</option>
                <option value="staging">Staging</option>
                <option value="dev">Development</option>
              </select>
            </div>

            {credentialType === 'azure' && (
              <>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Tenant ID *
                  </label>
                  <input
                    type="text"
                    value={tenantId}
                    onChange={(e) => setTenantId(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    required
                    placeholder="Azure tenant ID"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Client ID *
                  </label>
                  <input
                    type="text"
                    value={clientId}
                    onChange={(e) => setClientId(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    required
                    placeholder="Azure client ID"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Client Secret *
                  </label>
                  <input
                    type="password"
                    value={clientSecret}
                    onChange={(e) => setClientSecret(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    required
                    placeholder="Azure client secret"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Subscription ID
                  </label>
                  <input
                    type="text"
                    value={subscriptionId}
                    onChange={(e) => setSubscriptionId(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    placeholder="Azure subscription ID (optional)"
                  />
                </div>
              </>
            )}

            {credentialType === 'gcp' && (
              <>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Service Account Key (JSON) *
                  </label>
                  <textarea
                    value={serviceAccountKey}
                    onChange={(e) => setServiceAccountKey(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    rows={6}
                    required
                    placeholder="Paste GCP service account JSON key"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Project ID
                  </label>
                  <input
                    type="text"
                    value={projectId}
                    onChange={(e) => setProjectId(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    placeholder="GCP project ID (optional)"
                  />
                </div>
              </>
            )}

            {credentialType === 'aws' && (
              <>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Access Key ID *
                  </label>
                  <input
                    type="text"
                    value={accessKeyId}
                    onChange={(e) => setAccessKeyId(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    required
                    placeholder="AWS access key ID"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Secret Access Key *
                  </label>
                  <input
                    type="password"
                    value={secretAccessKey}
                    onChange={(e) => setSecretAccessKey(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    required
                    placeholder="AWS secret access key"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Region
                  </label>
                  <input
                    type="text"
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    placeholder="e.g., us-east-1"
                  />
                </div>
              </>
            )}

            {(credentialType === 'ssh' || credentialType === 'database') && (
              <>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Username
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    placeholder="Username"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Password
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    placeholder="Password"
                  />
                </div>
                {credentialType === 'database' && (
                  <div>
                    <label className="block text-sm font-semibold text-neutral-700 mb-2">
                      Database Name
                    </label>
                    <input
                      type="text"
                      value={databaseName}
                      onChange={(e) => setDatabaseName(e.target.value)}
                      className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                      placeholder="Database name"
                    />
                  </div>
                )}
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Host
                  </label>
                  <input
                    type="text"
                    value={host}
                    onChange={(e) => setHost(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    placeholder="Host or IP address"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Port
                  </label>
                  <input
                    type="number"
                    value={port}
                    onChange={(e) => setPort(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    placeholder="Port number"
                  />
                </div>
              </>
            )}

            {credentialType === 'api_key' && (
              <div>
                <label className="block text-sm font-semibold text-neutral-700 mb-2">
                  API Key *
                </label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                  required
                  placeholder="API key"
                />
              </div>
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
                  disabled={saving}
                  isLoading={saving}
                >
                  {saving ? 'Saving...' : 'Save Credential'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}



