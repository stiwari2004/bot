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
  ArrowRightOnRectangleIcon,
  BellIcon,
} from '@heroicons/react/24/outline';
import { Tickets } from '@/features/tickets';
import { Alerts } from '@/features/alerts';
import { Settings } from '@/features/settings';
import { AgentWorkspace } from '@/features/agent';
import { RunbookList } from '@/features/runbooks';
import { RunbookGenerator } from '@/components/RunbookGenerator';
import { FileUpload } from '@/components/FileUpload';
import { SystemStats } from '@/components/SystemStats';
import { useAgentVitals } from '@/features/agent/hooks/useAgentVitals';
import { ExecutionsSurface } from '@/features/executions/components/ExecutionsSurface';
import { AnalyticsAccuracyDashboard } from '@/features/analytics/components/AnalyticsAccuracyDashboard';
import { useAuth } from '@/contexts/AuthContext';
import { LoginPage } from '@/components/LoginPage';

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
  const { isAuthenticated, loading: authLoading, user, logout } = useAuth();
  const [skipLogin, setSkipLogin] = useState(false);
  const [activeTab, setActiveTab] = useState('tickets');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [workspaceSessionId, setWorkspaceSessionId] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const { vitals, loading: vitalsLoading, error: vitalsError, refresh: refreshVitals } = useAgentVitals();

  const workspaceEnabled = process.env.NEXT_PUBLIC_AGENT_WORKSPACE_ENABLED !== 'false';

  // ALL HOOKS MUST BE CALLED BEFORE ANY CONDITIONAL RETURNS
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

  // Show login page if not authenticated and user hasn't skipped
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Always show login page if not authenticated (unless user explicitly skipped)
  if (!isAuthenticated && !skipLogin) {
    return <LoginPage onSkipLogin={() => setSkipLogin(true)} />;
  }

  // If authenticated or skipped, show main app

  const navigationSections: NavSection[] = [
    {
      id: 'agent',
      label: 'Agent Tools',
      icon: BoltIcon,
      items: [
        { id: 'tickets', name: 'Ticket Queue', description: 'Tickets from ticketing tools', icon: TicketIcon },
        { id: 'alerts', name: 'Alerts', description: 'Alerts from monitoring tools', icon: BellIcon },
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
      case 'alerts':
        return <Alerts />;
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
    <div className="min-h-screen bg-[#fafafa] text-gray-900">
      <div className="flex h-screen overflow-hidden">
        <aside
          className={`fixed inset-y-0 left-0 z-50 w-72 transform border-r border-gray-100 bg-[#fafafa] shadow-lg transition-transform duration-300 lg:static lg:translate-x-0 ${
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between px-6 py-6 lg:justify-start">
              <div className="flex items-center space-x-3">
                <div className="rounded-xl bg-gradient-to-br from-indigo-100 to-violet-100 p-2">
                  <SparklesIcon className="h-6 w-6 text-indigo-600" />
                </div>
                <div className="text-left">
                  <p className="text-xs uppercase tracking-[0.3em] text-gray-500">Troubleshooting</p>
                  <p className="text-lg font-semibold text-gray-900">AI Agent</p>
                </div>
              </div>
              <button
                className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 lg:hidden"
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
                    <div className="flex items-center space-x-3 text-xs font-semibold uppercase tracking-widest text-gray-500">
                      <section.icon className="h-4 w-4 text-gray-400" />
                      <span className="text-left">{section.label}</span>
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
                                ? 'border-indigo-300 bg-gradient-to-r from-indigo-50 to-violet-50 text-indigo-900 shadow-md shadow-indigo-100'
                                : 'border-gray-100 bg-white text-gray-700 hover:border-indigo-200 hover:bg-indigo-50/50'
                            }`}
                          >
                            <div className="flex items-center space-x-3">
                              <item.icon className={`h-5 w-5 flex-shrink-0 ${isActive ? 'text-indigo-600' : 'text-gray-400'}`} />
                              <div className="text-left min-w-0 flex-1">
                                <p className="text-sm font-semibold">{item.name}</p>
                                {item.description && (
                                  <p className="text-xs text-gray-500 mt-0.5">{item.description}</p>
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
            <div className="border-t border-gray-100 p-4">
              <button className="flex w-full items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 transition-colors shadow-sm">
                <CommandLineIcon className="h-4 w-4" />
                Command Palette
              </button>
            </div>
          </div>
        </aside>

        <div className="flex flex-1 flex-col overflow-hidden">
          <header className="flex items-center justify-between border-b border-gray-100 bg-white px-8 py-5 shadow-sm">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(true)}
                className="rounded-xl border border-gray-200 p-2 text-gray-600 hover:border-indigo-300 hover:text-indigo-600 lg:hidden transition-colors"
                aria-label="Open navigation"
              >
                <Bars3Icon className="h-5 w-5" />
              </button>
              <p className="text-xs uppercase tracking-[0.4em] text-gray-500">Control Center</p>
              <div className="text-left">
                <p className="text-sm text-gray-600">Monitor, guide, and measure your AI responder</p>
              </div>
            </div>
            <div className="hidden md:flex items-center gap-3">
              {isAuthenticated && user && (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-50 border border-indigo-200">
                  <span className="text-sm text-indigo-700 font-medium">{user.email}</span>
                  <span className="text-xs text-indigo-500">({user.role})</span>
                </div>
              )}
              {!isAuthenticated && (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-100 border border-gray-200">
                  <span className="text-xs text-gray-600">Demo Mode</span>
                </div>
              )}
              <button
                onClick={refreshVitals}
                className="flex items-center gap-2 rounded-xl border border-gray-200 px-4 py-2 text-sm text-gray-700 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 transition-colors shadow-sm"
              >
                <ArrowPathIcon className="h-4 w-4" />
                Sync vitals
              </button>
              {isAuthenticated && (
                <button
                  onClick={logout}
                  className="flex items-center gap-2 rounded-xl border border-gray-200 px-4 py-2 text-sm text-gray-700 hover:border-red-300 hover:bg-red-50 hover:text-red-700 transition-colors shadow-sm"
                  title="Logout"
                >
                  <ArrowRightOnRectangleIcon className="h-4 w-4" />
                  Logout
                </button>
              )}
              <button
                onClick={() => setSidebarOpen(true)}
                className="rounded-xl border border-gray-200 px-3 py-2 text-gray-600 hover:border-indigo-300 hover:text-indigo-600 lg:hidden transition-colors"
              >
                <Bars3Icon className="h-5 w-5" />
              </button>
            </div>
          </header>

          <section className="border-b border-gray-100 bg-white px-8 py-4">
            <div className="flex flex-wrap gap-3">
              {statusIndicators.map((indicator) => (
                <div
                  key={indicator.label}
                  className="rounded-2xl border border-gray-100 bg-white px-4 py-2 text-sm shadow-sm hover:shadow-md transition-shadow"
                >
                  <p className="text-xs uppercase tracking-wider text-gray-500 text-left">{indicator.label}</p>
                  <p className="text-lg font-semibold text-gray-900 text-left">
                    {vitalsLoading ? '...' : indicator.value}
                  </p>
                </div>
              ))}
              {vitalsError && (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700 shadow-sm">
                  {vitalsError}
                </div>
              )}
            </div>
          </section>

          <main className="flex-1 overflow-auto px-8 py-6 bg-[#fafafa]">
            <div className="rounded-3xl border border-gray-100 bg-white p-6 shadow-lg">
              {renderActiveView()}
            </div>
          </main>
        </div>
      </div>

      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/10 backdrop-blur-sm lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}
    </div>
  );
}
