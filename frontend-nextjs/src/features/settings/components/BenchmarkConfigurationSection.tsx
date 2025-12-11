'use client';

import { useState, useEffect } from 'react';
import {
  ChartBarIcon,
  PencilIcon,
  CheckIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface BenchmarkConfig {
  config_key: string;
  config_value: string;
  description: string;
}

interface BenchmarkConfigurationSectionProps {
  onSuccess?: (message: string) => void;
  onError?: (message: string) => void;
}

export function BenchmarkConfigurationSection({
  onSuccess,
  onError,
}: BenchmarkConfigurationSectionProps) {
  const [configs, setConfigs] = useState<BenchmarkConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>('');

  useEffect(() => {
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/settings/benchmark-config/demo');
      if (!response.ok) {
        throw new Error('Failed to fetch benchmark configuration');
      }
      const data = await response.json();
      setConfigs(data.configs || []);
    } catch (error) {
      console.error('Error fetching benchmark config:', error);
      onError?.('Failed to load benchmark configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (config: BenchmarkConfig) => {
    setEditingKey(config.config_key);
    setEditValue(config.config_value);
  };

  const handleCancel = () => {
    setEditingKey(null);
    setEditValue('');
  };

  const handleSave = async (configKey: string) => {
    try {
      // Validate value
      const value = parseFloat(editValue);
      if (isNaN(value) || value < 0 || value > 1) {
        onError?.('Value must be a number between 0.0 and 1.0');
        return;
      }

      setSaving(true);
      const response = await fetch('/api/v1/settings/benchmark-config/demo', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          config_key: configKey,
          config_value: editValue,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update benchmark configuration');
      }

      await fetchConfigs();
      setEditingKey(null);
      setEditValue('');
      onSuccess?.('Benchmark configuration updated successfully');
    } catch (error: any) {
      console.error('Error updating benchmark config:', error);
      onError?.(error.message || 'Failed to update benchmark configuration');
    } finally {
      setSaving(false);
    }
  };

  const getConfigLabel = (key: string): string => {
    const labels: Record<string, string> = {
      confidence_threshold_existing: 'Confidence Threshold (Existing Runbooks)',
      confidence_threshold_duplicate: 'Confidence Threshold (Duplicate Detection)',
      min_runbook_success_rate: 'Minimum Success Rate',
    };
    return labels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  };

  if (loading) {
    return (
      <Card variant="elevated">
        <CardContent padding="lg">
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            <span className="ml-3 text-neutral-600 font-medium">Loading benchmark configuration...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card variant="elevated">
      <CardHeader>
        <div className="flex items-center mb-2">
          <div className="p-1.5 rounded-lg bg-secondary-100 mr-3">
            <ChartBarIcon className="h-6 w-6 text-secondary-600" />
          </div>
          <h3 className="text-xl font-semibold text-neutral-900">Benchmark Configuration</h3>
        </div>
        <p className="text-sm text-neutral-600">
          Configure thresholds and benchmarks that control system behavior. These values determine
          when runbooks are suggested, flagged as duplicates, or considered high-quality.
        </p>
      </CardHeader>
      <CardContent padding="md">
        {configs.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-neutral-500">No benchmark configuration found. Default values will be used.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {configs.map((config) => (
              <Card
                key={config.config_key}
                variant="default"
                className="hover:border-primary-300 transition-colors"
              >
                <CardContent padding="md">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center mb-2">
                        <h4 className="text-sm font-semibold text-neutral-900">
                          {getConfigLabel(config.config_key)}
                        </h4>
                      </div>
                      <p className="text-xs text-neutral-600 mb-3">{config.description}</p>
                      {editingKey === config.config_key ? (
                        <div className="flex items-center gap-3">
                          <input
                            type="number"
                            min="0"
                            max="1"
                            step="0.01"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            className="px-3 py-2 border-2 border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 w-24 text-neutral-900 transition-all"
                            disabled={saving}
                          />
                          <span className="text-xs text-neutral-500">(0.0 - 1.0)</span>
                          <Button
                            variant="success"
                            size="sm"
                            onClick={() => handleSave(config.config_key)}
                            disabled={saving}
                            leftIcon={<CheckIcon className="h-4 w-4" />}
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
                            title="Cancel"
                          >
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-3">
                          <span className="text-lg font-mono font-semibold text-primary-600">
                            {config.config_value}
                          </span>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEdit(config)}
                            leftIcon={<PencilIcon className="h-4 w-4" />}
                            title="Edit"
                          >
                            Edit
                          </Button>
                        </div>
                      )}
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









