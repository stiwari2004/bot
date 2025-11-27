'use client';

import { useState, useEffect } from 'react';
import {
  TicketIcon,
  BoltIcon,
  ChartBarIcon,
  BookOpenIcon,
  Cog6ToothIcon,
  Bars3Icon,
  XMarkIcon,
  SparklesIcon,
  CommandLineIcon,
  ShieldCheckIcon,
  ArrowPathIcon,
  PlusIcon,
} from '@heroicons/react/24/outline';
import { Tickets } from '@/features/tickets';
import { Settings } from '@/features/settings';
import { AgentWorkspace } from '@/features/agent';
import { RunbookList } from '@/features/runbooks';
import { RunbookGenerator } from '@/components/RunbookGenerator';
import { FileUpload } from '@/components/FileUpload';
import { SystemStats } from '@/components/SystemStats';
import { useAgentVitals } from '@/features/agent/hooks/useAgentVitals';
import { ExecutionsSurface } from '@/features/executions/components/ExecutionsSurface';
import { AnalyticsAccuracyDashboard } from '@/features/analytics/components/AnalyticsAccuracyDashboard';

type NavItem = {
  id: string;
  name: string;
  description?: string;
  icon: any;
};

type NavSection = {
  id: string;
  label: string;
  icon: any;
  items: NavItem[];
};

export default function Home() {
  const [activeTab, setActiveTab] = useState('tickets');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [workspaceSessionId, setWorkspaceSessionId] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const { vitals, loading: vitalsLoading, error: vitalsError, refresh: refreshVitals } = useAgentVitals();

  const workspaceEnabled = process.env.NEXT_PUBLIC_AGENT_WORKSPACE_ENABLED !== 'false';

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const tab = params.get('tab');
    if (tab) setActiveTab(tab);
    if (tab || params.has('oauth_success') || params.has('oauth_error') || params.has('connection_id')) {
      const newParams = new URLSearchParams(params);
      newParams.delete('tab');
      const newUrl = window.location.pathname + (newParams.toString() ? `?${newParams.toString()}` : '');
      window.history.replaceState({}, '', newUrl);
    }
  }, []);

  const navigationSections: NavSection[] = [
    {
      id: 'agent',
      label: 'Agent Tools',
      icon: BoltIcon,
      items: [
        { id: 'tickets', name: 'Ticket Queue', description: 'Triage & dispatch incoming alerts', icon: TicketIcon },
        ...(workspaceEnabled
          ? [
              {
                id: 'agent-workspace',
                name: 'Live Workspace',
                description: 'Monitor autonomous execution',
                icon: SparklesIcon,
              },
            ]
          : []),
        {
          id: 'executions',
          name: 'Executions Console',
          description: 'Sessions, approvals & history',
          icon: CommandLineIcon,
        },
      ],
    },
    {
      id: 'knowledge',
      label: 'Knowledge & Creation',
      icon: BookOpenIcon,
      items: [
        { id: 'runbooks', name: 'Runbook Library', description: 'Browse & approve runbooks', icon: BookOpenIcon },
        { id: 'runbook', name: 'Generate Runbook', description: 'Create remediation playbooks', icon: SparklesIcon },
        { id: 'upload', name: 'Document Uploads', description: 'Ingest knowledge sources', icon: PlusIcon },
      ],
    },
    {
      id: 'insights',
      label: 'Insights',
      icon: ChartBarIcon,
      items: [
        {
          id: 'analytics',
          name: 'Analytics & Accuracy',
          description: 'Accuracy, trends, system health',
          icon: ShieldCheckIcon,
        },
      ],
    },
    {
      id: 'system',
      label: 'System',
      icon: Cog6ToothIcon,
      items: [
        { id: 'settings', name: 'Settings & Connections', description: 'Connectors & credentials', icon: Cog6ToothIcon },
        { id: 'stats', name: 'System Stats', description: 'Platform diagnostics', icon: ChartBarIcon },
      ],
    },
  ];

  const handleSessionLaunched = (sessionId: number) => {
    setWorkspaceSessionId(sessionId);
    setActiveTab('agent-workspace');
    setSidebarOpen(false);
  };

  const handleRunbookGenerated = () => {
    refreshVitals();
    setRefreshKey((prev) => prev + 1);
  };

  const statusIndicators = [
    { label: 'Active Tickets', value: vitals?.activeTickets ?? '—' },
    { label: 'Pending Approvals', value: vitals?.pendingApprovals ?? '—' },
    { label: 'Executions Today', value: vitals?.executionsToday ?? '—' },
    { label: 'Success Rate', value: vitals ? `${vitals.successRate}%` : '—' },
  ];

  const renderActiveView = () => {
    switch (activeTab) {
      case 'tickets':
        return <Tickets onSessionLaunched={handleSessionLaunched} />;
      case 'agent-workspace':
        return <AgentWorkspace initialSessionId={workspaceSessionId} />;
      case 'executions':
        return <ExecutionsSurface />;
      case 'analytics':
        return <AnalyticsAccuracyDashboard />;
      case 'runbooks':
        return <RunbookList key={refreshKey} />;
      case 'runbook':
        return <RunbookGenerator onRunbookGenerated={handleRunbookGenerated} />;
      case 'upload':
        return <FileUpload onFileUploaded={refreshVitals} />;
      case 'settings':
        return <Settings />;
      case 'stats':
        return (
          <SystemStats
            stats={
              vitals
                ? {
                    total_documents: vitals.totalDocuments,
                    total_chunks: vitals.totalChunks,
                    total_runbooks: vitals.totalRunbooks,
                  }
                : null
            }
          />
        );
      default:
        return <Tickets onSessionLaunched={handleSessionLaunched} />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="flex h-screen overflow-hidden">
        <aside
          className={`fixed inset-y-0 left-0 z-50 w-72 transform border-r border-slate-900 bg-slate-950/95 backdrop-blur-xl transition-transform duration-300 lg:static lg:translate-x-0 ${
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between px-6 py-6 lg:justify-start">
              <div className="flex items-center space-x-3">
                <div className="rounded-xl bg-blue-600/20 p-2">
                  <SparklesIcon className="h-6 w-6 text-blue-300" />
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Troubleshooting</p>
                  <p className="text-lg font-semibold text-white">AI Agent</p>
                </div>
              </div>
              <button
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 lg:hidden"
                onClick={() => setSidebarOpen(false)}
                aria-label="Close navigation"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
            <nav className="flex-1 overflow-y-auto px-4 pb-6">
              <div className="space-y-6">
                {navigationSections.map((section) => (
                  <div key={section.id} className="space-y-3">
                    <div className="flex items-center space-x-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
                      <section.icon className="h-4 w-4 text-slate-400" />
                      <span>{section.label}</span>
                    </div>
                    <div className="space-y-2">
                      {section.items.map((item) => {
                        const isActive = activeTab === item.id;
                        return (
                          <button
                            key={item.id}
                            onClick={() => {
                              setActiveTab(item.id);
                              setSidebarOpen(false);
                            }}
                            className={`w-full rounded-2xl border px-4 py-3 text-left transition-all ${
                              isActive
                                ? 'border-blue-500/40 bg-blue-500/10 text-white shadow-lg shadow-blue-500/20'
                                : 'border-slate-800 bg-slate-900/60 text-slate-300 hover:border-slate-700 hover:bg-slate-900'
                            }`}
                          >
                            <div className="flex items-center space-x-3">
                              <item.icon className={`h-5 w-5 ${isActive ? 'text-blue-300' : 'text-slate-500'}`} />
                              <div>
                                <p className="text-sm font-semibold">{item.name}</p>
                                {item.description && (
                                  <p className="text-xs text-slate-500">{item.description}</p>
                                )}
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </nav>
            <div className="border-t border-slate-900 p-4">
              <button className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm font-medium text-slate-200 hover:border-blue-500 hover:text-white">
                <CommandLineIcon className="h-4 w-4" />
                Command Palette
              </button>
            </div>
          </div>
        </aside>

        <div className="flex flex-1 flex-col">
          <header className="flex items-center justify-between border-b border-slate-900 bg-slate-950/80 px-8 py-5">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(true)}
                className="rounded-xl border border-slate-800 p-2 text-slate-400 hover:border-blue-500 hover:text-white lg:hidden"
                aria-label="Open navigation"
              >
                <Bars3Icon className="h-5 w-5" />
              </button>
              <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Control Center</p>
              <div>
                <h1 className="text-2xl font-semibold text-white">Autonomous Troubleshooting Agent</h1>
                <p className="text-sm text-slate-400">Monitor, guide, and measure your AI responder</p>
              </div>
            </div>
            <div className="hidden md:flex items-center gap-3">
              <button
                onClick={refreshVitals}
                className="flex items-center gap-2 rounded-xl border border-slate-800 px-4 py-2 text-sm text-slate-300 hover:border-blue-500 hover:text-white"
              >
                <ArrowPathIcon className="h-4 w-4" />
                Sync vitals
              </button>
              <button
                onClick={() => setSidebarOpen(true)}
                className="rounded-xl border border-slate-800 px-3 py-2 text-slate-300 hover:border-blue-500 hover:text-white lg:hidden"
              >
                <Bars3Icon className="h-5 w-5" />
              </button>
            </div>
          </header>

          <section className="border-b border-slate-900 bg-slate-950/80 px-8 py-4">
            <div className="flex flex-wrap gap-3">
              {statusIndicators.map((indicator) => (
                <div
                  key={indicator.label}
                  className="rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm text-slate-300"
                >
                  <p className="text-xs uppercase tracking-wider text-slate-500">{indicator.label}</p>
                  <p className="text-lg font-semibold text-white">
                    {vitalsLoading ? '...' : indicator.value}
                  </p>
                </div>
              ))}
              {vitalsError && (
                <div className="rounded-2xl border border-red-500/40 bg-red-500/10 px-4 py-2 text-sm text-red-200">
                  {vitalsError}
                </div>
              )}
            </div>
          </section>

          <main className="flex-1 overflow-auto px-8 py-6">
            <div className="rounded-3xl border border-slate-900 bg-slate-900/40 p-6 shadow-2xl shadow-black/30">
              {renderActiveView()}
            </div>
          </main>
        </div>
      </div>

      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}
    </div>
  );
}
