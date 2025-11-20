'use client';

import { PlusIcon, WrenchScrewdriverIcon } from '@heroicons/react/24/outline';
import type { InfrastructureConnection, Credential } from '../types';
import { useInfrastructureConnections } from '../hooks/useInfrastructureConnections';

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
  const {
    handleTestConnection,
    handleDiscoverResources,
    handleTestCommand,
    handleDeleteConnection,
  } = useInfrastructureConnections(onRefresh, onSuccess, onError);

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
      </div>
    </div>
  );
}

