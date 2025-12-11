'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardHeader, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Table, TableHeader, TableRow, TableHead, TableCell, TableBody } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { useSuperAdminAuth } from '@/contexts/SuperAdminAuthContext';
import { apiConfig } from '@/lib/api-config';
import {
  CurrencyDollarIcon,
  ArrowLeftIcon,
  PencilIcon,
  EyeIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

interface BillingConfig {
  id: number;
  tenant_id: number;
  tenant_name: string;
  fixed_monthly_cost: number;
  per_node_enabled: boolean;
  per_node_cost: number;
  node_count_override: number | null;
  per_ticket_received_enabled: boolean;
  per_ticket_received_cost: number;
  per_ticket_resolved_enabled: boolean;
  per_ticket_resolved_cost: number;
  per_execution_enabled: boolean;
  per_execution_cost: number;
  per_api_call_enabled: boolean;
  per_api_call_cost: number;
  per_llm_token_enabled: boolean;
  per_llm_token_cost: number;
  billing_cycle: string;
  billing_day: number;
  is_active: boolean;
}

interface BillingPreview {
  tenant_id: number;
  tenant_name: string;
  period_start: string;
  period_end: string;
  fixed_cost: number;
  node_cost: number;
  node_count: number;
  ticket_received_cost: number;
  ticket_resolved_cost: number;
  execution_cost: number;
  api_call_cost: number;
  llm_token_cost: number;
  total_cost: number;
  usage: {
    tickets_received: number;
    tickets_resolved: number;
    execution_sessions: number;
    api_calls: number;
    llm_tokens: number;
    active_nodes: number;
  };
  breakdown: Record<string, any>;
}

export default function BillingPage() {
  const router = useRouter();
  const { token } = useSuperAdminAuth();
  const [tenants, setTenants] = useState<any[]>([]);
  const [billingConfigs, setBillingConfigs] = useState<Map<number, BillingConfig>>(new Map());
  const [previews, setPreviews] = useState<Map<number, BillingPreview>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTenant, setSelectedTenant] = useState<number | null>(null);
  const [previewTenant, setPreviewTenant] = useState<number | null>(null);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [configForm, setConfigForm] = useState<Partial<BillingConfig>>({});

  useEffect(() => {
    fetchTenants();
  }, []);

  const fetchTenants = async () => {
    setLoading(true);
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.tenants(), {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setTenants(data.tenants || []);
        
        // Fetch billing configs for all tenants
        for (const tenant of data.tenants || []) {
          await fetchBillingConfig(tenant.id);
        }
      } else {
        setError('Failed to fetch tenants');
      }
    } catch (err) {
      setError('Error fetching tenants');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchBillingConfig = async (tenantId: number) => {
    try {
      const response = await fetch(`${apiConfig.baseURL || ''}/api/v1/billing/config/${tenantId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const config = await response.json();
        setBillingConfigs(prev => new Map(prev).set(tenantId, config));
      }
    } catch (err) {
      console.error(`Failed to fetch billing config for tenant ${tenantId}:`, err);
    }
  };

  const fetchBillingPreview = async (tenantId: number) => {
    try {
      const response = await fetch(`${apiConfig.baseURL || ''}/api/v1/billing/preview/${tenantId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const preview = await response.json();
        setPreviews(prev => new Map(prev).set(tenantId, preview));
        setPreviewTenant(tenantId);
        setShowPreviewModal(true);
      }
    } catch (err) {
      console.error(`Failed to fetch billing preview for tenant ${tenantId}:`, err);
      setError('Failed to fetch billing preview');
    }
  };

  const handleEditConfig = (tenantId: number) => {
    const config = billingConfigs.get(tenantId);
    setSelectedTenant(tenantId);
    setConfigForm(config || {
      tenant_id: tenantId,
      fixed_monthly_cost: 0,
      per_node_enabled: false,
      per_node_cost: 0,
      per_ticket_received_enabled: false,
      per_ticket_received_cost: 0,
      per_ticket_resolved_enabled: false,
      per_ticket_resolved_cost: 0,
      per_execution_enabled: false,
      per_execution_cost: 0,
      per_api_call_enabled: false,
      per_api_call_cost: 0,
      per_llm_token_enabled: false,
      per_llm_token_cost: 0,
      billing_cycle: 'monthly',
      billing_day: 1,
      is_active: true,
    });
    setShowConfigModal(true);
  };

  const handleSaveConfig = async () => {
    if (!selectedTenant) return;
    
    try {
      const response = await fetch(`${apiConfig.baseURL || ''}/api/v1/billing/config/${selectedTenant}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(configForm),
      });
      
      if (response.ok) {
        await fetchBillingConfig(selectedTenant);
        setShowConfigModal(false);
        setSelectedTenant(null);
        setConfigForm({});
      } else {
        const error = await response.json();
        setError(error.detail || 'Failed to save billing config');
      }
    } catch (err) {
      setError('Error saving billing config');
      console.error(err);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-neutral-50">
      {/* Header */}
      <header className="bg-white border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.push('/super-admin')}
                className="p-2 hover:bg-neutral-100 rounded-lg transition"
              >
                <ArrowLeftIcon className="h-5 w-5 text-neutral-600" />
              </button>
              <div className="flex items-center space-x-3">
                <div className="rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 p-2.5 shadow-lg">
                  <CurrencyDollarIcon className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-neutral-900">Billing Management</h1>
                  <p className="text-sm text-neutral-600">Configure tenant billing</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 p-4 bg-error-50 border border-error-200 rounded-lg">
            <p className="text-error-800">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-neutral-600">Loading billing configurations...</p>
          </div>
        ) : (
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-neutral-900">Tenant Billing Configurations</h2>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tenant</TableHead>
                    <TableHead>Fixed Cost</TableHead>
                    <TableHead>Per-Node</TableHead>
                    <TableHead>Per-Ticket (R)</TableHead>
                    <TableHead>Per-Ticket (Res)</TableHead>
                    <TableHead>Per-Execution</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tenants.map((tenant) => {
                    const config = billingConfigs.get(tenant.id);
                    return (
                      <TableRow key={tenant.id}>
                        <TableCell className="font-medium">{tenant.name}</TableCell>
                        <TableCell>{formatCurrency(config?.fixed_monthly_cost || 0)}</TableCell>
                        <TableCell>
                          {config?.per_node_enabled ? (
                            <span className="text-sm">{formatCurrency(config.per_node_cost)}/node</span>
                          ) : (
                            <span className="text-neutral-400">Disabled</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {config?.per_ticket_received_enabled ? (
                            <span className="text-sm">{formatCurrency(config.per_ticket_received_cost)}/ticket</span>
                          ) : (
                            <span className="text-neutral-400">Disabled</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {config?.per_ticket_resolved_enabled ? (
                            <span className="text-sm">{formatCurrency(config.per_ticket_resolved_cost)}/ticket</span>
                          ) : (
                            <span className="text-neutral-400">Disabled</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {config?.per_execution_enabled ? (
                            <span className="text-sm">{formatCurrency(config.per_execution_cost)}/exec</span>
                          ) : (
                            <span className="text-neutral-400">Disabled</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {config?.is_active ? (
                            <Badge variant="success">Active</Badge>
                          ) : (
                            <Badge variant="secondary">Inactive</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => fetchBillingPreview(tenant.id)}
                              className="p-2 hover:bg-neutral-100 rounded-lg transition"
                              title="Preview Billing"
                            >
                              <EyeIcon className="h-4 w-4 text-neutral-600" />
                            </button>
                            <button
                              onClick={() => handleEditConfig(tenant.id)}
                              className="p-2 hover:bg-neutral-100 rounded-lg transition"
                              title="Edit Configuration"
                            >
                              <PencilIcon className="h-4 w-4 text-primary-600" />
                            </button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* Config Modal */}
        {showConfigModal && selectedTenant && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">Edit Billing Configuration</h2>
                  <button
                    onClick={() => {
                      setShowConfigModal(false);
                      setSelectedTenant(null);
                      setConfigForm({});
                    }}
                    className="p-2 hover:bg-neutral-100 rounded-lg"
                  >
                    <XCircleIcon className="h-5 w-5" />
                  </button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {/* Fixed Monthly Cost */}
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Fixed Monthly Cost (₹)
                    </label>
                    <Input
                      type="number"
                      step="0.01"
                      value={configForm.fixed_monthly_cost || 0}
                      onChange={(e) => setConfigForm({ ...configForm, fixed_monthly_cost: parseFloat(e.target.value) || 0 })}
                    />
                  </div>

                  {/* Per-Node */}
                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between mb-4">
                      <label className="block text-sm font-medium text-neutral-700">
                        Per-Node Billing
                      </label>
                      <input
                        type="checkbox"
                        checked={configForm.per_node_enabled || false}
                        onChange={(e) => setConfigForm({ ...configForm, per_node_enabled: e.target.checked })}
                        className="h-4 w-4"
                      />
                    </div>
                    {configForm.per_node_enabled && (
                      <div className="space-y-4 ml-6">
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 mb-2">
                            Cost per Node per Month (₹)
                          </label>
                          <Input
                            type="number"
                            step="0.01"
                            value={configForm.per_node_cost || 0}
                            onChange={(e) => setConfigForm({ ...configForm, per_node_cost: parseFloat(e.target.value) || 0 })}
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 mb-2">
                            Node Count Override (leave empty for auto-calculate)
                          </label>
                          <Input
                            type="number"
                            value={configForm.node_count_override || ''}
                            onChange={(e) => setConfigForm({ ...configForm, node_count_override: e.target.value ? parseInt(e.target.value) : null })}
                            placeholder="Auto-calculate"
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Per-Ticket Received */}
                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between mb-4">
                      <label className="block text-sm font-medium text-neutral-700">
                        Per-Ticket-Received Billing
                      </label>
                      <input
                        type="checkbox"
                        checked={configForm.per_ticket_received_enabled || false}
                        onChange={(e) => setConfigForm({ ...configForm, per_ticket_received_enabled: e.target.checked })}
                        className="h-4 w-4"
                      />
                    </div>
                    {configForm.per_ticket_received_enabled && (
                      <div className="ml-6">
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          Cost per Ticket Received (₹)
                        </label>
                        <Input
                          type="number"
                          step="0.01"
                          value={configForm.per_ticket_received_cost || 0}
                          onChange={(e) => setConfigForm({ ...configForm, per_ticket_received_cost: parseFloat(e.target.value) || 0 })}
                        />
                      </div>
                    )}
                  </div>

                  {/* Per-Ticket Resolved */}
                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between mb-4">
                      <label className="block text-sm font-medium text-neutral-700">
                        Per-Ticket-Resolved Billing
                      </label>
                      <input
                        type="checkbox"
                        checked={configForm.per_ticket_resolved_enabled || false}
                        onChange={(e) => setConfigForm({ ...configForm, per_ticket_resolved_enabled: e.target.checked })}
                        className="h-4 w-4"
                      />
                    </div>
                    {configForm.per_ticket_resolved_enabled && (
                      <div className="ml-6">
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          Cost per Ticket Resolved (₹)
                        </label>
                        <Input
                          type="number"
                          step="0.01"
                          value={configForm.per_ticket_resolved_cost || 0}
                          onChange={(e) => setConfigForm({ ...configForm, per_ticket_resolved_cost: parseFloat(e.target.value) || 0 })}
                        />
                      </div>
                    )}
                  </div>

                  {/* Per-Execution */}
                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between mb-4">
                      <label className="block text-sm font-medium text-neutral-700">
                        Per-Execution Billing
                      </label>
                      <input
                        type="checkbox"
                        checked={configForm.per_execution_enabled || false}
                        onChange={(e) => setConfigForm({ ...configForm, per_execution_enabled: e.target.checked })}
                        className="h-4 w-4"
                      />
                    </div>
                    {configForm.per_execution_enabled && (
                      <div className="ml-6">
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          Cost per Execution (₹)
                        </label>
                        <Input
                          type="number"
                          step="0.01"
                          value={configForm.per_execution_cost || 0}
                          onChange={(e) => setConfigForm({ ...configForm, per_execution_cost: parseFloat(e.target.value) || 0 })}
                        />
                      </div>
                    )}
                  </div>

                  {/* Active Status */}
                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between">
                      <label className="block text-sm font-medium text-neutral-700">
                        Active
                      </label>
                      <input
                        type="checkbox"
                        checked={configForm.is_active !== false}
                        onChange={(e) => setConfigForm({ ...configForm, is_active: e.target.checked })}
                        className="h-4 w-4"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end space-x-4 pt-4 border-t">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setShowConfigModal(false);
                        setSelectedTenant(null);
                        setConfigForm({});
                      }}
                    >
                      Cancel
                    </Button>
                    <Button onClick={handleSaveConfig}>
                      Save Configuration
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Preview Modal */}
        {showPreviewModal && previewTenant && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">Billing Preview</h2>
                  <button
                    onClick={() => {
                      setShowPreviewModal(false);
                      setPreviewTenant(null);
                    }}
                    className="p-2 hover:bg-neutral-100 rounded-lg"
                  >
                    <XCircleIcon className="h-5 w-5" />
                  </button>
                </div>
              </CardHeader>
              <CardContent>
                {previews.get(previewTenant) && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-neutral-600">Period</p>
                        <p className="font-medium">
                          {new Date(previews.get(previewTenant)!.period_start).toLocaleDateString()} - {new Date(previews.get(previewTenant)!.period_end).toLocaleDateString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-neutral-600">Total Cost</p>
                        <p className="text-2xl font-bold text-primary-600">
                          {formatCurrency(previews.get(previewTenant)!.total_cost)}
                        </p>
                      </div>
                    </div>
                    <div className="border-t pt-4">
                      <h3 className="font-semibold mb-2">Cost Breakdown</h3>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span>Fixed Cost:</span>
                          <span>{formatCurrency(previews.get(previewTenant)!.fixed_cost)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Node Cost ({previews.get(previewTenant)!.node_count} nodes):</span>
                          <span>{formatCurrency(previews.get(previewTenant)!.node_cost)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Ticket Received ({previews.get(previewTenant)!.usage.tickets_received} tickets):</span>
                          <span>{formatCurrency(previews.get(previewTenant)!.ticket_received_cost)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Ticket Resolved ({previews.get(previewTenant)!.usage.tickets_resolved} tickets):</span>
                          <span>{formatCurrency(previews.get(previewTenant)!.ticket_resolved_cost)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Executions ({previews.get(previewTenant)!.usage.execution_sessions} sessions):</span>
                          <span>{formatCurrency(previews.get(previewTenant)!.execution_cost)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </main>
    </div>
  );
}

