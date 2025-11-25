'use client';

import { useState, useEffect } from 'react';
import { 
  DocumentTextIcon, 
  MagnifyingGlassIcon, 
  PlusIcon,
  Cog6ToothIcon,
  ChartBarIcon,
  BookOpenIcon,
  BoltIcon,
  Bars3Icon,
  XMarkIcon,
  CpuChipIcon,
  TicketIcon,
  ChevronDownIcon,
  ChevronUpIcon
} from '@heroicons/react/24/outline';
import { SearchDemo } from '@/components/SearchDemo';
import { RunbookGenerator } from '@/components/RunbookGenerator';
import { RunbookList } from '@/features/runbooks';
import { FileUpload } from '@/components/FileUpload';
import { SystemStats } from '@/components/SystemStats';
import { TicketAnalyzer } from '@/components/TicketAnalyzer';
import AnalyticsDashboard from '@/components/AnalyticsDashboard';
import { ExecutionHistory } from '@/components/ExecutionHistory';
import { RunbookQualityDashboard } from '@/components/RunbookQualityDashboard';
import { AgentDashboard } from '@/components/AgentDashboard';
import { Tickets } from '@/features/tickets';
import { Settings } from '@/features/settings';
import { AgentWorkspace, ActiveSessionView } from '@/features/agent';
import { SessionManager } from '@/components/SessionManager';
import apiConfig from '@/lib/api-config';

type Stats = {
  total_documents?: number;
  total_chunks?: number;
  pending_approvals?: number;
  active_tickets?: number;
  executions_today?: number;
  total_runbooks?: number;
  success_rate?: number;
};

const API_BASE = apiConfig.baseUrl;

export default function Home() {
  const [activeTab, setActiveTab] = useState('tickets'); // Default to Tickets tab
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());
  const [workspaceSessionId, setWorkspaceSessionId] = useState<number | null>(null);
  
  // Debug: Log activeTab changes
  useEffect(() => {
    console.log('[Home] activeTab changed to:', activeTab);
  }, [activeTab]);
  
  // Debug: Log workspaceSessionId changes
  useEffect(() => {
    console.log('[Home] workspaceSessionId changed to:', workspaceSessionId);
  }, [workspaceSessionId]);
  
  // Handle OAuth callback and tab switching from URL params (client-side only)
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const params = new URLSearchParams(window.location.search);
    const tab = params.get('tab');
    
    // Only set tab from URL on initial mount (if present)
    if (tab) {
      console.log('[Home] Setting initial tab from URL:', tab);
      setActiveTab(tab);
    }
    
    // Clean up URL params after reading them
    if (tab || params.has('oauth_success') || params.has('oauth_error') || params.has('connection_id')) {
      const newParams = new URLSearchParams(params);
      newParams.delete('tab');
      const newUrl = window.location.pathname + (newParams.toString() ? `?${newParams.toString()}` : '');
      window.history.replaceState({}, '', newUrl);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run only once on mount

  const toggleSection = (sectionId: string) => {
    setCollapsedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
      }
      return newSet;
    });
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const [statsRes, ticketsRes, approvalsRes, executionsRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/demo/stats`),
        fetch(`${API_BASE}/api/v1/tickets/demo/tickets?limit=100&status=open,in_progress,analyzing`),
        fetch(`${API_BASE}/api/v1/agent/pending-approvals`),
        fetch(`${API_BASE}/api/v1/executions/demo/executions?limit=100`),
      ]);
      
      if (!statsRes.ok || !ticketsRes.ok || !approvalsRes.ok || !executionsRes.ok) {
        throw new Error('Failed to fetch dashboard statistics');
      }

      const statsData = await statsRes.json();
      const ticketsData = await ticketsRes.json();
      const approvalsData = await approvalsRes.json();
      const executionsData = await executionsRes.json();

      const sessions = Array.isArray(executionsData.sessions) ? executionsData.sessions : [];
      const now = new Date();
      const todayString = now.toDateString();

      const executionsToday = sessions.filter((session: any) => {
        if (!session?.started_at) return false;
        const startedAt = new Date(session.started_at);
        return startedAt.toDateString() === todayString;
      }).length;

      const completedSessions = sessions.filter((session: any) => {
        const status = (session?.status || '').toLowerCase();
        return status === 'completed' || status === 'failed';
      });

      const successfulSessions = sessions.filter((session: any) => (session?.status || '').toLowerCase() === 'completed');

      const successRate = completedSessions.length > 0
        ? Math.round((successfulSessions.length / completedSessions.length) * 100)
        : 0;
      
      setStats({
        total_documents: statsData.total_documents || 0,
        total_chunks: statsData.total_chunks || 0,
        total_runbooks: statsData.total_runbooks || 0,
        active_tickets: ticketsData.tickets?.length || 0,
        pending_approvals: approvalsData.pending_approvals?.length || 0,
        executions_today: executionsToday,
        success_rate: successRate,
      });
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const handleRunbookGenerated = () => {
    fetchStats();
    setRefreshKey(prev => prev + 1);
  };

  const workspaceEnabled = process.env.NEXT_PUBLIC_AGENT_WORKSPACE_ENABLED !== 'false';
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  
  const handleSessionLaunched = (sessionId: number) => {
    console.log('[handleSessionLaunched] Called with sessionId:', sessionId);
    console.log('[handleSessionLaunched] Current activeTab:', activeTab);
    console.log('[handleSessionLaunched] workspaceEnabled:', workspaceEnabled);
    
    setWorkspaceSessionId(sessionId);
    setActiveSessionId(sessionId);
    
    // Navigate to agent-workspace to see telemetry
    const targetTab = workspaceEnabled ? 'agent-workspace' : 'agent';
    console.log('[handleSessionLaunched] Setting activeTab to:', targetTab);
    setActiveTab(targetTab);
    setSidebarOpen(false);
    
    console.log('[handleSessionLaunched] Navigation complete');
  };
  type NavigationItem = { id: string; name: string; icon: any; color: string };

  const agentNavigation: NavigationItem[] = [
    { id: 'tickets', name: 'Tickets', icon: TicketIcon, color: 'text-blue-600' },
    workspaceEnabled
      ? { id: 'agent-workspace', name: 'Agent Workspace', icon: BoltIcon, color: 'text-amber-600' }
      : null,
    { id: 'agent', name: 'Agent Dashboard', icon: CpuChipIcon, color: 'text-red-600' },
    { id: 'sessions', name: 'Session Manager', icon: Cog6ToothIcon, color: 'text-orange-600' },
    { id: 'executions', name: 'Execution History', icon: DocumentTextIcon, color: 'text-purple-600' },
  ].filter(Boolean) as NavigationItem[];

  const navigationSections = [
    {
      id: 'agent',
      name: 'AGENT',
      icon: CpuChipIcon,
      items: agentNavigation,
    },
    {
      id: 'assistant',
      name: 'ASSISTANT',
      icon: BookOpenIcon,
      items: [
        { id: 'runbooks', name: 'View Runbooks', icon: BookOpenIcon, color: 'text-green-600' },
        { id: 'runbook', name: 'Generate Runbook', icon: BookOpenIcon, color: 'text-orange-600' },
        { id: 'upload', name: 'Upload Documents', icon: PlusIcon, color: 'text-teal-600' },
        { id: 'quality', name: 'Quality Metrics', icon: ChartBarIcon, color: 'text-indigo-600' },
        { id: 'analytics', name: 'Analytics', icon: ChartBarIcon, color: 'text-cyan-600' },
      ],
    },
    {
      id: 'system',
      name: 'SYSTEM',
      icon: Cog6ToothIcon,
      items: [
        { id: 'settings', name: 'Settings & Connections', icon: Cog6ToothIcon, color: 'text-gray-600' },
        { id: 'stats', name: 'System Stats', icon: Cog6ToothIcon, color: 'text-gray-600' },
      ],
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Header */}
      <div className="bg-white shadow-lg border-b border-gray-200">
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="lg:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
              >
                {sidebarOpen ? (
                  <XMarkIcon className="h-6 w-6 text-gray-600" />
                ) : (
                  <Bars3Icon className="h-6 w-6 text-gray-600" />
                )}
              </button>
              <div className="flex items-center">
                <div className="bg-gradient-to-br from-blue-600 to-indigo-600 p-2 rounded-lg shadow-lg">
                  <Cog6ToothIcon className="h-6 w-6 text-white" />
                </div>
                <div className="ml-3">
                  <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                    Troubleshooting AI
                  </h1>
                  <p className="text-xs text-gray-500 font-medium">AI-Powered IT Infrastructure Assistant</p>
                </div>
              </div>
            </div>
            <div className="hidden md:flex items-center space-x-6">
              {stats && (
                <div className="flex items-center space-x-6 text-sm">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-gray-600 font-medium">System Active</span>
                  </div>
                  <div className="text-gray-400">|</div>
                  <span className="text-gray-600 font-medium">{stats.total_documents || 0} Documents</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="flex">
        {/* Sidebar Navigation */}
        <div className={`
          fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-2xl transform transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          lg:translate-x-0 lg:static lg:inset-0
          pt-20 lg:pt-0
        `}>
          <nav className="px-4 py-6 space-y-4 overflow-y-auto h-full pb-20">
            {navigationSections.map((section) => {
              const SectionIcon = section.icon;
              const isCollapsed = collapsedSections.has(section.id);
              const isAgentSection = section.id === 'agent';
              const isAssistantSection = section.id === 'assistant';
              const isSystemSection = section.id === 'system';
              
              return (
                <div key={section.id} className="space-y-2">
                  {/* Section Header */}
                  <div 
                    className={`flex items-center justify-between px-4 py-2 mb-2 rounded-lg transition-colors
                      ${isAgentSection ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md' : ''}
                      ${isAssistantSection ? 'cursor-pointer hover:bg-gray-50' : ''}
                      ${isSystemSection ? 'bg-gray-50 text-gray-600 uppercase' : ''}
                    `}
                    onClick={isAssistantSection ? () => toggleSection(section.id) : undefined}
                  >
                    <div className="flex items-center space-x-2">
                      <SectionIcon className={`h-4 w-4 ${isAgentSection ? 'text-white' : 'text-gray-500'}`} />
                      <span className={`text-xs font-semibold uppercase tracking-wider
                        ${isAgentSection ? 'text-white font-bold' : ''}
                        ${isSystemSection ? 'text-gray-600' : 'text-gray-500'}
                      `}>
                        {section.name}
                      </span>
                    </div>
                    {isAssistantSection && (
                      <div>
                        {isCollapsed ? (
                          <ChevronDownIcon className="h-4 w-4 text-gray-400" />
                        ) : (
                          <ChevronUpIcon className="h-4 w-4 text-gray-400" />
                        )}
                      </div>
                    )}
                  </div>
                  
                  {/* Section Items */}
                  {!isCollapsed && section.items.map((item) => {
                    const Icon = item.icon;
                    const badgeCount = item.id === 'agent' && stats?.pending_approvals 
                      ? stats.pending_approvals 
                      : item.id === 'tickets' && stats?.active_tickets 
                      ? stats.active_tickets 
                      : null;
                    
                    return (
                      <button
                        key={item.id}
                        onClick={() => {
                          setActiveTab(item.id);
                          setSidebarOpen(false);
                        }}
                        className={`
                          w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 relative
                          ${activeTab === item.id
                            ? isAgentSection
                              ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg transform scale-[1.03]'
                              : 'bg-blue-50 text-blue-600 shadow-md'
                            : isAgentSection
                              ? 'text-gray-700 bg-white border border-blue-100 hover:border-blue-300 hover:shadow-lg'
                              : 'text-gray-700 hover:bg-gray-100 hover:text-blue-600'
                          }
                          ${isAgentSection ? 'font-semibold' : ''}
                        `}
                      >
                        <div className="flex items-center space-x-3">
                          <Icon className={`${isAgentSection ? 'h-7 w-7' : 'h-5 w-5'} ${activeTab === item.id ? (isAgentSection ? 'text-white' : 'text-blue-600') : item.color}`} />
                          <span className={`font-medium ${isAgentSection ? 'text-base tracking-tight' : 'text-sm'}`}>{item.name}</span>
                        </div>
                        {badgeCount !== null && badgeCount > 0 && (
                          <span className={`
                            px-2 py-1 rounded-full text-xs font-bold min-w-[20px] text-center
                            ${activeTab === item.id 
                              ? 'bg-white text-blue-600' 
                              : 'bg-red-500 text-white'
                            }
                          `}>
                            {badgeCount}
                          </span>
                        )}
                      </button>
                    );
                  })}
                  
                  {/* Section Separator */}
                  {section.id !== 'system' && (
                    <div className="border-t border-gray-200 my-2"></div>
                  )}
                </div>
              );
            })}
          </nav>
        </div>

        {/* Main Content */}
        <div className="flex-1 lg:ml-0">
          {/* Stats Overview */}
          {stats && (
            <div className="px-4 sm:px-6 lg:px-8 py-6">
              {/* Agent-focused metrics (Top row) */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow border border-gray-100">
                  <div className="flex items-center">
                    <div className="bg-blue-100 p-3 rounded-lg">
                      <TicketIcon className="h-6 w-6 text-blue-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Active Tickets</p>
                      <p className="text-2xl font-bold text-gray-900">{stats.active_tickets || 0}</p>
                    </div>
                  </div>
                </div>
                <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow border border-gray-100">
                  <div className="flex items-center">
                    <div className="bg-red-100 p-3 rounded-lg">
                      <CpuChipIcon className="h-6 w-6 text-red-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Pending Approvals</p>
                      <p className="text-2xl font-bold text-gray-900">{stats.pending_approvals || 0}</p>
                    </div>
                  </div>
                </div>
                <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow border border-gray-100">
                  <div className="flex items-center">
                    <div className="bg-purple-100 p-3 rounded-lg">
                      <DocumentTextIcon className="h-6 w-6 text-purple-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Executions Today</p>
                      <p className="text-2xl font-bold text-gray-900">{stats.executions_today || 0}</p>
                    </div>
                  </div>
                </div>
                <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow border border-gray-100">
                  <div className="flex items-center">
                    <div className="bg-green-100 p-3 rounded-lg">
                      <ChartBarIcon className="h-6 w-6 text-green-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Success Rate</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {typeof stats.success_rate === 'number' ? `${stats.success_rate}%` : '—'}
                    </p>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Assistant-focused metrics (Bottom row) */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow border border-gray-100">
                  <div className="flex items-center">
                    <div className="bg-purple-100 p-3 rounded-lg">
                      <BookOpenIcon className="h-6 w-6 text-purple-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Runbooks</p>
                      <p className="text-2xl font-bold text-gray-900">{stats.total_runbooks || 0}</p>
                    </div>
                  </div>
                </div>
                <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow border border-gray-100">
                  <div className="flex items-center">
                    <div className="bg-blue-100 p-3 rounded-lg">
                      <DocumentTextIcon className="h-6 w-6 text-blue-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Documents</p>
                      <p className="text-2xl font-bold text-gray-900">{stats.total_documents || 0}</p>
                    </div>
                  </div>
                </div>
                <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow border border-gray-100">
                  <div className="flex items-center">
                    <div className="bg-indigo-100 p-3 rounded-lg">
                      <ChartBarIcon className="h-6 w-6 text-indigo-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Quality Score</p>
                      <p className="text-2xl font-bold text-gray-900">8.5</p>
                    </div>
                  </div>
                </div>
                <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow border border-gray-100">
                  <div className="flex items-center">
                    <div className="bg-orange-100 p-3 rounded-lg">
                      <Cog6ToothIcon className="h-6 w-6 text-orange-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Status</p>
                      <p className="text-2xl font-bold text-green-600">Active</p>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Quick Actions */}
              {(stats.pending_approvals && stats.pending_approvals > 0) && (
                <div className="mt-4 flex items-center gap-3">
                  <a
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      setActiveTab('agent');
                    }}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                  >
                    View Pending Approvals ({stats.pending_approvals})
                  </a>
                  <span className="text-gray-300">|</span>
                  <a
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      setActiveTab('runbook');
                    }}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                  >
                    Generate Runbook
                  </a>
                </div>
              )}
            </div>
          )}

          {/* Tab Content */}
          <div className="px-4 sm:px-6 lg:px-8 pb-8">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
              {activeTab === 'tickets' && <Tickets onSessionLaunched={handleSessionLaunched} />}
              {activeTab === 'active-session' && (
                <div className="p-6">
                  {activeSessionId ? (
                    <ActiveSessionView sessionId={activeSessionId} />
                  ) : (
                    <div className="text-center py-12">
                      <p className="text-gray-600">No active session. Execute a runbook to view live execution.</p>
                      <button
                        onClick={() => setActiveTab('tickets')}
                        className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                      >
                        Go to Tickets
                      </button>
                    </div>
                  )}
                </div>
              )}
              {activeTab === 'agent-workspace' && <AgentWorkspace initialSessionId={workspaceSessionId} />}
              {activeTab === 'agent' && <AgentDashboard />}
              {activeTab === 'sessions' && <SessionManager />}
              {activeTab === 'settings' && <Settings />}
              {activeTab === 'runbooks' && <RunbookList key={refreshKey} />}
              {activeTab === 'runbook' && <RunbookGenerator onRunbookGenerated={handleRunbookGenerated} />}
              {activeTab === 'executions' && <ExecutionHistory />}
              {activeTab === 'quality' && <RunbookQualityDashboard />}
              {activeTab === 'upload' && <FileUpload onFileUploaded={fetchStats} />}
              {activeTab === 'analytics' && <AnalyticsDashboard />}
              {activeTab === 'stats' && <SystemStats stats={stats} />}
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}