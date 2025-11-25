'use client';

import { useState, useEffect } from 'react';
import {
  ServerIcon,
  PencilIcon,
  CheckIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

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
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Loading infrastructure thresholds...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
      <div className="flex items-center mb-6">
        <ServerIcon className="h-6 w-6 text-indigo-600 mr-2" />
        <h3 className="text-lg font-semibold text-gray-900">Infrastructure Thresholds</h3>
      </div>
      <p className="text-sm text-gray-600 mb-6">
        Configure thresholds for infrastructure metrics (CPU, Memory, Disk, Network) used by
        precheck analysis to determine if reported issues are false positives. If a metric is below
        the warning threshold, the ticket will be closed as a false positive.
      </p>

      <div className="space-y-6">
        {Object.entries(groupedByMetric).map(([metric, metricThresholds]) => (
          <div key={metric} className="border border-gray-200 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-gray-900 mb-4">
              {getMetricLabel(metric)}
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {metricThresholds.map((threshold) => {
                const key = `${threshold.metric}_${threshold.environment}`;
                const isEditing = editingKey === key;

                return (
                  <div
                    key={key}
                    className="border border-gray-200 rounded-lg p-3 bg-gray-50"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-gray-700">
                        {getEnvironmentLabel(threshold.environment)}
                      </span>
                    </div>
                    {isEditing ? (
                      <div className="space-y-2">
                        <div>
                          <label className="text-xs text-gray-600">Warning (%)</label>
                          <input
                            type="number"
                            min="0"
                            max="100"
                            step="0.1"
                            value={editWarning}
                            onChange={(e) => setEditWarning(parseFloat(e.target.value) || 0)}
                            className="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            disabled={saving}
                          />
                        </div>
                        <div>
                          <label className="text-xs text-gray-600">Critical (%)</label>
                          <input
                            type="number"
                            min="0"
                            max="100"
                            step="0.1"
                            value={editCritical}
                            onChange={(e) => setEditCritical(parseFloat(e.target.value) || 0)}
                            className="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            disabled={saving}
                          />
                        </div>
                        <div className="flex items-center space-x-1">
                          <button
                            onClick={() =>
                              handleSave(threshold.metric, threshold.environment)
                            }
                            disabled={saving}
                            className="flex-1 p-1.5 text-green-600 hover:bg-green-50 rounded transition-colors disabled:opacity-50 text-xs"
                            title="Save"
                          >
                            <CheckIcon className="h-4 w-4 mx-auto" />
                          </button>
                          <button
                            onClick={handleCancel}
                            disabled={saving}
                            className="flex-1 p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50 text-xs"
                            title="Cancel"
                          >
                            <XMarkIcon className="h-4 w-4 mx-auto" />
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-600">Warning:</span>
                          <span className="text-sm font-semibold text-yellow-600">
                            {threshold.warning_threshold}%
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-600">Critical:</span>
                          <span className="text-sm font-semibold text-red-600">
                            {threshold.critical_threshold}%
                          </span>
                        </div>
                        <button
                          onClick={() => handleEdit(threshold)}
                          className="mt-2 w-full p-1 text-gray-600 hover:bg-gray-100 rounded transition-colors text-xs"
                          title="Edit"
                        >
                          <PencilIcon className="h-3 w-3 mx-auto" />
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {thresholds.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No infrastructure thresholds found. Default values will be used.</p>
        </div>
      )}
    </div>
  );
}



