'use client';

import { useState } from 'react';
import { PlusIcon, WrenchScrewdriverIcon, ArrowUpTrayIcon } from '@heroicons/react/24/outline';
import type { InfrastructureConnection, Credential } from '../types';
import { useInfrastructureConnections } from '../hooks/useInfrastructureConnections';
import { apiConfig } from '@/lib/api-config';

interface InfrastructureConnectionsSectionProps {
  connections: InfrastructureConnection[];
  credentials: Credential[];
  onRefresh: () => void;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
  onShowAddCredential: () => void;
  onShowAddConnection: () => void;
  onEditConnection: (connection: InfrastructureConnection) => void;
  onShowTestCommand: (connection: InfrastructureConnection) => void;
}

export function InfrastructureConnectionsSection({
  connections,
  credentials,
  onRefresh,
  onSuccess,
  onError,
  onShowAddCredential,
  onShowAddConnection,
  onEditConnection,
  onShowTestCommand,
}: InfrastructureConnectionsSectionProps) {
  const [showImport, setShowImport] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);

  const {
    handleTestConnection,
    handleDiscoverResources,
    handleTestCommand,
    handleDeleteConnection,
  } = useInfrastructureConnections(onRefresh, onSuccess, onError);

  const handleImport = async () => {
    if (!importFile) return;

    try {
      setImporting(true);
      const formData = new FormData();
      formData.append('file', importFile);

      const response = await fetch(apiConfig.endpoints.connectors.infrastructureConnectionsImport(), {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Import failed');
      }

      const result = await response.json();
      setImportResult(result);
      setImportFile(null);
      
      if (result.imported && result.imported.length > 0) {
        onSuccess(`Successfully imported ${result.imported.length} connections`);
        onRefresh();
      }
    } catch (error) {
      console.error('Error importing connections:', error);
      onError(error instanceof Error ? error.message : 'Failed to import connections');
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm mb-6">
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Infrastructure Connections
            </h3>
            <p className="text-sm text-gray-600">
              Manage cloud and infrastructure connections (Azure, GCP, AWS, SSH, etc.)
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowImport(true)}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <ArrowUpTrayIcon className="h-5 w-5" />
              Import from Excel
            </button>
            <button
              onClick={onShowAddCredential}
              className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              <PlusIcon className="h-5 w-5" />
              Add Credential
            </button>
            <button
              onClick={onShowAddConnection}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <PlusIcon className="h-5 w-5" />
              Add Connection
            </button>
          </div>
        </div>

        {connections.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <WrenchScrewdriverIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p>No infrastructure connections configured</p>
            <p className="text-sm mt-2">Add credentials and connections to enable cloud access</p>
          </div>
        ) : (
          <div className="space-y-4">
            {connections.map((connection) => (
              <div
                key={connection.id}
                className="border border-gray-200 rounded-lg p-4"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="font-medium text-gray-900">
                        {connection.name}
                      </h4>
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 capitalize">
                        {connection.type.replace('_', ' ')}
                      </span>
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        {connection.environment}
                      </span>
                    </div>
                    {connection.target_host && (
                      <p className="text-sm text-gray-600 mb-1">
                        Host: <code className="bg-gray-100 px-2 py-1 rounded text-xs">{connection.target_host}</code>
                        {connection.target_port && <span className="ml-2">Port: {connection.target_port}</span>}
                      </p>
                    )}
                    {connection.target_service && (
                      <p className="text-sm text-gray-600 mb-1">
                        Service: <code className="bg-gray-100 px-2 py-1 rounded text-xs">{connection.target_service}</code>
                      </p>
                    )}
                    {connection.credential_id && (
                      <p className="text-xs text-gray-500 mt-2">
                        Credential ID: {connection.credential_id}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    {(connection.type === 'cloud_account' || connection.type === 'azure_subscription' || connection.type === 'azure_bastion') && (
                      <>
                        <button
                          onClick={() => handleTestConnection(connection.id)}
                          className="px-3 py-1 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                          title="Test Connection"
                        >
                          Test
                        </button>
                        <button
                          onClick={() => handleDiscoverResources(connection.id)}
                          className="px-3 py-1 text-sm bg-green-100 text-green-800 rounded-lg hover:bg-green-200 transition-colors"
                          title="Discover Resources"
                        >
                          Discover
                        </button>
                        <button
                          onClick={async () => {
                            await handleTestCommand(connection.id);
                            onShowTestCommand(connection);
                          }}
                          className="px-3 py-1 text-sm bg-purple-100 text-purple-800 rounded-lg hover:bg-purple-200 transition-colors"
                          title="Test Command Execution"
                        >
                          Test Command
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => onEditConnection(connection)}
                      className="px-3 py-1 text-sm bg-blue-100 text-blue-800 rounded-lg hover:bg-blue-200 transition-colors"
                      title="Edit Connection"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeleteConnection(connection.id)}
                      className="px-3 py-1 text-sm bg-red-100 text-red-800 rounded-lg hover:bg-red-200 transition-colors"
                      title="Delete Connection"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Import Modal */}
        {showImport && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4">
              <h2 className="text-xl font-bold mb-4">Import Infrastructure Connections from Excel</h2>
              
              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-2">
                  Upload an Excel file (.xlsx) with the following columns:
                </p>
                <div className="bg-gray-50 p-3 rounded text-sm">
                  <p className="font-semibold mb-1">Required columns:</p>
                  <ul className="list-disc list-inside text-gray-700 mb-2">
                    <li>name (or hostname, device_name, connection_name)</li>
                    <li>target_host (or host, ip, ip_address, management_ip)</li>
                    <li>connection_type (ssh, network_device, database, api, etc.)</li>
                  </ul>
                  <p className="font-semibold mb-1">Optional columns:</p>
                  <ul className="list-disc list-inside text-gray-700 mb-2">
                    <li>target_port, environment, username, password</li>
                    <li>For network devices: vendor, model, device_type, location, network_segment, site, serial_number, firmware_version, snmp_community, snmp_version</li>
                  </ul>
                </div>
              </div>

              <div className="mb-4">
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>

              {importResult && (
                <div className="mb-4 p-4 bg-gray-50 rounded">
                  <p className="font-semibold mb-2">{importResult.message}</p>
                  {importResult.imported && importResult.imported.length > 0 && (
                    <div className="mb-2">
                      <p className="text-sm text-green-700 font-medium">Imported ({importResult.imported.length}):</p>
                      <ul className="text-xs text-gray-600 mt-1">
                        {importResult.imported.slice(0, 5).map((item: any) => (
                          <li key={item.id}>• {item.name} ({item.host}) - {item.type}</li>
                        ))}
                        {importResult.imported.length > 5 && (
                          <li>... and {importResult.imported.length - 5} more</li>
                        )}
                      </ul>
                    </div>
                  )}
                  {importResult.errors && importResult.errors.length > 0 && (
                    <div>
                      <p className="text-sm text-red-700 font-medium">Errors ({importResult.errors.length}):</p>
                      <ul className="text-xs text-gray-600 mt-1">
                        {importResult.errors.slice(0, 5).map((error: any, idx: number) => (
                          <li key={idx}>• Row {error.row}: {error.error}</li>
                        ))}
                        {importResult.errors.length > 5 && (
                          <li>... and {importResult.errors.length - 5} more errors</li>
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              <div className="flex justify-end gap-3">
                <button
                  onClick={() => {
                    setShowImport(false);
                    setImportFile(null);
                    setImportResult(null);
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                  disabled={importing}
                >
                  Cancel
                </button>
                <button
                  onClick={handleImport}
                  disabled={!importFile || importing}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {importing ? 'Importing...' : 'Import'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

