'use client';

import { useState, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import type { InfrastructureConnection, Credential } from '../types';

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

      const response = await fetch(apiConfig.endpoints.connectors.infrastructureConnection(connection.id), {
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
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-semibold text-gray-900">Edit Infrastructure Connection</h3>
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
                Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
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

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Credential
              </label>
              <select
                value={credentialId || ''}
                onChange={(e) => setCredentialId(e.target.value ? parseInt(e.target.value) : null)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Target Host
                  </label>
                  <input
                    type="text"
                    value={targetHost}
                    onChange={(e) => setTargetHost(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Host or IP address"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Target Port
                  </label>
                  <input
                    type="number"
                    value={targetPort}
                    onChange={(e) => setTargetPort(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Port number"
                  />
                </div>
                {connection.type === 'database' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Service Name
                    </label>
                    <input
                      type="text"
                      value={targetService}
                      onChange={(e) => setTargetService(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="e.g., postgres, mysql"
                    />
                  </div>
                )}
              </>
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
                {saving ? 'Saving...' : 'Save Connection'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

