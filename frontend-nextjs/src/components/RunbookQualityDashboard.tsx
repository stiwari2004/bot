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
        const response = await fetch(`/api/v1/analytics/demo/runbook-quality?days=${days}`);
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
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <div className="text-gray-600">Loading quality metrics...</div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />
            <p className="text-red-800 font-medium">Error loading metrics</p>
          </div>
          <p className="text-red-700 mt-2 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!data || !data.overall_stats) {
    return (
      <div className="p-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-8 text-center">
          <ChartBarIcon className="h-12 w-12 text-blue-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No metrics yet</h3>
          <p className="text-gray-600 text-sm">
            Execute a few runbooks and capture feedback to populate this dashboard.
          </p>
        </div>
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
    <div className="p-6 space-y-6 bg-slate-50">
      {/* Header */}
      <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Quality Metrics Dashboard</h2>
          <p className="text-gray-600 text-sm mt-1">
            Snapshot of runbook execution performance for the past {days} days.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="metrics-period" className="text-sm font-medium text-gray-700">
            Period
          </label>
          <select
            id="metrics-period"
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
        </div>
      </div>

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
      <section className="bg-white border border-gray-200 rounded-lg shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Daily Trends</h3>
            <p className="text-sm text-gray-600">
              Execution outcomes by day
            </p>
          </div>
        </div>
        {daily_trends.length === 0 ? (
          <div className="px-6 py-6 text-sm text-gray-500">
            No execution activity recorded during this period.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <HeaderCell>Date</HeaderCell>
                  <HeaderCell align="center">Executions</HeaderCell>
                  <HeaderCell align="center">Success Rate</HeaderCell>
                  <HeaderCell align="center">Avg Time</HeaderCell>
                  <HeaderCell align="center">Avg Rating</HeaderCell>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {daily_trends.map((trend) => (
                  <tr key={trend.date} className="hover:bg-gray-50 transition-colors">
                    <BodyCell>{formatDate(trend.date)}</BodyCell>
                    <BodyCell align="center">{trend.total_executions}</BodyCell>
                    <BodyCell align="center">{formatPercentage(trend.success_rate)}</BodyCell>
                    <BodyCell align="center">{formatMinutes(trend.avg_execution_time_minutes)}</BodyCell>
                    <BodyCell align="center">{trend.avg_rating.toFixed(1)}</BodyCell>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Top performers */}
      <section className="bg-white border border-gray-200 rounded-lg shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-3">
          <div className="p-2 bg-green-100 rounded-lg">
            <ArrowTrendingUpIcon className="h-6 w-6 text-green-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Top Performers</h3>
            <p className="text-sm text-gray-600">Runbooks with ≥70% success rate and at least 3 executions</p>
          </div>
        </div>
        {top_performers.length === 0 ? (
          <div className="px-6 py-6 text-sm text-gray-500">
            No runbooks meet the top performer criteria yet.
          </div>
        ) : (
          <div className="p-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {top_performers.map((runbook) => (
              <RunbookSummaryCard key={runbook.runbook_id} runbook={runbook} accent="green" />
            ))}
          </div>
        )}
      </section>

      {/* Underperformers */}
      <section className="bg-white border border-gray-200 rounded-lg shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-3">
          <div className="p-2 bg-red-100 rounded-lg">
            <ArrowTrendingDownIcon className="h-6 w-6 text-red-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Runbooks Needing Attention</h3>
            <p className="text-sm text-gray-600">Runbooks with &lt;50% success rate and at least 3 executions</p>
          </div>
        </div>
        {underperformers.length === 0 ? (
          <div className="px-6 py-6 text-sm text-gray-500">
            No underperforming runbooks – keep up the good work!
          </div>
        ) : (
          <div className="p-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {underperformers.map((runbook) => (
              <RunbookSummaryCard key={runbook.runbook_id} runbook={runbook} accent="red" />
            ))}
          </div>
        )}
      </section>

      {/* All runbooks */}
      <section className="bg-white border border-gray-200 rounded-lg shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">All Runbooks</h3>
          <p className="text-sm text-gray-600 mt-1">
            Comprehensive performance breakdown for every runbook with execution history
          </p>
        </div>
        {all_runbooks.length === 0 ? (
          <div className="px-6 py-6 text-sm text-gray-500">
            No execution data recorded yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <HeaderCell>Runbook</HeaderCell>
                  <HeaderCell align="center">Executions</HeaderCell>
                  <HeaderCell align="center">Success Rate</HeaderCell>
                  <HeaderCell align="center">Avg Time</HeaderCell>
                  <HeaderCell align="center">Avg Rating</HeaderCell>
                  <HeaderCell align="center">Resolution</HeaderCell>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {all_runbooks.map((runbook) => (
                  <tr key={runbook.runbook_id} className="hover:bg-gray-50 transition-colors">
                    <BodyCell>
                      <div className="text-sm font-medium text-gray-900">{runbook.title}</div>
                    </BodyCell>
                    <BodyCell align="center">
                      <div className="text-sm text-gray-600">
                        {runbook.total_executions}
                        <span className="text-gray-400 ml-2">({runbook.successful} ✓ / {runbook.failed} ✗)</span>
                      </div>
                    </BodyCell>
                    <BodyCell align="center">
                      <SuccessBadge value={runbook.success_rate} />
                    </BodyCell>
                    <BodyCell align="center">{formatMinutes(runbook.avg_execution_time_minutes)}</BodyCell>
                    <BodyCell align="center">{runbook.avg_rating.toFixed(1)}</BodyCell>
                    <BodyCell align="center">{formatPercentage(runbook.resolution_rate)}</BodyCell>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
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
    blue: { bg: 'bg-blue-50', icon: 'text-blue-600' },
    green: { bg: 'bg-green-50', icon: 'text-green-600' },
    purple: { bg: 'bg-purple-50', icon: 'text-purple-600' },
    yellow: { bg: 'bg-yellow-50', icon: 'text-yellow-600' },
    red: { bg: 'bg-red-50', icon: 'text-red-600' }
  } as const;

  const colors = colorClasses[color];

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 mb-1">{title}</p>
          <div className="flex items-baseline gap-1">
            <p className="text-3xl font-bold text-gray-900">{value}</p>
            {valueSuffix && <span className="text-lg text-gray-500">{valueSuffix}</span>}
          </div>
          {subtitle && <p className="text-xs text-gray-500 mt-2">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-lg ${colors.bg}`}>
          <span className={colors.icon}>{icon}</span>
        </div>
      </div>
    </div>
  );
}

interface RunbookSummaryCardProps {
  runbook: RunbookMetric;
  accent: 'green' | 'red';
}

function RunbookSummaryCard({ runbook, accent }: RunbookSummaryCardProps) {
  const isPositive = accent === 'green';
  const accentClasses = isPositive
    ? 'bg-green-50 border border-green-200'
    : 'bg-red-50 border border-red-200';
  const titleClasses = isPositive ? 'text-green-700' : 'text-red-700';

  return (
    <div className={`rounded-lg p-4 ${accentClasses}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className={`text-sm font-semibold ${titleClasses}`}>{runbook.title}</h4>
          <p className="text-xs text-gray-600 mt-1">
            {runbook.total_executions} executions • {runbook.successful} successes · {runbook.failed} failures
          </p>
        </div>
        <div className={`text-sm font-semibold ${titleClasses}`}>{formatPercentage(runbook.success_rate)}</div>
      </div>
      <div className="grid grid-cols-2 gap-2 mt-3 text-xs text-gray-600">
        <div>
          <span className="block font-medium text-gray-700">Avg Time</span>
          <span>{formatMinutes(runbook.avg_execution_time_minutes)}</span>
        </div>
        <div>
          <span className="block font-medium text-gray-700">Avg Rating</span>
          <span>{runbook.avg_rating.toFixed(1)}</span>
        </div>
        <div>
          <span className="block font-medium text-gray-700">Resolution Rate</span>
          <span>{formatPercentage(runbook.resolution_rate)}</span>
        </div>
      </div>
    </div>
  );
}

interface TableCellProps {
  children: ReactNode;
  align?: 'left' | 'center' | 'right';
}

function HeaderCell({ children, align = 'left' }: TableCellProps) {
  const alignment = align === 'center' ? 'text-center' : align === 'right' ? 'text-right' : 'text-left';
  return (
    <th className={`px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${alignment}`}>
      {children}
    </th>
  );
}

function BodyCell({ children, align = 'left' }: TableCellProps) {
  const alignment = align === 'center' ? 'text-center' : align === 'right' ? 'text-right' : 'text-left';
  return <td className={`px-6 py-4 whitespace-nowrap ${alignment}`}>{children}</td>;
}

function SuccessBadge({ value }: { value: number }) {
  const state = value >= 70 ? 'good' : value >= 50 ? 'neutral' : 'bad';
  const color = state === 'good' ? 'text-green-600 bg-green-100' : state === 'neutral' ? 'text-yellow-600 bg-yellow-100' : 'text-red-600 bg-red-100';

  return (
    <span className={`inline-flex items-center justify-center px-2 py-1 rounded-full text-xs font-semibold ${color}`}>
      {formatPercentage(value)}
    </span>
  );
}



