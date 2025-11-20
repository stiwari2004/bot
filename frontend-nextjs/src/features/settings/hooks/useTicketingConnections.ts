'use client';

import { useState, useCallback } from 'react';
import { apiConfig } from '@/lib/api-config';
import type { TicketingConnection } from '../types';

export function useTicketingConnections(
  onRefresh: () => void,
  onSuccess: (message: string) => void,
  onError: (message: string) => void
) {
  const [editingConnection, setEditingConnection] = useState<TicketingConnection | null>(null);

  const handleTestConnection = useCallback(async (connectionId: number) => {
    try {
      const response = await fetch(apiConfig.endpoints.settings.ticketingConnectionTest(connectionId), {
        method: 'POST',
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Connection test failed');
      }
      const data = await response.json();
      onSuccess(data.message || 'Connection test successful');
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to test connection');
    }
  }, [onSuccess, onError]);

  const handleToggleConnection = useCallback(async (connectionId: number, isActive: boolean) => {
    try {
      const response = await fetch(apiConfig.endpoints.settings.ticketingConnection(connectionId), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !isActive }),
      });
      if (!response.ok) {
        throw new Error('Failed to toggle connection');
      }
      onRefresh();
      onSuccess(`Connection ${!isActive ? 'enabled' : 'disabled'} successfully`);
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to toggle connection');
    }
  }, [onRefresh, onSuccess, onError]);

  const handleAuthorizeConnection = useCallback(async (connectionId: number, toolName: string) => {
    try {
      const response = await fetch(
        `${apiConfig.endpoints.settings.ticketingConnections()}/${connectionId}/oauth/authorize`,
        { method: 'POST' }
      );
      if (!response.ok) {
        const errorData = await response.json();
        const errorMessage = errorData.detail || 'Failed to get authorization URL';
        
        // For ManageEngine, provide helpful guidance if credentials are missing
        if (toolName === 'manageengine' && errorMessage.includes('Client ID not configured')) {
          onError('Please configure OAuth credentials first. Click "Edit" to add your Client ID and Client Secret before authorizing.');
          return;
        }
        
        throw new Error(errorMessage);
      }
      const data = await response.json();
      if (data.authorization_url) {
        window.location.href = data.authorization_url;
      }
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to authorize connection');
    }
  }, [onError]);

  const handleDeleteConnection = useCallback(async (connectionId: number) => {
    if (!confirm('Are you sure you want to delete this connection?')) return;
    
    try {
      const response = await fetch(apiConfig.endpoints.settings.ticketingConnection(connectionId), {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error('Failed to delete connection');
      }
      onRefresh();
      onSuccess('Connection deleted successfully');
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to delete connection');
    }
  }, [onRefresh, onSuccess, onError]);

  return {
    editingConnection,
    setEditingConnection,
    handleTestConnection,
    handleToggleConnection,
    handleAuthorizeConnection,
    handleDeleteConnection,
  };
}

