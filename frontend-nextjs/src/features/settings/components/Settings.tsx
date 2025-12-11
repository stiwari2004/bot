'use client';

import { useState } from 'react';
import {
  Cog6ToothIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useSettings } from '../hooks/useSettings';
import { Card, CardContent } from '@/components/ui/Card';
import { ExecutionModeSection } from './ExecutionModeSection';
import { TicketingConnectionsSection } from './TicketingConnectionsSection';
import { MonitoringConnectionsSection } from './MonitoringConnectionsSection';
import { InfrastructureConnectionsSection } from './InfrastructureConnectionsSection';
import { BenchmarkConfigurationSection } from './BenchmarkConfigurationSection';
import { InfrastructureThresholdSection } from './InfrastructureThresholdSection';
import { AddConnectionModal } from './AddConnectionModal';
import { EditConnectionModal } from './EditConnectionModal';
import { AddCredentialModal } from './AddCredentialModal';
import { AddInfrastructureConnectionModal } from './AddInfrastructureConnectionModal';
import { EditInfrastructureConnectionModal } from './EditInfrastructureConnectionModal';
import { TestCommandModal } from './TestCommandModal';
import { useInfrastructureConnections } from '../hooks/useInfrastructureConnections';
import type { InfrastructureConnection } from '../types';

export function Settings() {
  const [showAddConnection, setShowAddConnection] = useState(false);
  const [editingConnection, setEditingConnection] = useState<any>(null);
  const [showAddInfraConnection, setShowAddInfraConnection] = useState(false);
  const [showAddCredential, setShowAddCredential] = useState(false);
  const [editingInfraConnection, setEditingInfraConnection] = useState<InfrastructureConnection | null>(null);
  const [testCommandConnection, setTestCommandConnection] = useState<InfrastructureConnection | null>(null);
  const [showTestCommand, setShowTestCommand] = useState(false);
  const [showAddMonitoringConnection, setShowAddMonitoringConnection] = useState(false);

  const {
    executionMode,
    ticketingConnections,
    availableTools,
    infrastructureConnections,
    credentials,
    loading,
    saving,
    error,
    success,
    setError,
    setSuccess,
    handleModeChange,
    fetchTicketingConnections,
    fetchInfrastructureConnections,
    fetchCredentials,
    monitoringConnections,
    fetchMonitoringConnections,
  } = useSettings();

  const infrastructureHooks = useInfrastructureConnections(
    fetchInfrastructureConnections,
    (msg) => {
      setSuccess(msg);
      setTimeout(() => setSuccess(null), 3000);
    },
    (msg) => setError(msg)
  );
  
  const { discoveredVMs } = infrastructureHooks;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <div className="text-neutral-600 font-medium">Loading settings...</div>
        </div>
      </div>
    );
  }

  const handleSuccess = (message: string) => {
    setSuccess(message);
    setTimeout(() => setSuccess(null), 3000);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="mb-6">
        <h2 className="text-3xl font-bold text-neutral-900 mb-2 flex items-center">
          <div className="mr-3 p-2 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500">
            <Cog6ToothIcon className="h-7 w-7 text-white" />
          </div>
          Settings & Connections
        </h2>
        <p className="text-neutral-600 text-lg">Configure system behavior and connect to ticketing tools</p>
      </div>

      {error && (
        <Card variant="outlined" className="border-error-200 bg-error-50">
          <CardContent padding="md">
            <div className="flex items-center gap-3">
              <ExclamationTriangleIcon className="h-5 w-5 text-error-600 flex-shrink-0" />
              <div>
                <p className="text-error-800 font-semibold">Error</p>
                <p className="text-error-700 mt-1 text-sm">{error}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {success && (
        <Card variant="outlined" className="border-success-200 bg-success-50">
          <CardContent padding="md">
            <div className="flex items-center gap-3">
              <CheckCircleIcon className="h-5 w-5 text-success-600 flex-shrink-0" />
              <p className="text-success-800 font-semibold">{success}</p>
            </div>
          </CardContent>
        </Card>
      )}

      <ExecutionModeSection
        executionMode={executionMode}
        saving={saving}
        onModeChange={handleModeChange}
      />

      <div className="mb-6">
        <BenchmarkConfigurationSection
          onSuccess={handleSuccess}
          onError={(msg: string) => setError(msg)}
        />
      </div>

      <div className="mb-6">
        <InfrastructureThresholdSection
          onSuccess={handleSuccess}
          onError={(msg: string) => setError(msg)}
        />
      </div>

      <TicketingConnectionsSection
        connections={ticketingConnections}
        availableTools={availableTools}
        onRefresh={fetchTicketingConnections}
        onSuccess={handleSuccess}
        onError={(msg: string) => setError(msg)}
        onShowAddModal={() => setShowAddConnection(true)}
        editingConnection={editingConnection}
        onShowEditModal={setEditingConnection}
      />

        <InfrastructureConnectionsSection
        connections={infrastructureConnections}
        credentials={credentials}
        onRefresh={fetchInfrastructureConnections}
        onSuccess={handleSuccess}
        onError={(msg: string) => setError(msg)}
        onShowAddCredential={() => setShowAddCredential(true)}
        onShowAddConnection={() => setShowAddInfraConnection(true)}
        onEditConnection={setEditingInfraConnection}
        onShowTestCommand={(connection) => {
          setTestCommandConnection(connection);
          setShowTestCommand(true);
        }}
      />

      <MonitoringConnectionsSection
        connections={monitoringConnections}
        onRefresh={fetchMonitoringConnections}
        onSuccess={handleSuccess}
        onError={(msg: string) => setError(msg)}
      />

      {/* Modals */}
      {showAddConnection && (
        <AddConnectionModal
          availableTools={availableTools}
          onClose={() => setShowAddConnection(false)}
          onSuccess={() => {
            setShowAddConnection(false);
            fetchTicketingConnections();
            handleSuccess('Connection added successfully');
          }}
        />
      )}

      {editingConnection && (
        <EditConnectionModal
          connection={editingConnection}
          availableTools={availableTools}
          onClose={() => setEditingConnection(null)}
          onSuccess={() => {
            setEditingConnection(null);
            fetchTicketingConnections();
            handleSuccess('Connection updated successfully');
          }}
        />
      )}

      {showAddCredential && (
        <AddCredentialModal
          onClose={() => setShowAddCredential(false)}
          onSuccess={() => {
            setShowAddCredential(false);
            fetchCredentials();
            handleSuccess('Credential added successfully');
          }}
        />
      )}

      {showAddInfraConnection && (
        <AddInfrastructureConnectionModal
          credentials={credentials}
          onClose={() => setShowAddInfraConnection(false)}
          onSuccess={() => {
            setShowAddInfraConnection(false);
            fetchInfrastructureConnections();
            handleSuccess('Infrastructure connection added successfully');
          }}
        />
      )}

      {editingInfraConnection && (
        <EditInfrastructureConnectionModal
          connection={editingInfraConnection}
          credentials={credentials}
          onClose={() => setEditingInfraConnection(null)}
          onSuccess={() => {
            setEditingInfraConnection(null);
            fetchInfrastructureConnections();
            handleSuccess('Connection updated successfully');
          }}
        />
      )}

      {showTestCommand && testCommandConnection && (
        <TestCommandModal
          connection={testCommandConnection}
          discoveredVMs={discoveredVMs}
          onClose={() => {
            setShowTestCommand(false);
            setTestCommandConnection(null);
          }}
        />
      )}
    </div>
  );
}

