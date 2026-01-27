'use client';

import { QuarantineDashboard } from '@/components/quarantine/QuarantineDashboard';

export default function QuarantinePage() {
  return (
    <div className="container mx-auto py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-900">Runbook Quarantine Dashboard</h1>
        <p className="text-sm text-neutral-600 mt-1">
          Review quarantined runbooks, analyze failure patterns, and manage releases
        </p>
      </div>
      <QuarantineDashboard />
    </div>
  );
}
