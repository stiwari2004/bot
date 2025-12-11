'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useState, useEffect } from 'react';
import { apiConfig } from '@/lib/api-config';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';

interface Node {
  id: number;
  name: string;
  connection_type: string;
  target_host: string | null;
  environment: string | null;
  is_active: boolean;
  created_at: string;
}

export function NodeManagement() {
  const { token } = useAuth();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'active' | 'pending'>('all');

  const fetchNodes = async () => {
    if (!token) return;
    
    setLoading(true);
    try {
      const params = filter === 'all' ? '' : `?is_active=${filter === 'active'}`;
      const response = await fetch(apiConfig.endpoints.clientAdmin.nodes() + params, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setNodes(data);
      }
    } catch (error) {
      console.error('Failed to fetch nodes:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchNodes();
    }
  }, [token, filter]);

  const handleActivate = async (nodeId: number) => {
    if (!token) return;

    try {
      const response = await fetch(apiConfig.endpoints.clientAdmin.activateNode(nodeId), {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        fetchNodes();
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to activate node');
      }
    } catch (error) {
      console.error('Failed to activate node:', error);
      alert('Failed to activate node');
    }
  };

  const handleDeactivate = async (nodeId: number) => {
    if (!token) return;
    if (!confirm('Are you sure you want to deactivate this node? It will be removed from billing and execution.')) return;

    try {
      const response = await fetch(apiConfig.endpoints.clientAdmin.deactivateNode(nodeId), {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        fetchNodes();
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to deactivate node');
      }
    } catch (error) {
      console.error('Failed to deactivate node:', error);
      alert('Failed to deactivate node');
    }
  };

  const filteredNodes = nodes.filter(node => {
    if (filter === 'active') return node.is_active;
    if (filter === 'pending') return !node.is_active;
    return true;
  });

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-neutral-900 mb-4">Node Management</h2>
        <div className="flex items-center space-x-4">
          <Button
            variant={filter === 'all' ? 'primary' : 'secondary'}
            onClick={() => setFilter('all')}
          >
            All ({nodes.length})
          </Button>
          <Button
            variant={filter === 'active' ? 'primary' : 'secondary'}
            onClick={() => setFilter('active')}
          >
            Active ({nodes.filter(n => n.is_active).length})
          </Button>
          <Button
            variant={filter === 'pending' ? 'primary' : 'secondary'}
            onClick={() => setFilter('pending')}
          >
            Pending ({nodes.filter(n => !n.is_active).length})
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : (
        <Card>
          <CardContent padding="md">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-neutral-200">
                    <th className="text-left py-3 px-4 font-semibold text-neutral-900">Name</th>
                    <th className="text-left py-3 px-4 font-semibold text-neutral-900">Type</th>
                    <th className="text-left py-3 px-4 font-semibold text-neutral-900">Host</th>
                    <th className="text-left py-3 px-4 font-semibold text-neutral-900">Environment</th>
                    <th className="text-left py-3 px-4 font-semibold text-neutral-900">Status</th>
                    <th className="text-left py-3 px-4 font-semibold text-neutral-900">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredNodes.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-neutral-600">
                        No nodes found
                      </td>
                    </tr>
                  ) : (
                    filteredNodes.map((node) => (
                      <tr key={node.id} className="border-b border-neutral-100 hover:bg-neutral-50">
                        <td className="py-3 px-4 font-medium">{node.name}</td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                            {node.connection_type}
                          </span>
                        </td>
                        <td className="py-3 px-4">{node.target_host || '—'}</td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-800 capitalize">
                            {node.environment || '—'}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            node.is_active ? 'bg-green-100 text-green-800' : 'bg-orange-100 text-orange-800'
                          }`}>
                            {node.is_active ? 'Active' : 'Pending'}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          {node.is_active ? (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleDeactivate(node.id)}
                            >
                              <XCircleIcon className="h-4 w-4 mr-1" />
                              Deactivate
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              onClick={() => handleActivate(node.id)}
                            >
                              <CheckCircleIcon className="h-4 w-4 mr-1" />
                              Activate
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

