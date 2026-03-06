'use client';

import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface ProvisioningProject {
  id: number;
  name: string;
  description?: string;
  provider: string;
  state: string;
  created_at: string;
  updated_at?: string;
}

type OsType = 'linux' | 'windows';

export function ProvisioningDashboard() {
  const [projects, setProjects] = useState<ProvisioningProject[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Form state for provision modal (Azure VM)
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [subscriptionId, setSubscriptionId] = useState('');
  const [tenantId, setTenantId] = useState('');
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [location, setLocation] = useState('eastus');
  const [resourceGroup, setResourceGroup] = useState('');
  const [vmName, setVmName] = useState('');
  const [vmSize, setVmSize] = useState('Standard_B1s');
  const [osType, setOsType] = useState<OsType>('linux');
  const [sshPublicKey, setSshPublicKey] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const url = apiConfig.endpoints.provisioning.list();
      const response = await authFetch(url);
      if (!response.ok) {
        throw new Error('Failed to fetch projects');
      }
      const data = await response.json();
      setProjects(data.projects || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const openCreateModal = () => {
    setCreateError(null);
    setName('');
    setDescription('');
    setSubscriptionId('');
    setTenantId('');
    setClientId('');
    setClientSecret('');
    setLocation('eastus');
    setResourceGroup('');
    setVmName('');
    setVmSize('Standard_B1s');
    setOsType('linux');
    setSshPublicKey('');
    setAdminPassword('');
    setShowCreateModal(true);
  };

  const closeCreateModal = () => {
    if (!creating) setShowCreateModal(false);
  };

  const handleProvisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);

    try {
      const variables: Record<string, string | boolean> = {
        create_vm: true,
        vm_name: vmName || `vm-${Date.now()}`,
        vm_size: vmSize,
        location,
        admin_username: 'azureuser',
      };
      if (resourceGroup.trim()) variables.resource_group = resourceGroup.trim();
      if (osType === 'linux') {
        if (sshPublicKey.trim()) variables.ssh_public_key = sshPublicKey.trim();
      } else {
        if (adminPassword) variables.admin_password = adminPassword;
      }

      const body = {
        name: name.trim() || 'Azure VM Project',
        description: description.trim() || undefined,
        provider: 'azure',
        credentials: {
          subscription_id: subscriptionId.trim(),
          tenant_id: tenantId.trim(),
          client_id: clientId.trim(),
          client_secret: clientSecret,
        },
        variables,
      };

      const url = apiConfig.endpoints.provisioning.provision();
      const response = await authFetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const msg = typeof data.detail === 'string' ? data.detail : data.error || 'Provisioning failed';
        throw new Error(msg);
      }
      if (data && data.success === false && data.error) {
        throw new Error(data.error);
      }
      closeCreateModal();
      fetchProjects();
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setCreating(false);
    }
  };

  const stateColors: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-800',
    provisioning: 'bg-blue-100 text-blue-800',
    active: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    destroyed: 'bg-gray-100 text-gray-600',
  };

  const provisionModal = showCreateModal && mounted && createPortal(
    <div
      className="fixed inset-0 z-[9999] overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={closeCreateModal}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="max-w-2xl w-full max-h-[90vh] overflow-y-auto"
      >
        <Card variant="elevated">
          <CardHeader className="flex flex-row items-center justify-between border-b border-neutral-200 pb-4">
            <h3 className="text-lg font-semibold text-neutral-900">Provision Azure VM</h3>
            <button
              type="button"
              onClick={closeCreateModal}
              disabled={creating}
              className="p-1 rounded-md text-neutral-500 hover:text-neutral-700 hover:bg-neutral-100"
              aria-label="Close"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </CardHeader>
          <CardContent className="pt-4">
            <form onSubmit={handleProvisionSubmit} className="space-y-4">
              {createError && (
                <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-800">
                  {createError}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Project name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="My Azure VM"
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-neutral-900 placeholder-neutral-400 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Description (optional)</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Short description"
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-neutral-900 placeholder-neutral-400 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                />
              </div>

              <div className="border-t border-neutral-200 pt-4">
                <h4 className="text-sm font-semibold text-neutral-800 mb-3">Azure credentials</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-medium text-neutral-700 mb-1">Subscription ID</label>
                    <input
                      type="text"
                      value={subscriptionId}
                      onChange={(e) => setSubscriptionId(e.target.value)}
                      required
                      className="w-full rounded-md border border-neutral-300 px-3 py-2 text-neutral-900 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1">Tenant ID</label>
                    <input
                      type="text"
                      value={tenantId}
                      onChange={(e) => setTenantId(e.target.value)}
                      required
                      className="w-full rounded-md border border-neutral-300 px-3 py-2 text-neutral-900 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1">Client ID</label>
                    <input
                      type="text"
                      value={clientId}
                      onChange={(e) => setClientId(e.target.value)}
                      required
                      className="w-full rounded-md border border-neutral-300 px-3 py-2 text-neutral-900 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-medium text-neutral-700 mb-1">Client secret</label>
                    <input
                      type="password"
                      value={clientSecret}
                      onChange={(e) => setClientSecret(e.target.value)}
                      required
                      className="w-full rounded-md border border-neutral-300 px-3 py-2 text-neutral-900 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                    />
                  </div>
                </div>
              </div>

              <div className="border-t border-neutral-200 pt-4">
                <h4 className="text-sm font-semibold text-neutral-800 mb-3">VM settings</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1">Location</label>
                    <input
                      type="text"
                      value={location}
                      onChange={(e) => setLocation(e.target.value)}
                      placeholder="eastus"
                      className="w-full rounded-md border border-neutral-300 px-3 py-2 text-neutral-900 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1">Resource group (optional)</label>
                    <input
                      type="text"
                      value={resourceGroup}
                      onChange={(e) => setResourceGroup(e.target.value)}
                      placeholder="Auto-created if empty"
                      className="w-full rounded-md border border-neutral-300 px-3 py-2 text-neutral-900 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1">VM name</label>
                    <input
                      type="text"
                      value={vmName}
                      onChange={(e) => setVmName(e.target.value)}
                      placeholder="vm-my-server"
                      className="w-full rounded-md border border-neutral-300 px-3 py-2 text-neutral-900 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1">VM size</label>
                    <select
                      value={vmSize}
                      onChange={(e) => setVmSize(e.target.value)}
                      className="w-full rounded-md border border-neutral-300 px-3 py-2 text-neutral-900 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                    >
                      <option value="Standard_B1s">Standard_B1s</option>
                      <option value="Standard_B1ms">Standard_B1ms</option>
                      <option value="Standard_B2s">Standard_B2s</option>
                      <option value="Standard_D2s_v3">Standard_D2s_v3</option>
                    </select>
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-medium text-neutral-700 mb-1">OS type</label>
                    <div className="flex gap-4">
                      <label className="inline-flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="osType"
                          checked={osType === 'linux'}
                          onChange={() => setOsType('linux')}
                          className="rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
                        />
                        <span>Linux (SSH key)</span>
                      </label>
                      <label className="inline-flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="osType"
                          checked={osType === 'windows'}
                          onChange={() => setOsType('windows')}
                          className="rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
                        />
                        <span>Windows (password)</span>
                      </label>
                    </div>
                  </div>
                  {osType === 'linux' && (
                    <div className="sm:col-span-2">
                      <label className="block text-sm font-medium text-neutral-700 mb-1">SSH public key</label>
                      <textarea
                        value={sshPublicKey}
                        onChange={(e) => setSshPublicKey(e.target.value)}
                        rows={3}
                        placeholder="ssh-rsa AAAA..."
                        className="w-full rounded-md border border-neutral-300 px-3 py-2 text-neutral-900 font-mono text-sm placeholder-neutral-400 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                      />
                    </div>
                  )}
                  {osType === 'windows' && (
                    <div className="sm:col-span-2">
                      <label className="block text-sm font-medium text-neutral-700 mb-1">Admin password</label>
                      <input
                        type="password"
                        value={adminPassword}
                        onChange={(e) => setAdminPassword(e.target.value)}
                        placeholder="Must meet Azure complexity requirements"
                        className="w-full rounded-md border border-neutral-300 px-3 py-2 text-neutral-900 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                      />
                    </div>
                  )}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-neutral-200">
                <Button type="button" variant="secondary" onClick={closeCreateModal} disabled={creating}>
                  Cancel
                </Button>
                <Button type="submit" disabled={creating}>
                  {creating ? 'Provisioning…' : 'Provision'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>,
    document.body
  );

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-neutral-900">Infrastructure Provisioning</h2>
        <Button onClick={openCreateModal}>Provision Infrastructure</Button>
      </div>

      {loading && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto" />
          <p className="mt-4 text-neutral-600">Loading projects...</p>
        </div>
      )}

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 p-4">
          <p className="text-red-800">Error: {error}</p>
        </div>
      )}

      {!loading && !error && projects.length === 0 && (
        <div className="text-center py-8 bg-neutral-50 rounded-lg">
          <p className="text-neutral-600">No provisioning projects found. Create one with the button above.</p>
        </div>
      )}

      {!loading && !error && projects.length > 0 && (
        <div className="grid gap-4">
          {projects.map((project) => (
            <div
              key={project.id}
              className="border border-neutral-200 rounded-lg p-4 hover:shadow-md transition-shadow bg-white"
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-lg text-neutral-900">{project.name}</h3>
                  {project.description && (
                    <p className="text-sm text-neutral-600 mt-1">{project.description}</p>
                  )}
                  <p className="text-sm mt-2">
                    Provider: <span className="font-medium">{project.provider}</span>
                  </p>
                  <p className="text-sm text-neutral-500 mt-2">
                    Created: {new Date(project.created_at).toLocaleString()}
                  </p>
                </div>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-semibold capitalize ${
                    stateColors[project.state] ?? 'bg-neutral-200 text-neutral-800'
                  }`}
                >
                  {project.state}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {provisionModal}
    </div>
  );
}
