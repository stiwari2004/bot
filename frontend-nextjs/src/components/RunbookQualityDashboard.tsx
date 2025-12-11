'use client';

import { useState, useEffect, type ReactNode } from 'react';
import {
  ChartBarIcon,
  CheckCircleIcon,
  ClockIcon,
  StarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, TableHeader, TableRow, TableHead, TableCell, TableBody } from '@/components/ui/Table';

interface OverallStats {
  total_runbooks_with_executions: number;
  total_executions: number;
  success_rate: number;
  avg_execution_time_minutes: number;
  avg_rating: number;
  resolution_rate: number;
}

interface RunbookMetric {
  runbook_id: number;
  title: string;
  total_executions: number;
  success_rate: number;
  avg_execution_time_minutes: number;
  avg_rating: number;
  resolution_rate: number;
  successful: number;
  failed: number;
}

interface DailyTrend {
  date: string;
  total_executions: number;
  success_rate: number;
  avg_execution_time_minutes: number;
  avg_rating: number;
}

interface QualityMetricsData {
  period_days: number;
  overall_stats: OverallStats;
  top_performers: RunbookMetric[];
  underperformers: RunbookMetric[];
  all_runbooks: RunbookMetric[];
  daily_trends: DailyTrend[];
}

export function RunbookQualityDashboard() {
  const [data, setData] = useState<QualityMetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    const fetchMetrics = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(apiConfig.endpoints.analytics.runbookQuality(days));
        if (!response.ok) {
          throw new Error('Failed to fetch quality metrics');
        }

        const metricsData = await response.json();
        setData(metricsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch metrics');
        setData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, [days]);

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center min-h-[320px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
            <div className="text-neutral-600 font-medium">Loading quality metrics...</div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Card variant="outlined" className="border-error-200 bg-error-50">
          <CardContent padding="md">
            <div className="flex items-center gap-3">
              <ExclamationTriangleIcon className="h-5 w-5 text-error-600 flex-shrink-0" />
              <div>
                <p className="text-error-800 font-semibold">Error loading metrics</p>
                <p className="text-error-700 mt-1 text-sm">{error}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!data || !data.overall_stats) {
    return (
      <div className="p-6">
        <Card variant="outlined" className="border-primary-200 bg-primary-50">
          <CardContent padding="lg">
            <div className="text-center py-8">
              <div className="mx-auto w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center mb-4">
                <ChartBarIcon className="h-8 w-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-900 mb-2">No metrics yet</h3>
              <p className="text-neutral-600 text-sm">
                Execute a few runbooks and capture feedback to populate this dashboard.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const {
    overall_stats,
    top_performers = [],
    underperformers = [],
    daily_trends = [],
    all_runbooks = []
  } = data;

  return (
    <div className="p-6 space-y-6 bg-gradient-to-br from-neutral-50 via-white to-neutral-50">
      {/* Header */}
      <Card variant="elevated">
        <CardContent padding="md">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="text-3xl font-bold text-neutral-900 mb-1">Quality Metrics Dashboard</h2>
              <p className="text-neutral-600 text-sm">
                Snapshot of runbook execution performance for the past {days} days.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <label htmlFor="metrics-period" className="text-sm font-semibold text-neutral-700">
                Period
              </label>
              <select
                id="metrics-period"
                value={days}
                onChange={(event) => setDays(Number(event.target.value))}
                className="px-4 py-2.5 border-2 border-neutral-300 rounded-lg text-sm font-semibold text-neutral-900 bg-white hover:border-primary-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all"
              >
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
                <option value={365}>Last year</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Overall stats */}
      <section>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <StatCard
            title="Total Executions"
            value={overall_stats.total_executions}
            icon={<ChartBarIcon className="h-6 w-6" />}
            color="blue"
            subtitle={`${overall_stats.total_runbooks_with_executions} runbooks tracked`}
          />
          <StatCard
            title="Success Rate"
            value={formatPercentage(overall_stats.success_rate)}
            icon={<CheckCircleIcon className="h-6 w-6" />}
            color="green"
            subtitle="Overall execution success"
          />
          <StatCard
            title="Avg Execution Time"
            value={formatMinutes(overall_stats.avg_execution_time_minutes)}
            icon={<ClockIcon className="h-6 w-6" />}
            color="purple"
            subtitle="Average duration per runbook"
          />
          <StatCard
            title="Average Rating"
            value={overall_stats.avg_rating.toFixed(1)}
            valueSuffix="/5"
            icon={<StarIcon className="h-6 w-6" />}
            color="yellow"
            subtitle="User feedback"
          />
          <StatCard
            title="Resolution Rate"
            value={formatPercentage(overall_stats.resolution_rate)}
            icon={<CheckCircleIcon className="h-6 w-6" />}
            color="green"
            subtitle="Issues resolved successfully"
          />
          <StatCard
            title="Runbooks with Feedback"
            value={overall_stats.total_runbooks_with_executions}
            icon={<ChartBarIcon className="h-6 w-6" />}
            color="blue"
            subtitle="Runbooks with execution data"
          />
        </div>
      </section>

      {/* Daily trend table */}
      <Card variant="elevated">
        <CardHeader>
          <div>
            <h3 className="text-lg font-semibold text-neutral-900">Daily Trends</h3>
            <p className="text-sm text-neutral-600 mt-1">
              Execution outcomes by day
            </p>
          </div>
        </CardHeader>
        <CardContent padding="none">
          {daily_trends.length === 0 ? (
            <div className="px-6 py-8 text-center">
              <p className="text-sm text-neutral-500">No execution activity recorded during this period.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead className="text-center">Executions</TableHead>
                    <TableHead className="text-center">Success Rate</TableHead>
                    <TableHead className="text-center">Avg Time</TableHead>
                    <TableHead className="text-center">Avg Rating</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {daily_trends.map((trend) => (
                    <TableRow key={trend.date} hover>
                      <TableCell>{formatDate(trend.date)}</TableCell>
                      <TableCell className="text-center">{trend.total_executions}</TableCell>
                      <TableCell className="text-center">{formatPercentage(trend.success_rate)}</TableCell>
                      <TableCell className="text-center">{formatMinutes(trend.avg_execution_time_minutes)}</TableCell>
                      <TableCell className="text-center">{trend.avg_rating.toFixed(1)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Top performers */}
      <Card variant="elevated">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-success-100 rounded-lg">
              <ArrowTrendingUpIcon className="h-6 w-6 text-success-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-neutral-900">Top Performers</h3>
              <p className="text-sm text-neutral-600">Runbooks with ≥70% success rate and at least 3 executions</p>
            </div>
          </div>
        </CardHeader>
        <CardContent padding="md">
          {top_performers.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-sm text-neutral-500">No runbooks meet the top performer criteria yet.</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {top_performers.map((runbook) => (
                <RunbookSummaryCard key={runbook.runbook_id} runbook={runbook} accent="green" />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Underperformers */}
      <Card variant="elevated">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-error-100 rounded-lg">
              <ArrowTrendingDownIcon className="h-6 w-6 text-error-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-neutral-900">Runbooks Needing Attention</h3>
              <p className="text-sm text-neutral-600">Runbooks with &lt;50% success rate and at least 3 executions</p>
            </div>
          </div>
        </CardHeader>
        <CardContent padding="md">
          {underperformers.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-sm text-neutral-500">No underperforming runbooks – keep up the good work!</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {underperformers.map((runbook) => (
                <RunbookSummaryCard key={runbook.runbook_id} runbook={runbook} accent="red" />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* All runbooks */}
      <Card variant="elevated">
        <CardHeader>
          <div>
            <h3 className="text-lg font-semibold text-neutral-900">All Runbooks</h3>
            <p className="text-sm text-neutral-600 mt-1">
              Comprehensive performance breakdown for every runbook with execution history
            </p>
          </div>
        </CardHeader>
        <CardContent padding="none">
          {all_runbooks.length === 0 ? (
            <div className="px-6 py-8 text-center">
              <p className="text-sm text-neutral-500">No execution data recorded yet.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Runbook</TableHead>
                    <TableHead className="text-center">Executions</TableHead>
                    <TableHead className="text-center">Success Rate</TableHead>
                    <TableHead className="text-center">Avg Time</TableHead>
                    <TableHead className="text-center">Avg Rating</TableHead>
                    <TableHead className="text-center">Resolution</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {all_runbooks.map((runbook) => (
                    <TableRow key={runbook.runbook_id} hover>
                      <TableCell>
                        <div className="text-sm font-semibold text-neutral-900">{runbook.title}</div>
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="text-sm text-neutral-600">
                          {runbook.total_executions}
                          <span className="text-neutral-400 ml-2">({runbook.successful} ✓ / {runbook.failed} ✗)</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        <SuccessBadge value={runbook.success_rate} />
                      </TableCell>
                      <TableCell className="text-center">{formatMinutes(runbook.avg_execution_time_minutes)}</TableCell>
                      <TableCell className="text-center">{runbook.avg_rating.toFixed(1)}</TableCell>
                      <TableCell className="text-center">{formatPercentage(runbook.resolution_rate)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function formatPercentage(value: number) {
  return `${value.toFixed(1)}%`;
}

function formatMinutes(value: number) {
  return `${value.toFixed(1)} min`;
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

interface StatCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
  color: 'blue' | 'green' | 'purple' | 'yellow' | 'red';
  subtitle?: string;
  valueSuffix?: string;
}

function StatCard({ title, value, icon, color, subtitle, valueSuffix }: StatCardProps) {
  const colorClasses = {
    blue: { bg: 'bg-primary-50', icon: 'text-primary-600' },
    green: { bg: 'bg-success-50', icon: 'text-success-600' },
    purple: { bg: 'bg-secondary-50', icon: 'text-secondary-600' },
    yellow: { bg: 'bg-warning-50', icon: 'text-warning-600' },
    red: { bg: 'bg-error-50', icon: 'text-error-600' }
  } as const;

  const colors = colorClasses[color];

  return (
    <Card variant="elevated" className="p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-semibold text-neutral-600 mb-1">{title}</p>
          <div className="flex items-baseline gap-1">
            <p className="text-3xl font-bold text-neutral-900 bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">{value}</p>
            {valueSuffix && <span className="text-lg text-neutral-500">{valueSuffix}</span>}
          </div>
          {subtitle && <p className="text-xs text-neutral-500 mt-2">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-lg ${colors.bg}`}>
          <span className={colors.icon}>{icon}</span>
        </div>
      </div>
    </Card>
  );
}

interface RunbookSummaryCardProps {
  runbook: RunbookMetric;
  accent: 'green' | 'red';
}

function RunbookSummaryCard({ runbook, accent }: RunbookSummaryCardProps) {
  const isPositive = accent === 'green';
  const variant = isPositive ? 'default' : 'outlined';
  const borderClass = isPositive ? 'border-success-200 bg-success-50' : 'border-error-200 bg-error-50';
  const titleColor = isPositive ? 'text-success-700' : 'text-error-700';

  return (
    <Card variant={variant} className={`${borderClass}`}>
      <CardContent padding="md">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1">
            <h4 className={`text-sm font-semibold ${titleColor} mb-1`}>{runbook.title}</h4>
            <p className="text-xs text-neutral-600">
              {runbook.total_executions} executions • {runbook.successful} successes · {runbook.failed} failures
            </p>
          </div>
          <Badge variant={isPositive ? 'success' : 'error'} size="sm">
            {formatPercentage(runbook.success_rate)}
          </Badge>
        </div>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div>
            <span className="block font-semibold text-neutral-700 mb-0.5">Avg Time</span>
            <span className="text-neutral-600">{formatMinutes(runbook.avg_execution_time_minutes)}</span>
          </div>
          <div>
            <span className="block font-semibold text-neutral-700 mb-0.5">Avg Rating</span>
            <span className="text-neutral-600">{runbook.avg_rating.toFixed(1)}</span>
          </div>
          <div className="col-span-2">
            <span className="block font-semibold text-neutral-700 mb-0.5">Resolution Rate</span>
            <span className="text-neutral-600">{formatPercentage(runbook.resolution_rate)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SuccessBadge({ value }: { value: number }) {
  const variant = value >= 70 ? 'success' : value >= 50 ? 'warning' : 'error';
  
  return (
    <Badge variant={variant} size="sm">
      {formatPercentage(value)}
    </Badge>
  );
}



