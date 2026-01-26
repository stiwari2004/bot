'use client';

import { QuickExportSection } from './QuickExportSection';
import { CustomReportBuilder } from './CustomReportBuilder';
import { ScheduledReportsList } from './ScheduledReportsList';

interface DashboardReportsProps {
  token: string | null;
  onExport: (type: 'overview' | 'tenants' | 'revenue', format: 'csv' | 'pdf') => Promise<void>;
}

export function DashboardReports({ token, onExport }: DashboardReportsProps) {
  return (
    <div className="space-y-6">
      <QuickExportSection onExport={onExport} />
      <CustomReportBuilder token={token} onExport={onExport} />
      <ScheduledReportsList token={token} />
    </div>
  );
}
