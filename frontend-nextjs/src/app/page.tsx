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
  XMarkIcon
} from '@heroicons/react/24/outline';
import { SearchDemo } from '@/components/SearchDemo';
import { RunbookGenerator } from '@/components/RunbookGenerator';
import { RunbookList } from '@/components/RunbookList';
import { FileUpload } from '@/components/FileUpload';
import { SystemStats } from '@/components/SystemStats';
import { TicketAnalyzer } from '@/components/TicketAnalyzer';
import AnalyticsDashboard from '@/components/AnalyticsDashboard';
import { ExecutionHistory } from '@/components/ExecutionHistory';

type Stats = {
  total_documents?: number;
  total_chunks?: number;
};

export default function Home() {
  const [activeTab, setActiveTab] = useState('runbooks');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch(`/api/v1/demo/stats`);
      const data = await response.json();
      setStats(data as Stats);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const handleRunbookGenerated = () => {
    fetchStats();
    setRefreshKey(prev => prev + 1);
  };

  const navigation = [
    { id: 'ticket', name: 'Ticket Analysis', icon: BoltIcon, color: 'text-blue-600' },
    { id: 'runbooks', name: 'View Runbooks', icon: BookOpenIcon, color: 'text-green-600' },
    { id: 'runbook', name: 'Generate Runbook', icon: BookOpenIcon, color: 'text-orange-600' },
    { id: 'executions', name: 'Execution History', icon: DocumentTextIcon, color: 'text-purple-600' },
    { id: 'upload', name: 'Upload Files', icon: PlusIcon, color: 'text-teal-600' },
    { id: 'analytics', name: 'Analytics', icon: ChartBarIcon, color: 'text-cyan-600' },
    { id: 'stats', name: 'System Stats', icon: Cog6ToothIcon, color: 'text-gray-600' },
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
          <nav className="px-4 py-6 space-y-2 overflow-y-auto h-full pb-20">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setActiveTab(item.id);
                    setSidebarOpen(false);
                  }}
                  className={`
                    w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200
                    ${activeTab === item.id
                      ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg transform scale-[1.02]'
                      : 'text-gray-700 hover:bg-gray-100 hover:text-blue-600'
                    }
                  `}
                >
                  <Icon className={`h-5 w-5 ${activeTab === item.id ? 'text-white' : item.color}`} />
                  <span className="font-medium">{item.name}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Main Content */}
        <div className="flex-1 lg:ml-0">
          {/* Stats Overview */}
          {stats && (
            <div className="px-4 sm:px-6 lg:px-8 py-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow border border-gray-100">
                  <div className="flex items-center">
                    <div className="bg-blue-100 p-3 rounded-lg">
                      <DocumentTextIcon className="h-6 w-6 text-blue-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Documents</p>
                      <p className="text-2xl font-bold text-gray-900">{stats.total_documents}</p>
                    </div>
                  </div>
                </div>
                <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow border border-gray-100">
                  <div className="flex items-center">
                    <div className="bg-green-100 p-3 rounded-lg">
                      <ChartBarIcon className="h-6 w-6 text-green-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Chunks</p>
                      <p className="text-2xl font-bold text-gray-900">{stats.total_chunks}</p>
                    </div>
                  </div>
                </div>
                <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow border border-gray-100">
                  <div className="flex items-center">
                    <div className="bg-purple-100 p-3 rounded-lg">
                      <BookOpenIcon className="h-6 w-6 text-purple-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Runbooks</p>
                      <p className="text-2xl font-bold text-gray-900">63</p>
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
            </div>
          )}

          {/* Tab Content */}
          <div className="px-4 sm:px-6 lg:px-8 pb-8">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
              {activeTab === 'ticket' && <TicketAnalyzer />}
              {activeTab === 'runbooks' && <RunbookList key={refreshKey} />}
              {activeTab === 'runbook' && <RunbookGenerator onRunbookGenerated={handleRunbookGenerated} />}
              {activeTab === 'executions' && <ExecutionHistory />}
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