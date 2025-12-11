'use client';

import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { apiConfig } from '@/lib/api-config';
import {
  ChartBarIcon,
  CheckCircleIcon,
  ClockIcon,
  StarIcon,
  XCircleIcon,
  ArrowUpIcon,
  ArrowDownIcon
} from '@heroicons/react/24/outline';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface OverallStats {
  total_executions: number;
  successful: number;
  failed: number;
  success_rate: number;
  avg_execution_time_minutes: number;
  min_execution_time_minutes: number;
  max_execution_time_minutes: number;
  avg_rating: number;
  resolution_rate: number;
}

interface DailyTrend {
  date: string;
  total_executions: number;
  success_rate: number;
  avg_execution_time_minutes: number;
  avg_rating: number;
}

interface StepMetric {
  step_type: string;
  step_number: number;
  total_attempts: number;
  completion_rate: number;
  success_rate: number;
  successful: number;
  failed: number;
}

interface RecentExecution {
  id: number;
  issue_description: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  duration_minutes: number | null;
  was_successful: boolean | null;
  rating: number | null;
  issue_resolved: boolean | null;
}

interface RunbookMetricsData {
  runbook_id: number;
  title: string;
  period_days: number;
  overall_stats: OverallStats;
  rating_distribution: Record<number, number>;
  daily_trends: DailyTrend[];
  step_metrics: StepMetric[];
  recent_executions: RecentExecution[];
  message?: string;
}

/**
 * RunbookMetrics - Individual Runbook Performance Metrics
 * 
 * This component displays detailed metrics for a single runbook.
 * Used in a modal when clicking "Metrics" on a specific runbook.
 * 
 * For overall/fleet-wide metrics, see RunbookQualityDashboard.
 */
export function RunbookMetrics({ runbookId }: { runbookId: number }) {
  const [data, setData] = useState<RunbookMetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    fetchMetrics();
  }, [runbookId, days]);

  const fetchMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(apiConfig.endpoints.runbooks.metrics(runbookId, days));
      if (!response.ok) {
        throw new Error('Failed to fetch runbook metrics');
      }
      const metricsData = await response.json();
      setData(metricsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card variant="elevated">
        <CardContent padding="lg">
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            <span className="ml-3 text-neutral-600 font-medium">Loading runbook metrics...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card variant="elevated">
        <CardContent padding="md">
          <div className="flex items-center gap-2">
            <XCircleIcon className="h-5 w-5 text-error-600" />
            <p className="text-error-800 font-medium">Error loading metrics</p>
          </div>
          <p className="text-error-700 mt-2 text-sm">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.message) {
    return (
      <Card variant="elevated">
        <CardContent padding="lg">
          <div className="text-center py-12">
            <div className="p-1.5 rounded-lg bg-primary-100 mx-auto mb-4 w-fit">
              <ChartBarIcon className="h-12 w-12 text-primary-600" />
            </div>
            <h3 className="text-lg font-semibold text-neutral-900 mb-2">No Metrics Available</h3>
            <p className="text-neutral-600 text-sm">
              {data?.message || 'Execute this runbook and provide feedback to see detailed metrics here.'}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const { overall_stats, daily_trends, step_metrics, rating_distribution, recent_executions } = data;

  // Prepare rating distribution data
  const ratingData = Object.entries(rating_distribution)
    .filter(([_, count]) => count > 0)
    .map(([rating, count]) => ({
      name: `${rating} Star${rating !== '1' ? 's' : ''}`,
      value: count,
      rating: Number(rating)
    }))
    .sort((a, b) => b.rating - a.rating);

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <Card variant="elevated">
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="min-w-0 flex-1">
              <div className="flex items-center mb-2">
                <div className="p-1.5 rounded-lg bg-secondary-100 mr-3">
                  <ChartBarIcon className="h-6 w-6 text-secondary-600" />
                </div>
                <h1 className="text-2xl font-semibold text-neutral-900">{data.title}</h1>
              </div>
              <p className="text-sm text-neutral-600">
                Detailed performance metrics for the last {days} days
              </p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <label htmlFor="period-select" className="text-sm font-medium text-neutral-700 whitespace-nowrap">
                Period:
              </label>
              <select
                id="period-select"
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="px-4 py-2 border-2 border-neutral-300 rounded-lg text-sm font-medium text-neutral-900 bg-white hover:border-primary-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all"
              >
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
                <option value={365}>Last year</option>
              </select>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Overall Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Executions"
          value={overall_stats.total_executions}
          icon={<ChartBarIcon className="h-6 w-6" />}
          color="blue"
        />
        <StatCard
          title="Success Rate"
          value={`${overall_stats.success_rate.toFixed(1)}%`}
          icon={<CheckCircleIcon className="h-6 w-6" />}
          color="green"
        />
        <StatCard
          title="Avg Execution Time"
          value={`${overall_stats.avg_execution_time_minutes.toFixed(1)}`}
          valueSuffix=" min"
          icon={<ClockIcon className="h-6 w-6" />}
          color="purple"
          subtitle={`Range: ${overall_stats.min_execution_time_minutes.toFixed(1)} - ${overall_stats.max_execution_time_minutes.toFixed(1)} min`}
        />
        <StatCard
          title="Average Rating"
          value={overall_stats.avg_rating.toFixed(1)}
          valueSuffix="/5"
          icon={<StarIcon className="h-6 w-6" />}
          color="yellow"
        />
      </div>

      {/* Additional Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          title="Successful"
          value={overall_stats.successful}
          icon={<CheckCircleIcon className="h-6 w-6" />}
          color="green"
        />
        <StatCard
          title="Failed"
          value={overall_stats.failed}
          icon={<XCircleIcon className="h-6 w-6" />}
          color="red"
        />
        <StatCard
          title="Resolution Rate"
          value={`${overall_stats.resolution_rate.toFixed(1)}%`}
          icon={<CheckCircleIcon className="h-6 w-6" />}
          color="green"
        />
      </div>

      {/* Daily Trends Chart */}
      {daily_trends && daily_trends.length > 0 && (
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center mb-2">
              <div className="p-1.5 rounded-lg bg-primary-100 mr-3">
                <ChartBarIcon className="h-6 w-6 text-primary-600" />
              </div>
              <h2 className="text-xl font-semibold text-neutral-900">Daily Trends</h2>
            </div>
            <p className="text-sm text-neutral-600">Performance metrics over time</p>
          </CardHeader>
          <CardContent padding="md">
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={daily_trends} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis 
                dataKey="date" 
                stroke="#6b7280"
                tick={{ fill: '#6b7280', fontSize: 12 }}
                tickFormatter={(value) => {
                  const date = new Date(value);
                  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                }}
              />
              <YAxis 
                yAxisId="left" 
                stroke="#6b7280"
                tick={{ fill: '#6b7280', fontSize: 12 }}
              />
              <YAxis 
                yAxisId="right" 
                orientation="right" 
                stroke="#6b7280"
                tick={{ fill: '#6b7280', fontSize: 12 }}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'white', 
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                }}
                labelStyle={{ fontWeight: 600, color: '#111827' }}
              />
              <Legend 
                wrapperStyle={{ paddingTop: '20px' }}
                iconType="line"
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="success_rate"
                stroke="#10b981"
                name="Success Rate %"
                strokeWidth={3}
                dot={{ r: 4, fill: '#10b981' }}
                activeDot={{ r: 6 }}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="avg_execution_time_minutes"
                stroke="#3b82f6"
                name="Avg Time (min)"
                strokeWidth={3}
                dot={{ r: 4, fill: '#3b82f6' }}
                activeDot={{ r: 6 }}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="avg_rating"
                stroke="#f59e0b"
                name="Avg Rating"
                strokeWidth={3}
                dot={{ r: 4, fill: '#f59e0b' }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Rating Distribution */}
      {ratingData.length > 0 && (
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center mb-2">
              <div className="p-1.5 rounded-lg bg-warning-100 mr-3">
                <StarIcon className="h-6 w-6 text-warning-600" />
              </div>
              <h2 className="text-xl font-semibold text-neutral-900">Rating Distribution</h2>
            </div>
            <p className="text-sm text-neutral-600">User feedback ratings breakdown</p>
          </CardHeader>
          <CardContent padding="md">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={ratingData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis 
                dataKey="name" 
                stroke="#6b7280"
                tick={{ fill: '#6b7280', fontSize: 12 }}
              />
              <YAxis 
                stroke="#6b7280"
                tick={{ fill: '#6b7280', fontSize: 12 }}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'white', 
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                }}
              />
              <Bar dataKey="value" fill="#f59e0b" name="Count" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Step Metrics */}
      {step_metrics && step_metrics.length > 0 && (
        <Card variant="elevated" className="overflow-hidden">
          <CardHeader>
            <div className="flex items-center mb-2">
              <div className="p-1.5 rounded-lg bg-secondary-100 mr-3">
                <ChartBarIcon className="h-6 w-6 text-secondary-600" />
              </div>
              <h2 className="text-xl font-semibold text-neutral-900">Step-Level Metrics</h2>
            </div>
            <p className="text-sm text-neutral-600">
              Performance breakdown by individual runbook steps
            </p>
          </CardHeader>
          <CardContent padding="none">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-neutral-200">
                <thead className="bg-neutral-50">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                      Step
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                      Attempts
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                      Completion Rate
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                      Success Rate
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                      Results
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-neutral-200">
                  {step_metrics.map((step, idx) => (
                    <tr key={idx} className="hover:bg-neutral-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-neutral-900">Step {step.step_number}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-1 text-xs font-medium bg-neutral-100 text-neutral-800 rounded capitalize">
                          {step.step_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-neutral-600">{step.total_attempts}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-neutral-600">{step.completion_rate.toFixed(1)}%</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span className={`text-sm font-semibold ${
                            step.success_rate >= 80 ? 'text-success-600' :
                            step.success_rate >= 50 ? 'text-warning-600' : 'text-error-600'
                          }`}>
                            {step.success_rate.toFixed(1)}%
                          </span>
                          <div className="w-20 h-2 bg-neutral-200 rounded-full overflow-hidden">
                            <div 
                              className={`h-full ${
                                step.success_rate >= 80 ? 'bg-success-500' :
                                step.success_rate >= 50 ? 'bg-warning-500' : 'bg-error-500'
                              }`}
                              style={{ width: `${step.success_rate}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-3 text-sm">
                          <span className="text-success-600 font-medium">{step.successful} ✓</span>
                          <span className="text-error-600 font-medium">{step.failed} ✗</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Executions */}
      {recent_executions && recent_executions.length > 0 && (
        <Card variant="elevated" className="overflow-hidden">
          <CardHeader>
            <div className="flex items-center mb-2">
              <div className="p-1.5 rounded-lg bg-primary-100 mr-3">
                <ClockIcon className="h-6 w-6 text-primary-600" />
              </div>
              <h2 className="text-xl font-semibold text-neutral-900">Recent Executions</h2>
            </div>
            <p className="text-sm text-neutral-600">
              Latest execution sessions for this runbook
            </p>
          </CardHeader>
          <CardContent padding="none">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-neutral-200">
                <thead className="bg-neutral-50">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                      Issue
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                      Duration
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                      Rating
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                      Resolved
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-neutral-200">
                  {recent_executions.map((execution) => (
                    <tr key={execution.id} className="hover:bg-neutral-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-neutral-600">
                          {new Date(execution.started_at).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric'
                          })}
                        </div>
                        <div className="text-xs text-neutral-400">
                          {new Date(execution.started_at).toLocaleTimeString('en-US', {
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-neutral-900 max-w-xs truncate" title={execution.issue_description}>
                          {execution.issue_description}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                          execution.was_successful ? 'bg-success-100 text-success-800' :
                          execution.was_successful === false ? 'bg-error-100 text-error-800' :
                          'bg-neutral-100 text-neutral-800'
                        }`}>
                          {execution.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-neutral-600">
                          {execution.duration_minutes ? `${execution.duration_minutes} min` : '-'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {execution.rating ? (
                          <div className="flex items-center gap-1">
                            <StarIcon className="h-4 w-4 text-warning-400" />
                            <span className="text-sm text-neutral-600">{execution.rating}/5</span>
                          </div>
                        ) : (
                          <span className="text-sm text-neutral-400">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {execution.issue_resolved !== null ? (
                          execution.issue_resolved ? (
                            <span className="inline-flex items-center gap-1 text-sm text-success-600 font-medium">
                              <CheckCircleIcon className="h-4 w-4" />
                              Yes
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-sm text-error-600 font-medium">
                              <XCircleIcon className="h-4 w-4" />
                              No
                            </span>
                          )
                        ) : (
                          <span className="text-sm text-neutral-400">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: 'blue' | 'green' | 'purple' | 'yellow' | 'red';
  subtitle?: string;
  valueSuffix?: string;
}

function StatCard({ title, value, icon, color, subtitle, valueSuffix }: StatCardProps) {
  const colorClasses = {
    blue: { bg: 'bg-primary-50', icon: 'text-primary-600', border: 'border-primary-200' },
    green: { bg: 'bg-success-50', icon: 'text-success-600', border: 'border-success-200' },
    purple: { bg: 'bg-secondary-50', icon: 'text-secondary-600', border: 'border-secondary-200' },
    yellow: { bg: 'bg-warning-50', icon: 'text-warning-600', border: 'border-warning-200' },
    red: { bg: 'bg-error-50', icon: 'text-error-600', border: 'border-error-200' }
  };

  const colors = colorClasses[color];

  return (
    <Card variant="elevated" className="p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-semibold text-neutral-600 mb-1">{title}</p>
          <div className="flex items-baseline gap-1">
            <p className="text-3xl font-bold text-neutral-900 bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">{value}</p>
            {valueSuffix && (
              <span className="text-lg text-neutral-500">{valueSuffix}</span>
            )}
          </div>
          {subtitle && (
            <p className="text-xs text-neutral-500 mt-2">{subtitle}</p>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colors.bg} ${colors.icon}`}>
          {icon}
        </div>
      </div>
    </Card>
  );
}
