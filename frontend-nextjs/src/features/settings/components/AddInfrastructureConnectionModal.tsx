'use client';

import { useState, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import type { Credential } from '../types';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface AddInfrastructureConnectionModalProps {
  credentials: Credential[];
  onClose: () => void;
  onSuccess: () => void;
}

export function AddInfrastructureConnectionModal({ credentials, onClose, onSuccess }: AddInfrastructureConnectionModalProps) {
  const [connectionType, setConnectionType] = useState<string>('ssh');
  const [name, setName] = useState('');
  const [environment, setEnvironment] = useState('prod');
  const [credentialId, setCredentialId] = useState<number | null>(null);
  const [targetHost, setTargetHost] = useState('');
  const [targetPort, setTargetPort] = useState('');
  const [targetService, setTargetService] = useState('');
  const [resourceId, setResourceId] = useState('');
  const [subscriptionId, setSubscriptionId] = useState('');
  const [projectId, setProjectId] = useState('');
  const [zone, setZone] = useState('');
  const [instanceName, setInstanceName] = useState('');
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
      const metaData: any = {};

      if (connectionType === 'cloud_account' || connectionType === 'azure_subscription') {
        if (subscriptionId) metaData.subscription_id = subscriptionId;
      } else if (connectionType === 'azure_bastion') {
        if (resourceId) metaData.resource_id = resourceId;
        if (subscriptionId) metaData.subscription_id = subscriptionId;
      } else if (connectionType === 'gcp_iap') {
        if (projectId) metaData.project_id = projectId;
        if (zone) metaData.zone = zone;
        if (instanceName) metaData.instance_name = instanceName;
      }

      const payload: any = {
        name,
        connection_type: connectionType,
        environment,
        credential_id: credentialId || undefined,
        target_host: targetHost || undefined,
        target_port: targetPort ? parseInt(targetPort) : undefined,
        target_service: targetService || undefined,
        meta_data: Object.keys(metaData).length > 0 ? metaData : undefined,
      };

      const response = await fetch(apiConfig.endpoints.connectors.infrastructureConnections(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div
        onClick={(e) => e.stopPropagation()}
        className="max-w-2xl w-full max-h-[90vh] overflow-y-auto"
      >
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-bold text-neutral-900">Add Infrastructure Connection</h3>
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
                Connection Type *
              </label>
              <select
                value={connectionType}
                onChange={(e) => setConnectionType(e.target.value)}
                className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              >
                <optgroup label="Cloud Accounts (Auto-Discovery)">
                  <option value="cloud_account">Cloud Account (Azure/GCP/AWS)</option>
                  <option value="azure_subscription">Azure Subscription</option>
                </optgroup>
                <optgroup label="Individual Servers">
                  <option value="ssh">SSH</option>
                  <option value="winrm">WinRM</option>
                  <option value="database">Database</option>
                  <option value="api">API</option>
                  <option value="azure_bastion">Azure Bastion (Single VM)</option>
                  <option value="gcp_iap">GCP IAP (Single Instance)</option>
                  <option value="aws_ssm">AWS SSM (Single Instance)</option>
                </optgroup>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                {connectionType === 'cloud_account' || connectionType === 'azure_subscription' 
                  ? 'Connect to your cloud account once. The agent will automatically discover and connect to any server within that account on-the-fly.'
                  : 'Connect to a specific server. You will need to add each server individually.'}
              </p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-neutral-700 mb-2">
                Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
                placeholder="e.g., Azure-VM-Prod-01"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-neutral-700 mb-2">
                Environment *
              </label>
              <select
                value={environment}
                onChange={(e) => setEnvironment(e.target.value)}
                className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              >
                <option value="prod">Production</option>
                <option value="staging">Staging</option>
                <option value="dev">Development</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold text-neutral-700 mb-2">
                Credential
              </label>
              <select
                value={credentialId || ''}
                onChange={(e) => setCredentialId(e.target.value ? parseInt(e.target.value) : null)}
                className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Select a credential (optional)</option>
                {credentials.map((cred) => (
                  <option key={cred.id} value={cred.id}>
                    {cred.name} ({cred.type} - {cred.environment})
                  </option>
                ))}
              </select>
            </div>

            {(connectionType === 'cloud_account' || connectionType === 'azure_subscription') && (
              <div>
                <label className="block text-sm font-semibold text-neutral-700 mb-2">
                  Subscription ID *
                </label>
                <input
                  type="text"
                  value={subscriptionId}
                  onChange={(e) => setSubscriptionId(e.target.value)}
                  className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                  placeholder="Azure subscription ID"
                />
                <p className="text-xs text-gray-500 mt-1">
                  The agent will automatically discover and connect to any VM in this subscription.
                </p>
              </div>
            )}

            {connectionType === 'azure_bastion' && (
              <>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Resource ID *
                  </label>
                  <input
                    type="text"
                    value={resourceId}
                    onChange={(e) => setResourceId(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                    placeholder="/subscriptions/.../virtualMachines/..."
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
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Azure subscription ID (optional)"
                  />
                </div>
              </>
            )}

            {connectionType === 'gcp_iap' && (
              <>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Project ID *
                  </label>
                  <input
                    type="text"
                    value={projectId}
                    onChange={(e) => setProjectId(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                    placeholder="GCP project ID"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Zone *
                  </label>
                  <input
                    type="text"
                    value={zone}
                    onChange={(e) => setZone(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                    placeholder="e.g., us-central1-a"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Instance Name *
                  </label>
                  <input
                    type="text"
                    value={instanceName}
                    onChange={(e) => setInstanceName(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                    placeholder="GCP instance name"
                  />
                </div>
              </>
            )}

            {(connectionType === 'ssh' || connectionType === 'winrm' || connectionType === 'database' || connectionType === 'api') && (
              <>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Target Host
                  </label>
                  <input
                    type="text"
                    value={targetHost}
                    onChange={(e) => setTargetHost(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Host or IP address"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Target Port
                  </label>
                  <input
                    type="number"
                    value={targetPort}
                    onChange={(e) => setTargetPort(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Port number"
                  />
                </div>
                {connectionType === 'database' && (
                  <div>
                    <label className="block text-sm font-semibold text-neutral-700 mb-2">
                      Service Name
                    </label>
                    <input
                      type="text"
                      value={targetService}
                      onChange={(e) => setTargetService(e.target.value)}
                      className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="e.g., postgres, mysql"
                    />
                  </div>
                )}
              </>
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
                  {saving ? 'Saving...' : 'Save Connection'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}



