'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardHeader, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Table, TableHeader, TableRow, TableHead, TableCell, TableBody } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Checkbox } from '@/components/ui/Checkbox';
import { useSuperAdminAuth } from '@/contexts/SuperAdminAuthContext';
import { apiConfig } from '@/lib/api-config';
import {
  KeyIcon,
  ArrowLeftIcon,
  PlusIcon,
  PencilIcon,
  XCircleIcon,
  CheckCircleIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';

interface LicensePlan {
  id: number;
  plan_key: string;
  plan_name: string;
  description: string | null;
  default_max_seats: number;
  default_max_nodes: number;
  default_monthly_price: string | null;
  features: Record<string, boolean>;
  is_active: boolean;
  is_system_plan: boolean;
  is_custom: boolean;
  display_order: number;
  created_at: string;
}

interface Feature {
  [key: string]: string; // feature_name: description
}

export default function LicensePlansPage() {
  const router = useRouter();
  const { token } = useSuperAdminAuth();
  const [plans, setPlans] = useState<LicensePlan[]>([]);
  const [features, setFeatures] = useState<Feature>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<LicensePlan | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [formData, setFormData] = useState({
    plan_key: '',
    plan_name: '',
    description: '',
    default_max_seats: 0,
    default_max_nodes: 0,
    default_monthly_price: '',
    features: {} as Record<string, boolean>,
    display_order: 0,
  });

  useEffect(() => {
    fetchPlans();
    fetchFeatures();
  }, []);

  const fetchPlans = async () => {
    setLoading(true);
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.licensePlans(), {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setPlans(data);
      } else {
        setError('Failed to fetch license plans');
      }
    } catch (err) {
      setError('Error fetching license plans');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchFeatures = async () => {
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.licensePlanFeatures(), {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setFeatures(data.features || {});
      }
    } catch (err) {
      console.error('Failed to fetch features:', err);
    }
  };

  const handleInitialize = async () => {
    if (!confirm('This will create the default license plans (Free, Starter, Professional, Enterprise). Continue?')) {
      return;
    }
    
    setError(null);
    try {
      const response = await fetch(apiConfig.endpoints.superAdmin.initializeLicensePlans(), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        setSuccess('Default license plans initialized successfully');
        setTimeout(() => setSuccess(null), 3000);
        await fetchPlans();
      } else {
        const error = await response.json();
        setError(error.detail || 'Failed to initialize license plans');
      }
    } catch (err) {
      setError('Error initializing license plans');
      console.error(err);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const payload = {
        plan_key: formData.plan_key,
        plan_name: formData.plan_name,
        description: formData.description || null,
        default_max_seats: formData.default_max_seats,
        default_max_nodes: formData.default_max_nodes,
        default_monthly_price: formData.default_monthly_price || null,
        features: formData.features,
        display_order: formData.display_order,
      };
      
      const response = await fetch(apiConfig.endpoints.superAdmin.licensePlans(), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      
      if (response.ok) {
        await fetchPlans();
        setShowCreateModal(false);
        setFormData({
          plan_key: '',
          plan_name: '',
          description: '',
          default_max_seats: 0,
          default_max_nodes: 0,
          default_monthly_price: '',
          features: {},
          display_order: 0,
        });
        setSuccess('License plan created successfully');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        const error = await response.json();
        setError(error.detail || 'Failed to create license plan');
      }
    } catch (err) {
      setError('Error creating license plan');
      console.error(err);
    }
  };

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPlan) return;
    
    setError(null);
    try {
      const payload: any = {};
      if (formData.plan_name !== selectedPlan.plan_name) payload.plan_name = formData.plan_name;
      if (formData.description !== selectedPlan.description) payload.description = formData.description;
      if (formData.default_max_seats !== selectedPlan.default_max_seats) payload.default_max_seats = formData.default_max_seats;
      if (formData.default_max_nodes !== selectedPlan.default_max_nodes) payload.default_max_nodes = formData.default_max_nodes;
      if (formData.default_monthly_price !== selectedPlan.default_monthly_price) payload.default_monthly_price = formData.default_monthly_price;
      if (JSON.stringify(formData.features) !== JSON.stringify(selectedPlan.features)) payload.features = formData.features;
      if (formData.display_order !== selectedPlan.display_order) payload.display_order = formData.display_order;
      
      const response = await fetch(apiConfig.endpoints.superAdmin.licensePlan(selectedPlan.id), {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      
      if (response.ok) {
        await fetchPlans();
        setShowEditModal(false);
        setSelectedPlan(null);
        setSuccess('License plan updated successfully');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        const error = await response.json();
        setError(error.detail || 'Failed to update license plan');
      }
    } catch (err) {
      setError('Error updating license plan');
      console.error(err);
    }
  };

  const openEditModal = (plan: LicensePlan) => {
    setSelectedPlan(plan);
    setFormData({
      plan_key: plan.plan_key,
      plan_name: plan.plan_name,
      description: plan.description || '',
      default_max_seats: plan.default_max_seats,
      default_max_nodes: plan.default_max_nodes,
      default_monthly_price: plan.default_monthly_price || '',
      features: { ...plan.features },
      display_order: plan.display_order,
    });
    setShowEditModal(true);
  };

  const toggleFeature = (featureName: string) => {
    setFormData({
      ...formData,
      features: {
        ...formData.features,
        [featureName]: !formData.features[featureName],
      },
    });
  };

  const formatPrice = (price: string | null) => {
    if (!price || price === 'custom') return 'Custom';
    if (price === '0') return 'Free';
    return `₹${price}/mo`;
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
                  <KeyIcon className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-neutral-900">License Plans</h1>
                  <p className="text-sm text-neutral-600">Manage subscription plans and features</p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              {plans.length === 0 && (
                <Button
                  variant="outline"
                  onClick={handleInitialize}
                >
                  Initialize Default Plans
                </Button>
              )}
              <Button
                variant="primary"
                leftIcon={<PlusIcon className="h-5 w-5" />}
                onClick={() => setShowCreateModal(true)}
              >
                Create Plan
              </Button>
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

        {success && (
          <div className="mb-6 p-4 bg-success-50 border border-success-200 rounded-lg">
            <p className="text-success-800">{success}</p>
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-neutral-600">Loading license plans...</p>
          </div>
        ) : (
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-neutral-900">License Plans</h2>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Plan Name</TableHead>
                    <TableHead>Key</TableHead>
                    <TableHead>Seats</TableHead>
                    <TableHead>Nodes</TableHead>
                    <TableHead>Price</TableHead>
                    <TableHead>Features</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {plans.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center py-8 text-neutral-500">
                        No license plans found. Click "Initialize Default Plans" to create the default plans, or create a custom plan.
                      </TableCell>
                    </TableRow>
                  ) : (
                    plans.map((plan) => (
                      <TableRow key={plan.id}>
                        <TableCell className="font-medium">{plan.plan_name}</TableCell>
                        <TableCell>
                          <code className="text-xs bg-neutral-100 px-2 py-1 rounded">{plan.plan_key}</code>
                        </TableCell>
                        <TableCell>{plan.default_max_seats === 999999 ? 'Unlimited' : plan.default_max_seats}</TableCell>
                        <TableCell>{plan.default_max_nodes === 999999 ? 'Unlimited' : plan.default_max_nodes}</TableCell>
                        <TableCell>{formatPrice(plan.default_monthly_price)}</TableCell>
                        <TableCell>
                          <span className="text-sm text-neutral-600">
                            {Object.values(plan.features || {}).filter(Boolean).length} enabled
                          </span>
                        </TableCell>
                        <TableCell>
                          {plan.is_system_plan ? (
                            <Badge variant="secondary">System</Badge>
                          ) : (
                            <Badge variant="primary">Custom</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {plan.is_active ? (
                            <Badge variant="success">Active</Badge>
                          ) : (
                            <Badge variant="secondary">Inactive</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <button
                            onClick={() => openEditModal(plan)}
                            className="p-2 hover:bg-neutral-100 rounded-lg transition"
                            title="Edit Plan"
                          >
                            <PencilIcon className="h-4 w-4 text-primary-600" />
                          </button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* Create Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">Create License Plan</h2>
                  <button
                    onClick={() => setShowCreateModal(false)}
                    className="p-2 hover:bg-neutral-100 rounded-lg"
                  >
                    <XCircleIcon className="h-5 w-5" />
                  </button>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreate} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Plan Key * (unique identifier)
                      </label>
                      <Input
                        value={formData.plan_key}
                        onChange={(e) => setFormData({ ...formData, plan_key: e.target.value.toLowerCase().replace(/\s+/g, '_') })}
                        placeholder="e.g., my_custom_plan"
                        required
                      />
                      <p className="text-xs text-neutral-500 mt-1">Lowercase, underscores only</p>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Plan Name *
                      </label>
                      <Input
                        value={formData.plan_name}
                        onChange={(e) => setFormData({ ...formData, plan_name: e.target.value })}
                        placeholder="e.g., My Custom Plan"
                        required
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Description
                    </label>
                    <Textarea
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      rows={2}
                      placeholder="Plan description"
                    />
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Default Max Seats *
                      </label>
                      <Input
                        type="number"
                        min="0"
                        value={formData.default_max_seats}
                        onChange={(e) => setFormData({ ...formData, default_max_seats: parseInt(e.target.value) || 0 })}
                        required
                      />
                      <p className="text-xs text-neutral-500 mt-1">Use 999999 for unlimited</p>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Default Max Nodes *
                      </label>
                      <Input
                        type="number"
                        min="0"
                        value={formData.default_max_nodes}
                        onChange={(e) => setFormData({ ...formData, default_max_nodes: parseInt(e.target.value) || 0 })}
                        required
                      />
                      <p className="text-xs text-neutral-500 mt-1">Use 999999 for unlimited</p>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Default Monthly Price
                      </label>
                      <Input
                        value={formData.default_monthly_price}
                        onChange={(e) => setFormData({ ...formData, default_monthly_price: e.target.value })}
                        placeholder="e.g., 99 or custom"
                      />
                      <p className="text-xs text-neutral-500 mt-1">Enter number or "custom"</p>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Display Order
                    </label>
                    <Input
                      type="number"
                      min="0"
                      value={formData.display_order}
                      onChange={(e) => setFormData({ ...formData, display_order: parseInt(e.target.value) || 0 })}
                    />
                  </div>
                  
                  <div className="border-t pt-4">
                    <label className="block text-sm font-medium text-neutral-700 mb-3">
                      Features *
                    </label>
                    <div className="grid grid-cols-2 gap-3 max-h-96 overflow-y-auto p-4 bg-neutral-50 rounded-lg">
                      {Object.entries(features).map(([featureName, description]) => (
                        <div key={featureName} className="flex items-start space-x-2">
                          <Checkbox
                            checked={formData.features[featureName] || false}
                            onChange={() => toggleFeature(featureName)}
                          />
                          <div className="flex-1">
                            <label className="text-sm font-medium text-neutral-700 cursor-pointer" onClick={() => toggleFeature(featureName)}>
                              {featureName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            </label>
                            <p className="text-xs text-neutral-500">{description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  <div className="flex justify-end space-x-4 pt-4 border-t">
                    <Button
                      variant="outline"
                      onClick={() => setShowCreateModal(false)}
                    >
                      Cancel
                    </Button>
                    <Button type="submit" variant="primary">
                      Create Plan
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Edit Modal */}
        {showEditModal && selectedPlan && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">Edit License Plan</h2>
                  <button
                    onClick={() => {
                      setShowEditModal(false);
                      setSelectedPlan(null);
                    }}
                    className="p-2 hover:bg-neutral-100 rounded-lg"
                  >
                    <XCircleIcon className="h-5 w-5" />
                  </button>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleEdit} className="space-y-4">
                  <div className="p-4 bg-neutral-50 rounded-lg">
                    <p className="text-sm text-neutral-600 mb-1">
                      <span className="font-medium">Plan Key:</span> <code className="text-xs bg-white px-2 py-1 rounded">{selectedPlan.plan_key}</code>
                    </p>
                    {selectedPlan.is_system_plan && (
                      <p className="text-xs text-warning-600 mt-2">
                        ⚠️ System plans cannot have their features modified. Create a custom plan to modify features.
                      </p>
                    )}
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Plan Name *
                      </label>
                      <Input
                        value={formData.plan_name}
                        onChange={(e) => setFormData({ ...formData, plan_name: e.target.value })}
                        required
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Default Monthly Price
                      </label>
                      <Input
                        value={formData.default_monthly_price}
                        onChange={(e) => setFormData({ ...formData, default_monthly_price: e.target.value })}
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Description
                    </label>
                    <Textarea
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      rows={2}
                    />
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Default Max Seats *
                      </label>
                      <Input
                        type="number"
                        min="0"
                        value={formData.default_max_seats}
                        onChange={(e) => setFormData({ ...formData, default_max_seats: parseInt(e.target.value) || 0 })}
                        required
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Default Max Nodes *
                      </label>
                      <Input
                        type="number"
                        min="0"
                        value={formData.default_max_nodes}
                        onChange={(e) => setFormData({ ...formData, default_max_nodes: parseInt(e.target.value) || 0 })}
                        required
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Display Order
                      </label>
                      <Input
                        type="number"
                        min="0"
                        value={formData.display_order}
                        onChange={(e) => setFormData({ ...formData, display_order: parseInt(e.target.value) || 0 })}
                      />
                    </div>
                  </div>
                  
                  {!selectedPlan.is_system_plan && (
                    <div className="border-t pt-4">
                      <label className="block text-sm font-medium text-neutral-700 mb-3">
                        Features
                      </label>
                      <div className="grid grid-cols-2 gap-3 max-h-96 overflow-y-auto p-4 bg-neutral-50 rounded-lg">
                        {Object.entries(features).map(([featureName, description]) => (
                          <div key={featureName} className="flex items-start space-x-2">
                            <Checkbox
                              checked={formData.features[featureName] || false}
                              onChange={() => toggleFeature(featureName)}
                            />
                            <div className="flex-1">
                              <label className="text-sm font-medium text-neutral-700 cursor-pointer" onClick={() => toggleFeature(featureName)}>
                                {featureName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                              </label>
                              <p className="text-xs text-neutral-500">{description}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <div className="flex justify-end space-x-4 pt-4 border-t">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setShowEditModal(false);
                        setSelectedPlan(null);
                      }}
                    >
                      Cancel
                    </Button>
                    <Button type="submit" variant="primary">
                      Update Plan
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        )}
      </main>
    </div>
  );
}



