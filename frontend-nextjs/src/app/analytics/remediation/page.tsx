'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';
import { ChartBarIcon, ClockIcon, CheckCircleIcon } from '@heroicons/react/24/outline';

export default function RemediationAnalyticsPage() {
  const { token } = useAuth();
  const [effectiveness, setEffectiveness] = useState<any>(null);
  const [trends, setTrends] = useState<any>(null);
  const [failingSteps, setFailingSteps] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [effRes, trendsRes, stepsRes] = await Promise.all([
        fetch(apiConfig.endpoints.remediation.effectiveness(), {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        }),
        fetch(apiConfig.endpoints.remediation.trends('monthly', 12), {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        }),
        fetch(apiConfig.endpoints.remediation.failingSteps(undefined, undefined, 10), {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        }),
      ]);

      if (effRes.ok) setEffectiveness(await effRes.json());
      if (trendsRes.ok) setTrends(await trendsRes.json());
      if (stepsRes.ok) setFailingSteps(await stepsRes.json());
    } catch (err) {
      console.error('Error fetching remediation analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
          <span>Loading analytics...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-900">Remediation Effectiveness Analytics</h1>
        <p className="text-sm text-neutral-600 mt-1">
          Track MTTR, automation coverage, ROI, and identify improvement areas
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <Card variant="elevated">
          <CardContent padding="md">
            <div className="flex items-center gap-2 mb-2">
              <ClockIcon className="h-5 w-5 text-primary-600" />
              <h3 className="font-semibold text-neutral-900">MTTR</h3>
            </div>
            <p className="text-2xl font-bold text-neutral-900">
              {effectiveness?.mttr_minutes 
                ? `${effectiveness.mttr_minutes.toFixed(1)} min`
                : 'N/A'}
            </p>
            <p className="text-xs text-neutral-500 mt-1">Mean Time To Resolution</p>
          </CardContent>
        </Card>

        <Card variant="elevated">
          <CardContent padding="md">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircleIcon className="h-5 w-5 text-success-600" />
              <h3 className="font-semibold text-neutral-900">Automation Coverage</h3>
            </div>
            <p className="text-2xl font-bold text-neutral-900">
              {effectiveness?.automation_coverage?.automation_coverage_pct 
                ? `${effectiveness.automation_coverage.automation_coverage_pct.toFixed(1)}%`
                : 'N/A'}
            </p>
            <p className="text-xs text-neutral-500 mt-1">
              {effectiveness?.automation_coverage?.auto_resolution_count || 0} auto / {' '}
              {effectiveness?.automation_coverage?.total_incidents || 0} total
            </p>
          </CardContent>
        </Card>

        <Card variant="elevated">
          <CardContent padding="md">
            <div className="flex items-center gap-2 mb-2">
              <ChartBarIcon className="h-5 w-5 text-warning-600" />
              <h3 className="font-semibold text-neutral-900">ROI</h3>
            </div>
            <p className="text-2xl font-bold text-neutral-900">
              {effectiveness?.roi?.total_value 
                ? `$${effectiveness.roi.total_value.toFixed(0)}`
                : 'N/A'}
            </p>
            <p className="text-xs text-neutral-500 mt-1">
              {effectiveness?.roi?.time_savings_hours 
                ? `${effectiveness.roi.time_savings_hours.toFixed(1)} hours saved`
                : 'No savings calculated'}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card variant="elevated">
        <CardHeader>
          <h3 className="font-semibold text-neutral-900">Top Failing Steps</h3>
        </CardHeader>
        <CardContent padding="md">
          {failingSteps.length === 0 ? (
            <p className="text-sm text-neutral-500">No failing steps identified</p>
          ) : (
            <div className="space-y-2">
              {failingSteps.map((step, idx) => (
                <div key={idx} className="flex justify-between items-center p-3 bg-neutral-50 rounded">
                  <div>
                    <p className="text-sm font-semibold">
                      Runbook {step.runbook_id} • Step {step.step_number}
                    </p>
                    <p className="text-xs text-neutral-600">
                      Failures: {step.failure_count} • Errors: {step.error_types?.join(', ') || 'Unknown'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
