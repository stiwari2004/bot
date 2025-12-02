'use client';

import { useMemo } from 'react';
import {
  ChartBarIcon,
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  BoltIcon,
} from '@heroicons/react/24/outline';
import { useAccuracyMetrics } from '../hooks/useAccuracyMetrics';

const colorScale = (value: number) => {
  if (value >= 90) return 'text-emerald-700';
  if (value >= 80) return 'text-amber-700';
  return 'text-red-700';
};

export function AnalyticsAccuracyDashboard() {
  const { snapshot, loading, error, refresh } = useAccuracyMetrics();

  const components = useMemo(() => {
    if (!snapshot) return [];
    return [
      { label: 'Retrieval', value: snapshot.componentScores.retrieval },
      { label: 'Generation', value: snapshot.componentScores.generation },
      { label: 'Execution', value: snapshot.componentScores.execution },
      { label: 'Resolution', value: snapshot.componentScores.resolution },
    ];
  }, [snapshot]);

  if (loading || !snapshot) {
    return <p className="text-sm text-gray-500 text-left">Synchronizing accuracy metrics...</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="text-left">
          <p className="text-xs uppercase tracking-[0.4em] text-gray-500">Analytics</p>
          <h2 className="text-2xl font-semibold text-gray-900">Accuracy & Intelligence</h2>
          <p className="text-sm text-gray-600">Measure the end-to-end reliability of the AI agent.</p>
        </div>
        <button
          onClick={refresh}
          className="inline-flex items-center gap-2 rounded-2xl border border-gray-200 bg-white px-4 py-2 text-sm text-gray-700 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 transition-colors shadow-sm"
        >
          <BoltIcon className="h-4 w-4" />
          Refresh analytics
        </button>
      </div>

      {error && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          {error}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm lg:col-span-1">
          <p className="text-xs uppercase tracking-[0.4em] text-gray-500 text-left">Overall Accuracy</p>
          <div className="mt-4 flex items-baseline gap-3">
            <p className="text-5xl font-semibold text-gray-900">{snapshot.overall}%</p>
            <div className="flex items-center text-xs text-emerald-700">
              <ArrowTrendingUpIcon className="mr-1 h-4 w-4" />
              +1.8% vs last week
            </div>
          </div>
          <p className="mt-2 text-sm text-gray-600 text-left">
            Weighted across retrieval, generation, execution, and resolution components.
          </p>
        </div>

        <div className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm lg:col-span-2">
          <p className="text-xs uppercase tracking-[0.4em] text-gray-500 text-left">Component Breakdown</p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {components.map((component) => (
              <div
                key={component.label}
                className="rounded-2xl border border-gray-100 bg-gradient-to-br from-gray-50 to-indigo-50/30 p-4 hover:shadow-md transition-shadow"
              >
                <p className="text-sm text-gray-600 text-left">{component.label}</p>
                <p className={`text-3xl font-semibold text-left ${colorScale(component.value)}`}>
                  {component.value}%
                </p>
                <div className="mt-2 h-2 rounded-full bg-gray-200">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-blue-500 to-emerald-500"
                    style={{ width: `${component.value}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.4em] text-gray-500">Trend</p>
            <ChartBarIcon className="h-5 w-5 text-gray-400" />
          </div>
          <div className="mt-4 space-y-3 text-sm text-gray-700">
            {snapshot.trend.map((point) => (
              <div key={point.date} className="flex items-center justify-between">
                <span className="text-gray-600">{point.date}</span>
                <span className={point.score >= snapshot.overall ? 'text-emerald-700 font-semibold' : 'text-amber-700 font-semibold'}>
                  {point.score}%
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.4em] text-gray-500">Alerts</p>
            <ExclamationTriangleIcon className="h-5 w-5 text-amber-600" />
          </div>
          <div className="mt-4 space-y-3 text-sm text-gray-700">
            {snapshot.alerts.map((alert) => (
              <div
                key={alert.id}
                className={`rounded-2xl border px-4 py-3 ${
                  alert.severity === 'critical'
                    ? 'border-red-200 bg-red-50'
                    : alert.severity === 'warn'
                    ? 'border-amber-200 bg-amber-50'
                    : 'border-gray-100 bg-gray-50'
                }`}
              >
                <p className="font-semibold text-left">{alert.message}</p>
                <p className="text-xs text-gray-500 text-left mt-1">Alert ID: {alert.id}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.4em] text-gray-500">Momentum</p>
            <ArrowTrendingDownIcon className="h-5 w-5 text-gray-400" />
          </div>
          <p className="mt-4 text-sm text-gray-600 text-left">
            Resolution accuracy improved 2.1% this week. Focus areas: network automation & disk cleanup runbooks.
          </p>
        </div>
      </div>

      <div className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm hover:shadow-md transition-shadow">
        <p className="text-xs uppercase tracking-[0.4em] text-gray-500 text-left">Runbook Performance</p>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100 text-sm">
            <thead className="bg-gray-50 text-gray-700">
              <tr>
                <th className="px-3 py-2 text-left font-semibold">Runbook</th>
                <th className="px-3 py-2 text-left font-semibold">Category</th>
                <th className="px-3 py-2 text-left font-semibold">Executions</th>
                <th className="px-3 py-2 text-left font-semibold">Success Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {snapshot.runbookPerformance.map((item) => (
                <tr key={item.runbook} className="hover:bg-gray-50">
                  <td className="px-3 py-3 font-semibold text-gray-900">{item.runbook}</td>
                  <td className="px-3 py-3 text-xs text-gray-600">{item.category}</td>
                  <td className="px-3 py-3 text-xs text-gray-600">{item.executions}</td>
                  <td className="px-3 py-3 text-xs">
                    <span className={`font-semibold ${colorScale(item.successRate)}`}>{item.successRate}%</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}


