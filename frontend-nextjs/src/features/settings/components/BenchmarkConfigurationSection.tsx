'use client';

import { useState, useEffect } from 'react';
import {
  ChartBarIcon,
  PencilIcon,
  CheckIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

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
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Loading benchmark configuration...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
      <div className="flex items-center mb-6">
        <ChartBarIcon className="h-6 w-6 text-indigo-600 mr-2" />
        <h3 className="text-lg font-semibold text-gray-900">Benchmark Configuration</h3>
      </div>
      <p className="text-sm text-gray-600 mb-6">
        Configure thresholds and benchmarks that control system behavior. These values determine
        when runbooks are suggested, flagged as duplicates, or considered high-quality.
      </p>

      <div className="space-y-4">
        {configs.map((config) => (
          <div
            key={config.config_key}
            className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center mb-2">
                  <h4 className="text-sm font-semibold text-gray-900">
                    {getConfigLabel(config.config_key)}
                  </h4>
                </div>
                <p className="text-xs text-gray-600 mb-3">{config.description}</p>
                {editingKey === config.config_key ? (
                  <div className="flex items-center space-x-2">
                    <input
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-24"
                      disabled={saving}
                    />
                    <span className="text-xs text-gray-500">(0.0 - 1.0)</span>
                    <button
                      onClick={() => handleSave(config.config_key)}
                      disabled={saving}
                      className="p-1.5 text-green-600 hover:bg-green-50 rounded transition-colors disabled:opacity-50"
                      title="Save"
                    >
                      <CheckIcon className="h-5 w-5" />
                    </button>
                    <button
                      onClick={handleCancel}
                      disabled={saving}
                      className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                      title="Cancel"
                    >
                      <XMarkIcon className="h-5 w-5" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center space-x-3">
                    <span className="text-lg font-mono font-semibold text-blue-600">
                      {config.config_value}
                    </span>
                    <button
                      onClick={() => handleEdit(config)}
                      className="p-1.5 text-gray-600 hover:bg-gray-100 rounded transition-colors"
                      title="Edit"
                    >
                      <PencilIcon className="h-4 w-4" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {configs.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No benchmark configuration found. Default values will be used.</p>
        </div>
      )}
    </div>
  );
}



