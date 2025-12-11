'use client';

import { useState } from 'react';
import { PlusIcon, WrenchScrewdriverIcon, ArrowUpTrayIcon } from '@heroicons/react/24/outline';
import type { InfrastructureConnection, Credential } from '../types';
import { useInfrastructureConnections } from '../hooks/useInfrastructureConnections';
import { apiConfig } from '@/lib/api-config';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

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
    <Card variant="elevated">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-neutral-900 mb-1">
              Infrastructure Connections
            </h3>
            <p className="text-sm text-neutral-600">
              Manage cloud and infrastructure connections (Azure, GCP, AWS, SSH, etc.)
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              variant="success"
              size="sm"
              onClick={() => setShowImport(true)}
              leftIcon={<ArrowUpTrayIcon className="h-5 w-5" />}
            >
              Import from Excel
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={onShowAddCredential}
              leftIcon={<PlusIcon className="h-5 w-5" />}
            >
              Add Credential
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={onShowAddConnection}
              leftIcon={<PlusIcon className="h-5 w-5" />}
            >
              Add Connection
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent padding="md">
        {connections.length === 0 ? (
          <div className="text-center py-12">
            <div className="mx-auto w-16 h-16 rounded-full bg-neutral-100 flex items-center justify-center mb-4">
              <WrenchScrewdriverIcon className="h-8 w-8 text-neutral-400" />
            </div>
            <p className="text-neutral-700 font-medium mb-1">No infrastructure connections configured</p>
            <p className="text-sm text-neutral-500">Add credentials and connections to enable cloud access</p>
          </div>
        ) : (
          <div className="space-y-4">
            {connections.map((connection) => (
              <Card key={connection.id} variant="default">
                <CardContent padding="md">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-3 flex-wrap">
                        <h4 className="font-semibold text-neutral-900">
                          {connection.name}
                        </h4>
                        <Badge variant="primary" size="sm" className="capitalize">
                          {connection.type.replace('_', ' ')}
                        </Badge>
                        <Badge variant="secondary" size="sm">
                          {connection.environment}
                        </Badge>
                      </div>
                      {connection.target_host && (
                        <p className="text-sm text-neutral-600 mb-2">
                          Host: <code className="bg-neutral-100 px-2 py-1 rounded text-xs font-mono">{connection.target_host}</code>
                          {connection.target_port && <span className="ml-2">Port: {connection.target_port}</span>}
                        </p>
                      )}
                      {connection.target_service && (
                        <p className="text-sm text-neutral-600 mb-2">
                          Service: <code className="bg-neutral-100 px-2 py-1 rounded text-xs font-mono">{connection.target_service}</code>
                        </p>
                      )}
                      {connection.credential_id && (
                        <p className="text-xs text-neutral-500 mt-2">
                          Credential ID: {connection.credential_id}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-wrap">
                      {(connection.type === 'cloud_account' || connection.type === 'azure_subscription' || connection.type === 'azure_bastion') && (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleTestConnection(connection.id)}
                            title="Test Connection"
                          >
                            Test
                          </Button>
                          <Button
                            variant="success"
                            size="sm"
                            onClick={() => handleDiscoverResources(connection.id)}
                            title="Discover Resources"
                          >
                            Discover
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={async () => {
                              await handleTestCommand(connection.id);
                              onShowTestCommand(connection);
                            }}
                            title="Test Command Execution"
                          >
                            Test Command
                          </Button>
                        </>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onEditConnection(connection)}
                        title="Edit Connection"
                      >
                        Edit
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleDeleteConnection(connection.id)}
                        title="Delete Connection"
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Import Modal */}
        {showImport && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <Card variant="elevated" className="max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <h2 className="text-2xl font-bold text-neutral-900">Import Infrastructure Connections from Excel</h2>
              </CardHeader>
              <CardContent padding="md">
                <div className="mb-6">
                  <p className="text-sm text-neutral-600 mb-3">
                    Upload an Excel file (.xlsx) with the following columns:
                  </p>
                  <Card variant="outlined" className="bg-neutral-50">
                    <CardContent padding="sm">
                      <p className="font-semibold mb-2 text-neutral-900">Required columns:</p>
                      <ul className="list-disc list-inside text-neutral-700 mb-3 text-sm space-y-1">
                        <li>name (or hostname, device_name, connection_name)</li>
                        <li>target_host (or host, ip, ip_address, management_ip)</li>
                        <li>connection_type (ssh, network_device, database, api, etc.)</li>
                      </ul>
                      <p className="font-semibold mb-2 text-neutral-900">Optional columns:</p>
                      <ul className="list-disc list-inside text-neutral-700 text-sm space-y-1">
                        <li>target_port, environment, username, password</li>
                        <li>For network devices: vendor, model, device_type, location, network_segment, site, serial_number, firmware_version, snmp_community, snmp_version</li>
                      </ul>
                    </CardContent>
                  </Card>
                </div>

                <div className="mb-6">
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">Select Excel File</label>
                  <input
                    type="file"
                    accept=".xlsx,.xls"
                    onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                  />
                </div>

                {importResult && (
                  <Card variant="outlined" className="mb-6 bg-neutral-50">
                    <CardContent padding="md">
                      <p className="font-semibold mb-3 text-neutral-900">{importResult.message}</p>
                      {importResult.imported && importResult.imported.length > 0 && (
                        <div className="mb-3">
                          <p className="text-sm text-success-700 font-semibold mb-2">Imported ({importResult.imported.length}):</p>
                          <ul className="text-xs text-neutral-600 mt-1 space-y-1">
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
                          <p className="text-sm text-error-700 font-semibold mb-2">Errors ({importResult.errors.length}):</p>
                          <ul className="text-xs text-neutral-600 mt-1 space-y-1">
                            {importResult.errors.slice(0, 5).map((error: any, idx: number) => (
                              <li key={idx}>• Row {error.row}: {error.error}</li>
                            ))}
                            {importResult.errors.length > 5 && (
                              <li>... and {importResult.errors.length - 5} more errors</li>
                            )}
                          </ul>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                <div className="flex justify-end gap-3">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowImport(false);
                      setImportFile(null);
                      setImportResult(null);
                    }}
                    disabled={importing}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="primary"
                    onClick={handleImport}
                    disabled={!importFile || importing}
                    isLoading={importing}
                  >
                    {importing ? 'Importing...' : 'Import'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

