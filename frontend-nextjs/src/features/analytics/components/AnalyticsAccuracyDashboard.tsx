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
  if (value >= 90) return 'text-emerald-300';
  if (value >= 80) return 'text-amber-300';
  return 'text-red-300';
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
    return <p className="text-sm text-slate-400">Synchronizing accuracy metrics...</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Analytics</p>
          <h2 className="text-2xl font-semibold text-white">Accuracy & Intelligence</h2>
          <p className="text-sm text-slate-400">Measure the end-to-end reliability of the AI agent.</p>
        </div>
        <button
          onClick={refresh}
          className="inline-flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm text-slate-300 hover:border-blue-500 hover:text-white"
        >
          <BoltIcon className="h-4 w-4" />
          Refresh analytics
        </button>
      </div>

      {error && (
        <div className="rounded-2xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          {error}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-3xl border border-slate-900 bg-slate-900/40 p-6 lg:col-span-1">
          <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Overall Accuracy</p>
          <div className="mt-4 flex items-baseline gap-3">
            <p className="text-5xl font-semibold text-white">{snapshot.overall}%</p>
            <div className="flex items-center text-xs text-emerald-300">
              <ArrowTrendingUpIcon className="mr-1 h-4 w-4" />
              +1.8% vs last week
            </div>
          </div>
          <p className="mt-2 text-sm text-slate-400">
            Weighted across retrieval, generation, execution, and resolution components.
          </p>
        </div>

        <div className="rounded-3xl border border-slate-900 bg-slate-900/40 p-6 lg:col-span-2">
          <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Component Breakdown</p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {components.map((component) => (
              <div
                key={component.label}
                className="rounded-2xl border border-slate-800 bg-slate-950/40 p-4 shadow-inner shadow-black/20"
              >
                <p className="text-sm text-slate-400">{component.label}</p>
                <p className={`text-3xl font-semibold ${colorScale(component.value)}`}>
                  {component.value}%
                </p>
                <div className="mt-2 h-2 rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-blue-500 to-emerald-400"
                    style={{ width: `${component.value}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-3xl border border-slate-900 bg-slate-900/40 p-6">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Trend</p>
            <ChartBarIcon className="h-5 w-5 text-slate-500" />
          </div>
          <div className="mt-4 space-y-3 text-sm text-slate-300">
            {snapshot.trend.map((point) => (
              <div key={point.date} className="flex items-center justify-between">
                <span className="text-slate-500">{point.date}</span>
                <span className={point.score >= snapshot.overall ? 'text-emerald-300' : 'text-amber-300'}>
                  {point.score}%
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-slate-900 bg-slate-900/40 p-6">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Alerts</p>
            <ExclamationTriangleIcon className="h-5 w-5 text-amber-300" />
          </div>
          <div className="mt-4 space-y-3 text-sm text-slate-300">
            {snapshot.alerts.map((alert) => (
              <div
                key={alert.id}
                className={`rounded-2xl border px-4 py-3 ${
                  alert.severity === 'critical'
                    ? 'border-red-500/50 bg-red-500/10'
                    : alert.severity === 'warn'
                    ? 'border-amber-500/40 bg-amber-500/10'
                    : 'border-slate-700 bg-slate-900/60'
                }`}
              >
                <p className="font-semibold">{alert.message}</p>
                <p className="text-xs text-slate-400">Alert ID: {alert.id}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-slate-900 bg-slate-900/40 p-6">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Momentum</p>
            <ArrowTrendingDownIcon className="h-5 w-5 text-slate-500" />
          </div>
          <p className="mt-4 text-sm text-slate-400">
            Resolution accuracy improved 2.1% this week. Focus areas: network automation & disk cleanup runbooks.
          </p>
        </div>
      </div>

      <div className="rounded-3xl border border-slate-900 bg-slate-900/40 p-6">
        <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Runbook Performance</p>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-900 text-sm">
            <thead className="text-slate-400">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Runbook</th>
                <th className="px-3 py-2 text-left font-medium">Category</th>
                <th className="px-3 py-2 text-left font-medium">Executions</th>
                <th className="px-3 py-2 text-left font-medium">Success Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-900 text-slate-300">
              {snapshot.runbookPerformance.map((item) => (
                <tr key={item.runbook}>
                  <td className="px-3 py-3 font-semibold text-white">{item.runbook}</td>
                  <td className="px-3 py-3 text-xs text-slate-400">{item.category}</td>
                  <td className="px-3 py-3 text-xs text-slate-400">{item.executions}</td>
                  <td className="px-3 py-3 text-xs">
                    <span className={colorScale(item.successRate)}>{item.successRate}%</span>
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


