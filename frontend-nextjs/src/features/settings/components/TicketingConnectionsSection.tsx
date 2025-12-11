'use client';

import { PlusIcon, LinkIcon } from '@heroicons/react/24/outline';
import type { TicketingConnection, TicketingTool } from '../types';
import { useTicketingConnections } from '../hooks/useTicketingConnections';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

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
    <Card variant="elevated">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-neutral-900 mb-1">
              Ticketing Tool Connections
            </h3>
            <p className="text-sm text-neutral-600">
              Connect to external ticketing tools to receive tickets automatically
            </p>
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={onShowAddModal}
            leftIcon={<PlusIcon className="h-5 w-5" />}
          >
            Add Connection
          </Button>
        </div>
      </CardHeader>
      <CardContent padding="md">
        {connections.length === 0 ? (
          <div className="text-center py-12">
            <div className="mx-auto w-16 h-16 rounded-full bg-neutral-100 flex items-center justify-center mb-4">
              <LinkIcon className="h-8 w-8 text-neutral-400" />
            </div>
            <p className="text-neutral-700 font-medium mb-1">No ticketing tool connections configured</p>
            <p className="text-sm text-neutral-500">Click "Add Connection" to connect to ServiceNow, Zendesk, Jira, etc.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {connections.map((connection) => (
              <Card key={connection.id} variant="default">
                <CardContent padding="md">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-3 flex-wrap">
                        <h4 className="font-semibold text-neutral-900 capitalize">
                          {connection.tool_name.replace('_', ' ')}
                        </h4>
                        <Badge variant={connection.is_active ? 'success' : 'secondary'} size="sm">
                          {connection.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                        <Badge variant="primary" size="sm">
                          {connection.connection_type}
                        </Badge>
                        {connection.last_sync_status && (
                          <Badge 
                            variant={connection.last_sync_status === 'success' ? 'success' : connection.last_sync_status === 'failed' ? 'error' : 'secondary'} 
                            size="sm"
                          >
                            {connection.last_sync_status}
                          </Badge>
                        )}
                      </div>
                      {connection.webhook_url && (
                        <p className="text-sm text-neutral-600 mb-2">
                          Webhook: <code className="bg-neutral-100 px-2 py-1 rounded text-xs font-mono">{connection.webhook_url}</code>
                        </p>
                      )}
                      {connection.api_base_url && (
                        <p className="text-sm text-neutral-600 mb-2">
                          API: <code className="bg-neutral-100 px-2 py-1 rounded text-xs font-mono">{connection.api_base_url}</code>
                        </p>
                      )}
                      {connection.last_sync_at && (
                        <p className="text-xs text-neutral-500 mt-2">
                          Last sync: {new Date(connection.last_sync_at).toLocaleString()}
                        </p>
                      )}
                      {connection.last_error && (
                        <p className="text-xs text-error-600 mt-2 font-medium">
                          Error: {connection.last_error}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-wrap">
                      {/* OAuth tools (Zoho, ManageEngine) - show Authorize button */}
                      {(connection.tool_name === 'zoho' || connection.tool_name === 'manageengine') && connection.connection_type === 'api_poll' && (
                        <>
                          {connection.oauth_authorized ? (
                            <Badge variant="success" size="sm">✓ Authorized</Badge>
                          ) : (
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => handleAuthorizeConnection(connection.id, connection.tool_name)}
                              title={connection.tool_name === 'zoho' ? 'Authorize Zoho OAuth' : 'Authorize ManageEngine OAuth'}
                            >
                              Authorize
                            </Button>
                          )}
                        </>
                      )}
                      {/* ServiceNow (Basic Auth) - show authorization status */}
                      {connection.tool_name === 'servicenow' && connection.connection_type === 'api_poll' && (
                        <>
                          {connection.oauth_authorized ? (
                            <Badge variant="success" size="sm">✓ Authorized</Badge>
                          ) : (
                            <Badge variant="warning" size="sm">⚠ Not Authorized</Badge>
                          )}
                        </>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTestConnection(connection.id)}
                        title="Test Connection"
                      >
                        Test
                      </Button>
                      <Button
                        variant={connection.is_active ? 'danger' : 'success'}
                        size="sm"
                        onClick={() => handleToggleConnection(connection.id, connection.is_active)}
                      >
                        {connection.is_active ? 'Disable' : 'Enable'}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onShowEditModal(connection)}
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
      </CardContent>
    </Card>
  );
}



