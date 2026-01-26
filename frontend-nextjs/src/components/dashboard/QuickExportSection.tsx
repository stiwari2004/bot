'use client';

interface QuickExportSectionProps {
  onExport: (type: 'overview' | 'tenants' | 'revenue', format: 'csv' | 'pdf') => Promise<void>;
}

export function QuickExportSection({ onExport }: QuickExportSectionProps) {
  return (
    <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-neutral-900 mb-4">Quick Export</h2>
      <p className="text-sm text-neutral-600 mb-6">
        Generate standard reports instantly with default settings.
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="border border-neutral-200 rounded-lg p-4 hover:border-primary-300 transition">
          <h3 className="font-medium text-neutral-900 mb-2">Platform Overview</h3>
          <p className="text-sm text-neutral-600 mb-4">Complete platform statistics and metrics</p>
          <div className="flex gap-2">
            <button
              onClick={() => onExport('overview', 'pdf')}
              className="flex-1 px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
            >
              PDF
            </button>
            <button
              onClick={() => onExport('overview', 'csv')}
              className="flex-1 px-3 py-2 text-sm bg-neutral-100 text-neutral-700 rounded-lg hover:bg-neutral-200 transition"
            >
              CSV
            </button>
          </div>
        </div>
        
        <div className="border border-neutral-200 rounded-lg p-4 hover:border-primary-300 transition">
          <h3 className="font-medium text-neutral-900 mb-2">Tenant Report</h3>
          <p className="text-sm text-neutral-600 mb-4">All tenants with usage and billing data</p>
          <div className="flex gap-2">
            <button
              onClick={() => onExport('tenants', 'pdf')}
              className="flex-1 px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
            >
              PDF
            </button>
            <button
              onClick={() => onExport('tenants', 'csv')}
              className="flex-1 px-3 py-2 text-sm bg-neutral-100 text-neutral-700 rounded-lg hover:bg-neutral-200 transition"
            >
              CSV
            </button>
          </div>
        </div>
        
        <div className="border border-neutral-200 rounded-lg p-4 hover:border-primary-300 transition">
          <h3 className="font-medium text-neutral-900 mb-2">Revenue Report</h3>
          <p className="text-sm text-neutral-600 mb-4">Revenue analytics and trends</p>
          <div className="flex gap-2">
            <button
              onClick={() => onExport('revenue', 'pdf')}
              className="flex-1 px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
            >
              PDF
            </button>
            <button
              onClick={() => onExport('revenue', 'csv')}
              className="flex-1 px-3 py-2 text-sm bg-neutral-100 text-neutral-700 rounded-lg hover:bg-neutral-200 transition"
            >
              CSV
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
