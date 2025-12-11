'use client';

import { useState, useEffect } from 'react';
import {
  ServerIcon,
  PencilIcon,
  CheckIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface InfrastructureThreshold {
  metric: string;
  environment: string;
  warning_threshold: number;
  critical_threshold: number;
}

interface InfrastructureThresholdSectionProps {
  onSuccess?: (message: string) => void;
  onError?: (message: string) => void;
}

export function InfrastructureThresholdSection({
  onSuccess,
  onError,
}: InfrastructureThresholdSectionProps) {
  const [thresholds, setThresholds] = useState<InfrastructureThreshold[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editWarning, setEditWarning] = useState<number>(0);
  const [editCritical, setEditCritical] = useState<number>(0);

  useEffect(() => {
    fetchThresholds();
  }, []);

  const fetchThresholds = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/settings/infrastructure-thresholds/demo');
      if (!response.ok) {
        throw new Error('Failed to fetch infrastructure thresholds');
      }
      const data = await response.json();
      setThresholds(data.thresholds || []);
    } catch (error) {
      console.error('Error fetching infrastructure thresholds:', error);
      onError?.('Failed to load infrastructure thresholds');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (threshold: InfrastructureThreshold) => {
    const key = `${threshold.metric}_${threshold.environment}`;
    setEditingKey(key);
    setEditWarning(threshold.warning_threshold);
    setEditCritical(threshold.critical_threshold);
  };

  const handleCancel = () => {
    setEditingKey(null);
    setEditWarning(0);
    setEditCritical(0);
  };

  const handleSave = async (metric: string, environment: string) => {
    try {
      // Validate values
      if (editWarning < 0 || editWarning > 100) {
        onError?.('Warning threshold must be between 0 and 100');
        return;
      }
      if (editCritical < 0 || editCritical > 100) {
        onError?.('Critical threshold must be between 0 and 100');
        return;
      }
      if (editWarning >= editCritical) {
        onError?.('Warning threshold must be less than critical threshold');
        return;
      }

      setSaving(true);
      const response = await fetch('/api/v1/settings/infrastructure-thresholds/demo', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          metric,
          environment,
          warning_threshold: editWarning,
          critical_threshold: editCritical,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update infrastructure threshold');
      }

      await fetchThresholds();
      setEditingKey(null);
      setEditWarning(0);
      setEditCritical(0);
      onSuccess?.('Infrastructure threshold updated successfully');
    } catch (error: any) {
      console.error('Error updating infrastructure threshold:', error);
      onError?.(error.message || 'Failed to update infrastructure threshold');
    } finally {
      setSaving(false);
    }
  };

  const getMetricLabel = (metric: string): string => {
    const labels: Record<string, string> = {
      cpu: 'CPU Utilization',
      memory: 'Memory Utilization',
      disk: 'Disk Utilization',
      network: 'Network Utilization',
    };
    return labels[metric] || metric.toUpperCase();
  };

  const getEnvironmentLabel = (env: string): string => {
    const labels: Record<string, string> = {
      prod: 'Production',
      staging: 'Staging',
      dev: 'Development',
    };
    return labels[env] || env;
  };

  // Group thresholds by metric
  const groupedByMetric: Record<string, InfrastructureThreshold[]> = {};
  thresholds.forEach((threshold) => {
    if (!groupedByMetric[threshold.metric]) {
      groupedByMetric[threshold.metric] = [];
    }
    groupedByMetric[threshold.metric].push(threshold);
  });

  if (loading) {
    return (
      <Card variant="elevated">
        <CardContent padding="lg">
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            <span className="ml-3 text-neutral-600 font-medium">Loading infrastructure thresholds...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card variant="elevated">
      <CardHeader>
        <div className="flex items-center mb-2">
          <div className="p-1.5 rounded-lg bg-primary-100 mr-3">
            <ServerIcon className="h-6 w-6 text-primary-600" />
          </div>
          <h3 className="text-xl font-semibold text-neutral-900">Infrastructure Thresholds</h3>
        </div>
        <p className="text-sm text-neutral-600">
          Configure thresholds for infrastructure metrics (CPU, Memory, Disk, Network) used by
          precheck analysis to determine if reported issues are false positives. If a metric is below
          the warning threshold, the ticket will be closed as a false positive.
        </p>
      </CardHeader>
      <CardContent padding="md">
        {thresholds.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-neutral-500">No infrastructure thresholds found. Default values will be used.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(groupedByMetric).map(([metric, metricThresholds]) => (
              <Card key={metric} variant="default">
                <CardContent padding="md">
                  <h4 className="text-sm font-semibold text-neutral-900 mb-4">
                    {getMetricLabel(metric)}
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {metricThresholds.map((threshold) => {
                      const key = `${threshold.metric}_${threshold.environment}`;
                      const isEditing = editingKey === key;

                      return (
                        <Card
                          key={key}
                          variant="outlined"
                          className="bg-neutral-50"
                        >
                          <CardContent padding="sm">
                            <div className="flex items-center justify-between mb-3">
                              <span className="text-xs font-semibold text-neutral-700">
                                {getEnvironmentLabel(threshold.environment)}
                              </span>
                            </div>
                            {isEditing ? (
                              <div className="space-y-3">
                                <div>
                                  <label className="text-xs font-semibold text-neutral-600 mb-1 block">Warning (%)</label>
                                  <input
                                    type="number"
                                    min="0"
                                    max="100"
                                    step="0.1"
                                    value={editWarning}
                                    onChange={(e) => setEditWarning(parseFloat(e.target.value) || 0)}
                                    className="w-full px-2 py-1.5 border-2 border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                                    disabled={saving}
                                  />
                                </div>
                                <div>
                                  <label className="text-xs font-semibold text-neutral-600 mb-1 block">Critical (%)</label>
                                  <input
                                    type="number"
                                    min="0"
                                    max="100"
                                    step="0.1"
                                    value={editCritical}
                                    onChange={(e) => setEditCritical(parseFloat(e.target.value) || 0)}
                                    className="w-full px-2 py-1.5 border-2 border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                                    disabled={saving}
                                  />
                                </div>
                                <div className="flex items-center gap-2 pt-1">
                                  <Button
                                    variant="success"
                                    size="sm"
                                    onClick={() =>
                                      handleSave(threshold.metric, threshold.environment)
                                    }
                                    disabled={saving}
                                    leftIcon={<CheckIcon className="h-4 w-4" />}
                                    className="flex-1"
                                    title="Save"
                                  >
                                    Save
                                  </Button>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={handleCancel}
                                    disabled={saving}
                                    leftIcon={<XMarkIcon className="h-4 w-4" />}
                                    className="flex-1"
                                    title="Cancel"
                                  >
                                    Cancel
                                  </Button>
                                </div>
                              </div>
                            ) : (
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <span className="text-xs text-neutral-600">Warning:</span>
                                  <span className="text-sm font-semibold text-warning-600">
                                    {threshold.warning_threshold}%
                                  </span>
                                </div>
                                <div className="flex items-center justify-between">
                                  <span className="text-xs text-neutral-600">Critical:</span>
                                  <span className="text-sm font-semibold text-error-600">
                                    {threshold.critical_threshold}%
                                  </span>
                                </div>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleEdit(threshold)}
                                  leftIcon={<PencilIcon className="h-3 w-3" />}
                                  className="mt-2 w-full"
                                  title="Edit"
                                >
                                  Edit
                                </Button>
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      );
                    })}
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









