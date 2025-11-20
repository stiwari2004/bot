'use client';

import { useState, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';

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

      const response = await fetch(apiConfig.endpoints.connectors.credentials(), {
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
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-semibold text-gray-900">Add Credential</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Credential Type *
              </label>
              <select
                value={credentialType}
                onChange={(e) => setCredentialType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
                placeholder="e.g., Azure-Prod-Account"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Environment *
              </label>
              <select
                value={environment}
                onChange={(e) => setEnvironment(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Tenant ID *
                  </label>
                  <input
                    type="text"
                    value={tenantId}
                    onChange={(e) => setTenantId(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                    placeholder="Azure tenant ID"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Client ID *
                  </label>
                  <input
                    type="text"
                    value={clientId}
                    onChange={(e) => setClientId(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                    placeholder="Azure client ID"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Client Secret *
                  </label>
                  <input
                    type="password"
                    value={clientSecret}
                    onChange={(e) => setClientSecret(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                    placeholder="Azure client secret"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Subscription ID
                  </label>
                  <input
                    type="text"
                    value={subscriptionId}
                    onChange={(e) => setSubscriptionId(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Azure subscription ID (optional)"
                  />
                </div>
              </>
            )}

            {credentialType === 'gcp' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Service Account Key (JSON) *
                  </label>
                  <textarea
                    value={serviceAccountKey}
                    onChange={(e) => setServiceAccountKey(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    rows={6}
                    required
                    placeholder="Paste GCP service account JSON key"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Project ID
                  </label>
                  <input
                    type="text"
                    value={projectId}
                    onChange={(e) => setProjectId(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="GCP project ID (optional)"
                  />
                </div>
              </>
            )}

            {credentialType === 'aws' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Access Key ID *
                  </label>
                  <input
                    type="text"
                    value={accessKeyId}
                    onChange={(e) => setAccessKeyId(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                    placeholder="AWS access key ID"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Secret Access Key *
                  </label>
                  <input
                    type="password"
                    value={secretAccessKey}
                    onChange={(e) => setSecretAccessKey(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                    placeholder="AWS secret access key"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Region
                  </label>
                  <input
                    type="text"
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="e.g., us-east-1"
                  />
                </div>
              </>
            )}

            {(credentialType === 'ssh' || credentialType === 'database') && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Username
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Username"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Password
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Password"
                  />
                </div>
                {credentialType === 'database' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Database Name
                    </label>
                    <input
                      type="text"
                      value={databaseName}
                      onChange={(e) => setDatabaseName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Database name"
                    />
                  </div>
                )}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Host
                  </label>
                  <input
                    type="text"
                    value={host}
                    onChange={(e) => setHost(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Host or IP address"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Port
                  </label>
                  <input
                    type="number"
                    value={port}
                    onChange={(e) => setPort(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Port number"
                  />
                </div>
              </>
            )}

            {credentialType === 'api_key' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  API Key *
                </label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                  placeholder="API key"
                />
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Saving...' : 'Save Credential'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

