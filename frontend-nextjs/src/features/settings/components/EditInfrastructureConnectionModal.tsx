'use client';

import { useState, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';
import type { InfrastructureConnection, Credential } from '../types';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface EditInfrastructureConnectionModalProps {
  connection: InfrastructureConnection;
  credentials: Credential[];
  onClose: () => void;
  onSuccess: () => void;
}

export function EditInfrastructureConnectionModal({ connection, credentials, onClose, onSuccess }: EditInfrastructureConnectionModalProps) {
  const [name, setName] = useState(connection.name);
  const [environment, setEnvironment] = useState(connection.environment);
  const [credentialId, setCredentialId] = useState<number | null>(connection.credential_id);
  const [targetHost, setTargetHost] = useState(connection.target_host || '');
  const [targetPort, setTargetPort] = useState(connection.target_port?.toString() || '');
  const [targetService, setTargetService] = useState(connection.target_service || '');
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
        connection_type: connection.type,
        environment,
        credential_id: credentialId || undefined,
        target_host: targetHost || undefined,
        target_port: targetPort ? parseInt(targetPort) : undefined,
        target_service: targetService || undefined,
      };

      const response = await authFetch(apiConfig.endpoints.connectors.infrastructureConnection(connection.id), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

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
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div
        onClick={(e) => e.stopPropagation()}
        className="max-w-2xl w-full max-h-[90vh] overflow-y-auto"
      >
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-bold text-neutral-900">Edit Infrastructure Connection</h3>
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
                Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                required
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

            <div>
              <label className="block text-sm font-semibold text-neutral-700 mb-2">
                Credential
              </label>
              <select
                value={credentialId || ''}
                onChange={(e) => setCredentialId(e.target.value ? parseInt(e.target.value) : null)}
                className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
              >
                <option value="">Select a credential (optional)</option>
                {credentials.map((cred) => (
                  <option key={cred.id} value={cred.id}>
                    {cred.name} ({cred.type} - {cred.environment})
                  </option>
                ))}
              </select>
            </div>

            {(connection.type === 'ssh' || connection.type === 'winrm' || connection.type === 'database' || connection.type === 'api') && (
              <>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Target Host
                  </label>
                  <input
                    type="text"
                    value={targetHost}
                    onChange={(e) => setTargetHost(e.target.value)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
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
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    placeholder="Port number"
                  />
                </div>
                {connection.type === 'database' && (
                  <div>
                    <label className="block text-sm font-semibold text-neutral-700 mb-2">
                      Service Name
                    </label>
                    <input
                      type="text"
                      value={targetService}
                      onChange={(e) => setTargetService(e.target.value)}
                      className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
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



