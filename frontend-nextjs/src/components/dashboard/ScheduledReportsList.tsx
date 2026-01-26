'use client';

import { useState } from 'react';
import { 
  CalendarIcon, 
  ClockIcon, 
  PlusIcon, 
  PencilIcon, 
  TrashIcon, 
  PlayIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { useScheduledReports, ScheduledReport } from '@/hooks/useScheduledReports';
import { ScheduledReportModal } from './ScheduledReportModal';

interface ScheduledReportsListProps {
  token: string | null;
}

export function ScheduledReportsList({ token }: ScheduledReportsListProps) {
  const { reports, loading, error, fetchReports, deleteReport, executeReport } = useScheduledReports({ token });
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingReport, setEditingReport] = useState<ScheduledReport | null>(null);

  const handleDelete = async (reportId: number) => {
    if (confirm('Are you sure you want to delete this scheduled report?')) {
      try {
        await deleteReport(reportId);
      } catch (err) {
        alert(`Failed to delete report: ${err instanceof Error ? err.message : 'Unknown error'}`);
      }
    }
  };

  const handleExecute = async (reportId: number) => {
    try {
      await executeReport(reportId);
      alert('Report executed successfully');
    } catch (err) {
      alert(`Failed to execute report: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-neutral-900">Scheduled Reports</h2>
          <p className="text-sm text-neutral-600 mt-1">
            Automated reports sent via email on a schedule.
          </p>
        </div>
        <button
          onClick={() => {
            setEditingReport(null);
            setShowCreateModal(true);
          }}
          className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
        >
          <PlusIcon className="h-5 w-5" />
          <span>Create Schedule</span>
        </button>
      </div>
      
      {loading && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-2 text-sm text-neutral-600">Loading scheduled reports...</p>
        </div>
      )}
      
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}
      
      {!loading && reports.length === 0 && (
        <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-8 text-center">
          <CalendarIcon className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
          <p className="text-sm text-neutral-600 mb-2">No scheduled reports yet</p>
          <p className="text-xs text-neutral-500">Create your first scheduled report to automate report generation and delivery.</p>
        </div>
      )}
      
      {!loading && reports.length > 0 && (
        <div className="space-y-3">
          {reports.map((report) => (
            <div key={report.id} className="border border-neutral-200 rounded-lg p-4 hover:border-primary-300 transition">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <h3 className="font-medium text-neutral-900">{report.name}</h3>
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      report.is_active 
                        ? 'bg-success-100 text-success-700' 
                        : 'bg-neutral-100 text-neutral-600'
                    }`}>
                      {report.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  {report.description && (
                    <p className="text-sm text-neutral-600 mb-2">{report.description}</p>
                  )}
                  <div className="flex flex-wrap gap-4 text-xs text-neutral-500">
                    <span className="flex items-center space-x-1">
                      <DocumentTextIcon className="h-4 w-4" />
                      <span>{report.report_type}</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <ClockIcon className="h-4 w-4" />
                      <span>{report.frequency}</span>
                    </span>
                    {report.next_run_at && (
                      <span className="flex items-center space-x-1">
                        <CalendarIcon className="h-4 w-4" />
                        <span>Next: {new Date(report.next_run_at).toLocaleDateString()}</span>
                      </span>
                    )}
                    <span>{report.recipients.length} recipient{report.recipients.length !== 1 ? 's' : ''}</span>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleExecute(report.id)}
                    className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg transition"
                    title="Execute Now"
                  >
                    <PlayIcon className="h-5 w-5" />
                  </button>
                  <button
                    onClick={() => {
                      setEditingReport(report);
                      setShowCreateModal(true);
                    }}
                    className="p-2 text-neutral-600 hover:bg-neutral-50 rounded-lg transition"
                    title="Edit"
                  >
                    <PencilIcon className="h-5 w-5" />
                  </button>
                  <button
                    onClick={() => handleDelete(report.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                    title="Delete"
                  >
                    <TrashIcon className="h-5 w-5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showCreateModal && (
        <ScheduledReportModal
          report={editingReport}
          token={token}
          onClose={() => {
            setShowCreateModal(false);
            setEditingReport(null);
          }}
          onSave={async () => {
            setShowCreateModal(false);
            setEditingReport(null);
            await fetchReports();
          }}
        />
      )}
    </div>
  );
}
