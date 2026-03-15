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
  UserGroupIcon,
  ServerIcon,
  CurrencyDollarIcon,
  ClockIcon,
  CircleStackIcon,
  DocumentTextIcon,
  CubeTransparentIcon,
} from '@heroicons/react/24/outline';
import { Tickets } from '@/features/tickets';
import { Alerts } from '@/features/alerts';
import { Changes } from '@/features/changes';
import { Settings } from '@/features/settings';
import { AgentWorkspace } from '@/features/agent';
import { RunbookList } from '@/features/runbooks';
import { RunbookGenerator } from '@/components/RunbookGenerator';
import { FileUpload } from '@/components/FileUpload';
import { SystemStats } from '@/components/SystemStats';
import { UserManagement } from '@/features/admin/components/UserManagement';
import { NodeManagement } from '@/features/admin/components/NodeManagement';
import { BillingView } from '@/features/admin/components/BillingView';
import { DiscoveryView } from '@/features/admin/components/DiscoveryView';
import { AuditLogView } from '@/features/admin/components/AuditLogView';
import { ProvisioningDashboard } from '@/features/provisioning';
import { useAgentVitals } from '@/features/agent/hooks/useAgentVitals';
import { ExecutionsSurface } from '@/features/executions/components/ExecutionsSurface';
import { AnalyticsAccuracyDashboard } from '@/features/analytics/components/AnalyticsAccuracyDashboard';
import { useAuth } from '@/contexts/AuthContext';
import { LoginPage } from '@/components/LoginPage';
import { PasswordChangeModal } from '@/components/PasswordChangeModal';

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
  const { isAuthenticated, loading: authLoading, user, token, logout, mustChangePassword } = useAuth();
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

  // Handle redirects from /admin/* routes
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const pathname = window.location.pathname;
    if (pathname.startsWith('/admin')) {
      const adminPath = pathname.replace('/admin', '').replace(/^\//, '');
      let targetTab = 'admin-users'; // default
      
      if (adminPath === '' || adminPath === 'users') {
        targetTab = 'admin-users';
      } else if (adminPath === 'nodes') {
        targetTab = 'admin-nodes';
      } else if (adminPath === 'billing') {
        targetTab = 'admin-billing';
      } else if (adminPath === 'discovery') {
        targetTab = 'admin-discovery';
      } else if (adminPath === 'settings') {
        targetTab = 'settings';
      } else if (adminPath === 'audit-log') {
        targetTab = 'admin-audit-log';
      }
      
      // Redirect to main page with appropriate tab
      window.history.replaceState({}, '', `/?tab=${targetTab}`);
      setActiveTab(targetTab);
    }
  }, []);

  // Redirect admins to their appropriate admin pages (never on super-admin host – admin.resolvify.tech uses /super-admin/login)
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (authLoading) return;
    const hostname = window.location.hostname;
    const currentPath = window.location.pathname;
    if (hostname === 'admin.resolvify.tech' || currentPath.startsWith('/super-admin/')) return;
    // Wait for user data to be fully loaded (including tenant info)
    if (isAuthenticated && user && user.tenant !== undefined) {
      // Only MSP admins (role === 'msp_admin') go to tenant-admin.
      const isMspAdmin = user.role === 'msp_admin';
      if (isMspAdmin && currentPath === '/') {
        window.location.href = '/tenant-admin';
        return;
      }
      // Tenant admin (non-MSP) and regular users (including legacy 'admin' under MSP tenant): stay on main app
    }
  }, [isAuthenticated, user, authLoading]);

  // Show login page if not authenticated and user hasn't skipped
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-neutral-50 via-white to-neutral-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-neutral-600 font-medium">Loading...</p>
        </div>
      </div>
    );
  }

  // Always show login page if not authenticated (no demo skip in PaaS)
  if (!isAuthenticated) {
    return <LoginPage />;
  }

  // Show password change modal if required - BLOCK access to main app
  if (isAuthenticated && user && mustChangePassword) {
    return (
      <PasswordChangeModal
        onPasswordChanged={() => {
          // After password changed, re-fetch user info to update mustChangePassword flag
          window.location.reload();
        }}
      />
    );
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
        { id: 'changes', name: 'Changes', description: 'Active change windows', icon: ClockIcon },
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
    // System section only for authenticated (non-guest) users
    // Admin features only for tenant admins (role='tenant_admin' – including client admins under MSP tenants).
    ...(isAuthenticated ? [{
      id: 'system',
      label: 'System',
      icon: Cog6ToothIcon,
      items: [
        ...(user && user.role === 'tenant_admin' ? [
          { id: 'settings', name: 'Settings & Connections', description: 'Connectors & credentials', icon: Cog6ToothIcon },
          { id: 'admin-users', name: 'User Management', description: 'Create and manage users', icon: UserGroupIcon },
          { id: 'admin-nodes', name: 'Node Management', description: 'Approve and manage nodes', icon: ServerIcon },
          { id: 'admin-billing', name: 'Billing & Subscription', description: 'View billing details', icon: CurrencyDollarIcon },
          { id: 'admin-discovery', name: 'Discovery', description: 'Agent token, staged assets, create nodes', icon: CircleStackIcon },
          { id: 'admin-audit-log', name: 'Audit log', description: 'View and download execution and generation events', icon: DocumentTextIcon },
        ] : []),
        { id: 'provisioning', name: 'Provisioning', description: 'Create and manage infrastructure assets', icon: CubeTransparentIcon },
        { id: 'stats', name: 'System Stats', description: 'Platform diagnostics', icon: ChartBarIcon },
      ],
    }] : []),
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
      case 'changes':
        return <Changes />;
      case 'agent-workspace':
        return <AgentWorkspace initialSessionId={workspaceSessionId} />;
      case 'executions':
        return <ExecutionsSurface />;
      case 'analytics':
        return <AnalyticsAccuracyDashboard />;
      case 'runbooks':
        return <RunbookList key={refreshKey} onSessionLaunched={handleSessionLaunched} />;
      case 'runbook':
        return <RunbookGenerator onRunbookGenerated={handleRunbookGenerated} />;
      case 'upload':
        return <FileUpload onFileUploaded={refreshVitals} />;
      case 'settings':
        return <Settings />;
      case 'admin-users':
        return <UserManagement />;
      case 'admin-nodes':
        return <NodeManagement />;
      case 'admin-billing':
        return <BillingView />;
      case 'admin-discovery':
        return <DiscoveryView token={token} />;
      case 'admin-audit-log':
        return <AuditLogView />;
      case 'provisioning':
        return <ProvisioningDashboard />;
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
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-neutral-50 text-neutral-900">
      <div className="flex h-screen overflow-hidden">
        <aside
          className={`fixed inset-y-0 left-0 z-50 w-72 transform border-r border-neutral-200 bg-white shadow-xl transition-transform duration-300 lg:static lg:translate-x-0 ${
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between px-6 py-6 lg:justify-start border-b border-neutral-200">
              <div className="flex items-center space-x-3">
                <div className="rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 p-2.5 shadow-lg">
                  <SparklesIcon className="h-6 w-6 text-white" />
                </div>
                <div className="text-left">
                  <p className="text-xs uppercase tracking-[0.3em] text-neutral-500 font-semibold">Troubleshooting</p>
                  <p className="text-lg font-bold text-neutral-900 bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">AI Agent</p>
                </div>
              </div>
              <button
                className="rounded-lg p-2 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 transition-colors lg:hidden"
                onClick={() => setSidebarOpen(false)}
                aria-label="Close navigation"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
            <nav className="flex-1 overflow-y-auto px-4 pb-6 pt-6">
              <div className="space-y-8">
                {navigationSections.map((section) => (
                  <div key={section.id} className="space-y-3">
                    <div className="flex items-center space-x-3 px-2 text-xs font-bold uppercase tracking-widest text-neutral-500">
                      <section.icon className="h-4 w-4 text-primary-500" />
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
                            className={`w-full rounded-xl border-2 px-4 py-3 text-left transition-all duration-200 ${
                              isActive
                                ? 'border-primary-300 bg-gradient-to-r from-primary-50 to-secondary-50 text-primary-900 shadow-lg shadow-primary-100/50'
                                : 'border-neutral-200 bg-white text-neutral-700 hover:border-primary-200 hover:bg-primary-50/30 hover:shadow-md'
                            }`}
                          >
                            <div className="flex items-center space-x-3">
                              <div className={`p-1.5 rounded-lg ${isActive ? 'bg-primary-100' : 'bg-neutral-100'}`}>
                                <item.icon className={`h-5 w-5 flex-shrink-0 ${isActive ? 'text-primary-600' : 'text-neutral-500'}`} />
                              </div>
                              <div className="text-left min-w-0 flex-1">
                                <p className={`text-sm font-semibold ${isActive ? 'text-primary-900' : 'text-neutral-900'}`}>{item.name}</p>
                                {item.description && (
                                  <p className={`text-xs mt-0.5 ${isActive ? 'text-primary-700' : 'text-neutral-500'}`}>{item.description}</p>
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
            <div className="border-t border-neutral-200 p-4 bg-gradient-to-b from-white to-neutral-50">
              <button className="flex w-full items-center justify-center gap-2 rounded-xl border-2 border-primary-200 bg-gradient-to-r from-primary-50 to-secondary-50 px-4 py-2.5 text-sm font-semibold text-primary-700 hover:border-primary-300 hover:from-primary-100 hover:to-secondary-100 hover:text-primary-800 transition-all duration-200 shadow-md hover:shadow-lg">
                <CommandLineIcon className="h-4 w-4" />
                Command Palette
              </button>
            </div>
          </div>
        </aside>

        <div className="flex flex-1 flex-col overflow-hidden">
          <header className="flex items-center justify-between border-b border-neutral-200 bg-white px-8 py-5 shadow-sm">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSidebarOpen(true)}
                className="rounded-xl border-2 border-neutral-200 p-2 text-neutral-600 hover:border-primary-300 hover:text-primary-600 hover:bg-primary-50 lg:hidden transition-all duration-200"
                aria-label="Open navigation"
              >
                <Bars3Icon className="h-5 w-5" />
              </button>
              <div>
                <p className="text-xs uppercase tracking-[0.4em] text-neutral-500 font-bold">Control Center</p>
                <p className="text-sm text-neutral-600 mt-0.5">Monitor, guide, and measure your AI responder</p>
              </div>
            </div>
            <div className="hidden md:flex items-center gap-3">
              {isAuthenticated && user && (
                <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-primary-50 to-secondary-50 border-2 border-primary-200">
                  <span className="text-sm text-primary-700 font-semibold">{user.email}</span>
                  <span className="text-xs text-primary-600 font-medium">({user.role})</span>
                </div>
              )}
              {!isAuthenticated && (
                <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-neutral-100 border-2 border-neutral-200">
                  <span className="text-xs text-neutral-700 font-semibold">Demo Mode</span>
                </div>
              )}
              <button
                onClick={refreshVitals}
                className="flex items-center gap-2 rounded-xl border-2 border-primary-200 bg-white px-4 py-2 text-sm font-semibold text-primary-700 hover:border-primary-300 hover:bg-primary-50 transition-all duration-200 shadow-sm hover:shadow-md"
              >
                <ArrowPathIcon className="h-4 w-4" />
                Sync vitals
              </button>
              {isAuthenticated && (
                <button
                  onClick={logout}
                  className="flex items-center gap-2 rounded-xl border-2 border-error-200 bg-white px-4 py-2 text-sm font-semibold text-error-700 hover:border-error-300 hover:bg-error-50 transition-all duration-200 shadow-sm hover:shadow-md"
                  title="Logout"
                >
                  <ArrowRightOnRectangleIcon className="h-4 w-4" />
                  Logout
                </button>
              )}
            </div>
          </header>

          <section className="border-b border-neutral-200 bg-gradient-to-r from-white to-neutral-50 px-8 py-5">
            <div className="flex flex-wrap gap-4">
              {statusIndicators.map((indicator) => (
                <div
                  key={indicator.label}
                  className="rounded-xl border-2 border-neutral-200 bg-white px-5 py-3 shadow-md hover:shadow-lg transition-all duration-200 hover:border-primary-200 hover:-translate-y-0.5"
                >
                  <p className="text-xs uppercase tracking-wider text-neutral-500 text-left font-semibold mb-1">{indicator.label}</p>
                  <p className="text-2xl font-bold text-neutral-900 text-left bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
                    {vitalsLoading ? '...' : indicator.value}
                  </p>
                </div>
              ))}
              {vitalsError && (
                <div className="rounded-xl border-2 border-error-200 bg-error-50 px-5 py-3 text-sm text-error-700 shadow-md">
                  {vitalsError}
                </div>
              )}
            </div>
          </section>

          <main className="flex-1 overflow-auto px-8 py-6 bg-gradient-to-br from-neutral-50 via-white to-neutral-50">
            <div className="rounded-2xl border-2 border-neutral-200 bg-white p-8 shadow-xl animate-fade-in">
              {renderActiveView()}
            </div>
          </main>
        </div>
      </div>

      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm lg:hidden z-40" onClick={() => setSidebarOpen(false)} />
      )}
    </div>
  );
}