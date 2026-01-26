'use client';

import { Cog6ToothIcon } from '@heroicons/react/24/outline';

interface DashboardPreferences {
  auto_refresh?: boolean;
  refresh_interval?: number;
  widgets?: Record<string, { enabled: boolean; order: number }>;
}

interface PreferencesPanelProps {
  preferences: DashboardPreferences | null;
  onSave: (updates: Partial<DashboardPreferences>) => void;
  onClose: () => void;
}

export function PreferencesPanel({ preferences, onSave, onClose }: PreferencesPanelProps) {
  return (
    <div className="mb-6 bg-white border border-neutral-200 rounded-lg p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-neutral-900">Dashboard Settings</h3>
        <button
          onClick={onClose}
          className="text-neutral-500 hover:text-neutral-700 text-xl leading-none"
          aria-label="Close settings"
        >
          ×
        </button>
      </div>
      <div className="space-y-4">
        <div className="flex items-center justify-between py-2">
          <div className="flex-1">
            <label className="text-sm font-medium text-neutral-700">Auto Refresh</label>
            <p className="text-xs text-neutral-500 mt-1">Enable real-time updates via WebSocket</p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={preferences?.auto_refresh ?? true}
              onChange={(e) => onSave({ auto_refresh: e.target.checked })}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-neutral-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-neutral-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
          </label>
        </div>
        <div className="flex items-center justify-between py-2">
          <div className="flex-1">
            <label className="text-sm font-medium text-neutral-700">Refresh Interval</label>
            <p className="text-xs text-neutral-500 mt-1">Time between updates (milliseconds)</p>
          </div>
          <input
            type="number"
            value={preferences?.refresh_interval ?? 30000}
            onChange={(e) => onSave({ refresh_interval: parseInt(e.target.value) || 30000 })}
            className="w-32 px-3 py-1.5 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            min="5000"
            step="5000"
          />
        </div>
        {preferences?.widgets && (
          <div className="pt-4 border-t border-neutral-200">
            <p className="text-sm font-medium text-neutral-700 mb-3">Widget Visibility</p>
            <div className="space-y-2">
              {Object.entries(preferences.widgets).map(([key, widget]: [string, any]) => (
                <div key={key} className="flex items-center justify-between py-1">
                  <label className="text-sm text-neutral-600 capitalize">{key.replace(/_/g, ' ')}</label>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={widget.enabled}
                      onChange={(e) => {
                        const newWidgets = { ...preferences.widgets };
                        newWidgets[key] = { ...widget, enabled: e.target.checked };
                        onSave({ widgets: newWidgets });
                      }}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-neutral-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-neutral-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-600"></div>
                  </label>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
