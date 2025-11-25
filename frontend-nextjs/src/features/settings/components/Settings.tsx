'use client';

import { useState } from 'react';
import {
  Cog6ToothIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useSettings } from '../hooks/useSettings';
import { ExecutionModeSection } from './ExecutionModeSection';
import { TicketingConnectionsSection } from './TicketingConnectionsSection';
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
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-gray-600">Loading settings...</div>
        </div>
      </div>
    );
  }

  const handleSuccess = (message: string) => {
    setSuccess(message);
    setTimeout(() => setSuccess(null), 3000);
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2 flex items-center">
          <Cog6ToothIcon className="h-7 w-7 mr-2 text-blue-600" />
          Settings & Connections
        </h2>
        <p className="text-gray-600">Configure system behavior and connect to ticketing tools</p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />
            <p className="text-red-800 font-medium">Error</p>
          </div>
          <p className="text-red-700 mt-2 text-sm">{error}</p>
        </div>
      )}

      {success && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center gap-2">
            <CheckCircleIcon className="h-5 w-5 text-green-600" />
            <p className="text-green-800 font-medium">{success}</p>
          </div>
        </div>
      )}

      <ExecutionModeSection
        executionMode={executionMode}
        saving={saving}
        onModeChange={handleModeChange}
      />

      <div className="mb-6">
        <BenchmarkConfigurationSection
          onSuccess={handleSuccess}
          onError={(msg) => setError(msg)}
        />
      </div>

      <div className="mb-6">
        <InfrastructureThresholdSection
          onSuccess={handleSuccess}
          onError={(msg) => setError(msg)}
        />
      </div>

      <TicketingConnectionsSection
        connections={ticketingConnections}
        availableTools={availableTools}
        onRefresh={fetchTicketingConnections}
        onSuccess={handleSuccess}
        onError={(msg) => setError(msg)}
        onShowAddModal={() => setShowAddConnection(true)}
        editingConnection={editingConnection}
        onShowEditModal={setEditingConnection}
      />

      <InfrastructureConnectionsSection
        connections={infrastructureConnections}
        credentials={credentials}
        onRefresh={fetchInfrastructureConnections}
        onSuccess={handleSuccess}
        onError={(msg) => setError(msg)}
        onShowAddCredential={() => setShowAddCredential(true)}
        onShowAddConnection={() => setShowAddInfraConnection(true)}
        onEditConnection={setEditingInfraConnection}
        onShowTestCommand={(connection) => {
          setTestCommandConnection(connection);
          setShowTestCommand(true);
        }}
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

