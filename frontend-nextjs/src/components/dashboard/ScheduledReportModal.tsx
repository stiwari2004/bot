'use client';

import { useState, useEffect } from 'react';
import { ScheduledReport } from '@/hooks/useScheduledReports';
import { apiConfig } from '@/lib/api-config';

interface ScheduledReportModalProps {
  report: ScheduledReport | null;
  token: string | null;
  onClose: () => void;
  onSave: () => void;
}

export function ScheduledReportModal({ report, token, onClose, onSave }: ScheduledReportModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    report_type: 'overview',
    format: 'pdf',
    frequency: 'weekly',
    time: '09:00',
    recipients: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (report) {
      setFormData({
        name: report.name,
        description: report.description || '',
        report_type: report.report_type,
        format: report.format,
        frequency: report.frequency,
        time: report.schedule_config?.time || '09:00',
        recipients: report.recipients.join('\n'),
      });
    }
  }, [report]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setError('Not authenticated');
      return;
    }

    if (!formData.name.trim() || !formData.recipients.trim()) {
      setError('Please provide a name and at least one recipient email');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const recipients = formData.recipients.split('\n').filter(email => email.trim());
      
      const url = report
        ? apiConfig.endpoints.superAdmin.reporting.updateScheduled(report.id)
        : apiConfig.endpoints.superAdmin.reporting.createScheduled();
      
      const method = report ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: formData.name,
          description: formData.description || undefined,
          report_type: formData.report_type,
          format: formData.format,
          frequency: formData.frequency,
          schedule_config: { time: formData.time, timezone: 'UTC' },
          recipients,
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to ${report ? 'update' : 'create'} scheduled report`);
      }
      
      onSave();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save scheduled report');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-neutral-900">
              {report ? 'Edit Scheduled Report' : 'Create Scheduled Report'}
            </h3>
            <button
              onClick={onClose}
              className="text-neutral-500 hover:text-neutral-700 text-xl leading-none"
            >
              ×
            </button>
          </div>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">Report Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="e.g., Weekly Revenue Report"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                rows={2}
                placeholder="Optional description"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">Report Type</label>
                <select
                  value={formData.report_type}
                  onChange={(e) => setFormData({ ...formData, report_type: e.target.value })}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="overview">Overview</option>
                  <option value="tenants">Tenants</option>
                  <option value="revenue">Revenue</option>
                  <option value="usage">Usage</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">Format</label>
                <select
                  value={formData.format}
                  onChange={(e) => setFormData({ ...formData, format: e.target.value })}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="pdf">PDF</option>
                  <option value="csv">CSV</option>
                </select>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">Frequency</label>
                <select
                  value={formData.frequency}
                  onChange={(e) => setFormData({ ...formData, frequency: e.target.value })}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">Time</label>
                <input
                  type="time"
                  value={formData.time}
                  onChange={(e) => setFormData({ ...formData, time: e.target.value })}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  required
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">Recipients (Email addresses, one per line)</label>
              <textarea
                value={formData.recipients}
                onChange={(e) => setFormData({ ...formData, recipients: e.target.value })}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                rows={3}
                placeholder="admin@example.com&#10;manager@example.com"
                required
              />
            </div>
            
            <div className="flex justify-end gap-2 pt-4 border-t">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-neutral-300 rounded-lg hover:bg-neutral-50 transition"
                disabled={saving}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition disabled:opacity-50"
                disabled={saving}
              >
                {saving ? 'Saving...' : report ? 'Update' : 'Create'} Schedule
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
