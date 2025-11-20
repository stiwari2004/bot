'use client';

import { useState, useCallback } from 'react';
import { apiConfig } from '@/lib/api-config';
import type { InfrastructureConnection } from '../types';

export function useInfrastructureConnections(
  onRefresh: () => void,
  onSuccess: (message: string) => void,
  onError: (message: string) => void
) {
  const [discoveredVMs, setDiscoveredVMs] = useState<any[]>([]);
  const [testCommandConnection, setTestCommandConnection] = useState<InfrastructureConnection | null>(null);
  const [showTestCommand, setShowTestCommand] = useState(false);
  const [testCommandResult, setTestCommandResult] = useState<any>(null);
  const [testCommandLoading, setTestCommandLoading] = useState(false);

  const handleTestConnection = useCallback(async (connectionId: number) => {
    try {
      onError('');
      const url = apiConfig.endpoints.connectors.infrastructureConnectionTest(connectionId);
      const response = await fetch(url, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        let message = data.message;
        if (data.details) {
          if (data.details.virtual_machines !== undefined) {
            message += ` (${data.details.virtual_machines} VMs found)`;
          } else if (data.details.warning) {
            message += ` Warning: ${data.details.warning}`;
          }
        }
        onSuccess(message);
      } else {
        onError(data.message || 'Connection test failed');
      }
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to test connection');
    }
  }, [onSuccess, onError]);

  const handleDiscoverResources = useCallback(async (connectionId: number) => {
    try {
      onError('');
      const url = apiConfig.endpoints.connectors.infrastructureConnectionDiscover(connectionId);
      const response = await fetch(url);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.resources && data.resources.length > 0) {
        const vmList = data.resources.map((vm: any) => vm.name).join(', ');
        onSuccess(`Discovered ${data.total} resource(s): ${vmList.substring(0, 100)}${vmList.length > 100 ? '...' : ''}`);
        setDiscoveredVMs(data.resources);
      } else {
        if (data.warning) {
          if (data.warning.includes('Subscription ID not set')) {
            onError(data.warning + ' Please edit the connection and add Subscription ID in the metadata.');
          } else if (data.warning.includes('Reader')) {
            onError(data.warning + ' Go to Azure Portal → Subscriptions → Access control (IAM) → Add role assignment → Reader → Select your service principal.');
          } else {
            onError(data.warning);
          }
        } else {
          onError('No resources discovered. Possible reasons: 1) No VMs in subscription, 2) Missing Subscription ID, 3) Service principal needs "Reader" role.');
        }
        setDiscoveredVMs([]);
      }
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to discover resources');
      setDiscoveredVMs([]);
    }
  }, [onSuccess, onError]);

  const handleTestCommand = useCallback(async (connectionId: number) => {
    if (discoveredVMs.length === 0) {
      try {
        onError('');
        const url = apiConfig.endpoints.connectors.infrastructureConnectionDiscover(connectionId);
        const response = await fetch(url);
        if (response.ok) {
          const data = await response.json();
          if (data.resources && data.resources.length > 0) {
            setDiscoveredVMs(data.resources);
          } else {
            onError('No VMs discovered. Please click "Discover" first to find available VMs.');
            return;
          }
        } else {
          onError('Failed to discover VMs. Please click "Discover" first.');
          return;
        }
      } catch (err) {
        onError('Failed to discover VMs. Please click "Discover" first.');
        return;
      }
    }
    // Find connection to set as test command connection
    // This will be handled by the component
  }, [discoveredVMs, onError]);

  const handleDeleteConnection = useCallback(async (connectionId: number) => {
    if (!confirm('Are you sure you want to delete this connection?')) return;
    
    try {
      const response = await fetch(
        apiConfig.endpoints.connectors.infrastructureConnection(connectionId),
        { method: 'DELETE' }
      );
      if (response.ok) {
        onRefresh();
        onSuccess('Connection deleted successfully');
      } else {
        onError('Failed to delete connection');
      }
    } catch (err) {
      onError('Failed to delete connection');
    }
  }, [onRefresh, onSuccess, onError]);

  return {
    discoveredVMs,
    setDiscoveredVMs,
    testCommandConnection,
    setTestCommandConnection,
    showTestCommand,
    setShowTestCommand,
    testCommandResult,
    setTestCommandResult,
    testCommandLoading,
    setTestCommandLoading,
    handleTestConnection,
    handleDiscoverResources,
    handleTestCommand,
    handleDeleteConnection,
  };
}

