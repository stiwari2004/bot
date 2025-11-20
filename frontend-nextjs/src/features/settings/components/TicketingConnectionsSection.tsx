'use client';

import { PlusIcon, LinkIcon } from '@heroicons/react/24/outline';
import type { TicketingConnection, TicketingTool } from '../types';
import { useTicketingConnections } from '../hooks/useTicketingConnections';

interface TicketingConnectionsSectionProps {
  connections: TicketingConnection[];
  availableTools: TicketingTool[];
  onRefresh: () => void;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
  onShowAddModal: () => void;
  editingConnection: TicketingConnection | null;
  onShowEditModal: (connection: TicketingConnection) => void;
}

const getStatusColor = (status: string | null) => {
  switch (status) {
    case 'success':
      return 'bg-green-100 text-green-800';
    case 'failed':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

export function TicketingConnectionsSection({
  connections,
  availableTools,
  onRefresh,
  onSuccess,
  onError,
  onShowAddModal,
  editingConnection,
  onShowEditModal,
}: TicketingConnectionsSectionProps) {
  const {
    handleTestConnection,
    handleToggleConnection,
    handleAuthorizeConnection,
    handleDeleteConnection,
  } = useTicketingConnections(onRefresh, onSuccess, onError);

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm mb-6">
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Ticketing Tool Connections
            </h3>
            <p className="text-sm text-gray-600">
              Connect to external ticketing tools to receive tickets automatically
            </p>
          </div>
          <button
            onClick={onShowAddModal}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <PlusIcon className="h-5 w-5" />
            Add Connection
          </button>
        </div>

        {connections.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <LinkIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p>No ticketing tool connections configured</p>
            <p className="text-sm mt-2">Click "Add Connection" to connect to ServiceNow, Zendesk, Jira, etc.</p>
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
                      <h4 className="font-medium text-gray-900 capitalize">
                        {connection.tool_name.replace('_', ' ')}
                      </h4>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        connection.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {connection.is_active ? 'Active' : 'Inactive'}
                      </span>
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {connection.connection_type}
                      </span>
                      {connection.last_sync_status && (
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(connection.last_sync_status)}`}>
                          {connection.last_sync_status}
                        </span>
                      )}
                    </div>
                    {connection.webhook_url && (
                      <p className="text-sm text-gray-600 mb-1">
                        Webhook: <code className="bg-gray-100 px-2 py-1 rounded text-xs">{connection.webhook_url}</code>
                      </p>
                    )}
                    {connection.api_base_url && (
                      <p className="text-sm text-gray-600 mb-1">
                        API: <code className="bg-gray-100 px-2 py-1 rounded text-xs">{connection.api_base_url}</code>
                      </p>
                    )}
                    {connection.last_sync_at && (
                      <p className="text-xs text-gray-500 mt-2">
                        Last sync: {new Date(connection.last_sync_at).toLocaleString()}
                      </p>
                    )}
                    {connection.last_error && (
                      <p className="text-xs text-red-600 mt-1">
                        Error: {connection.last_error}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    {(connection.tool_name === 'zoho' || connection.tool_name === 'manageengine') && connection.connection_type === 'api_poll' && (
                      <>
                        {connection.oauth_authorized ? (
                          <span className="px-3 py-1 text-sm bg-green-100 text-green-800 rounded-lg">
                            ✓ Authorized
                          </span>
                        ) : (
                          <button
                            onClick={() => handleAuthorizeConnection(connection.id, connection.tool_name)}
                            className="px-3 py-1 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                            title={connection.tool_name === 'zoho' ? 'Authorize Zoho OAuth' : 'Authorize ManageEngine OAuth'}
                          >
                            Authorize
                          </button>
                        )}
                      </>
                    )}
                    <button
                      onClick={() => handleTestConnection(connection.id)}
                      className="px-3 py-1 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                      title="Test Connection"
                    >
                      Test
                    </button>
                    <button
                      onClick={() => handleToggleConnection(connection.id, connection.is_active)}
                      className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                        connection.is_active
                          ? 'bg-red-100 text-red-800 hover:bg-red-200'
                          : 'bg-green-100 text-green-800 hover:bg-green-200'
                      }`}
                    >
                      {connection.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      onClick={() => onShowEditModal(connection)}
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

