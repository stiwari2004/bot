'use client';

import { useState, useEffect } from 'react';
import { 
  DocumentTextIcon, 
  MagnifyingGlassIcon, 
  PlusIcon,
  Cog6ToothIcon,
  ChartBarIcon,
  BookOpenIcon,
  BoltIcon
} from '@heroicons/react/24/outline';
import { SearchDemo } from '@/components/SearchDemo';
import { RunbookGenerator } from '@/components/RunbookGenerator';
import { RunbookList } from '@/components/RunbookList';
import { FileUpload } from '@/components/FileUpload';
import { SystemStats } from '@/components/SystemStats';
import { TicketAnalyzer } from '@/components/TicketAnalyzer';
import AnalyticsDashboard from '@/components/AnalyticsDashboard';

type Stats = {
  total_documents?: number;
  total_chunks?: number;
};

export default function Home() {
  const [activeTab, setActiveTab] = useState('ticket');
  const [stats, setStats] = useState<Stats | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);  // Force re-render of child components

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      // Use Next.js rewrite to avoid hardcoding host/port
      const response = await fetch(`/api/v1/demo/stats`);
      const data = await response.json();
      setStats(data as Stats);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const handleRunbookGenerated = () => {
    fetchStats();
    setRefreshKey(prev => prev + 1);  // Force RunbookList to refresh
  };

  const tabs = [
    { id: 'ticket', name: 'Ticket Analysis', icon: BoltIcon },
    { id: 'search', name: 'Search Knowledge', icon: MagnifyingGlassIcon },
    { id: 'runbook', name: 'Generate Runbook', icon: BookOpenIcon },
    { id: 'runbooks', name: 'View Runbooks', icon: DocumentTextIcon },
    { id: 'upload', name: 'Upload Files', icon: PlusIcon },
    { id: 'analytics', name: 'Analytics', icon: ChartBarIcon },
    { id: 'stats', name: 'System Stats', icon: Cog6ToothIcon },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <Cog6ToothIcon className="h-8 w-8 text-blue-600" />
              <h1 className="ml-2 text-2xl font-bold text-gray-900">
                Troubleshooting AI
              </h1>
            </div>
            <div className="text-sm text-gray-500">
              AI-Powered IT Infrastructure Troubleshooting
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Overview */}
        {stats && (
          <div className="mb-8 grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center">
                <DocumentTextIcon className="h-8 w-8 text-blue-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Documents</p>
                  <p className="text-2xl font-semibold text-gray-900">{stats.total_documents}</p>
                </div>
              </div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center">
                <ChartBarIcon className="h-8 w-8 text-green-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Chunks</p>
                  <p className="text-2xl font-semibold text-gray-900">{stats.total_chunks}</p>
                </div>
              </div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center">
                <BookOpenIcon className="h-8 w-8 text-purple-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Runbooks</p>
                  <p className="text-2xl font-semibold text-gray-900">-</p>
                </div>
              </div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center">
                <Cog6ToothIcon className="h-8 w-8 text-orange-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Status</p>
                  <p className="text-2xl font-semibold text-green-600">Active</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="mb-8">
          <nav className="flex space-x-8" aria-label="Tabs">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  } whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm flex items-center`}
                >
                  <Icon className="h-5 w-5 mr-2" />
                  {tab.name}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="bg-white rounded-lg shadow">
          {activeTab === 'ticket' && <TicketAnalyzer />}
          {activeTab === 'search' && <SearchDemo />}
          {activeTab === 'runbook' && <RunbookGenerator onRunbookGenerated={handleRunbookGenerated} />}
          {activeTab === 'runbooks' && <RunbookList key={refreshKey} />}
          {activeTab === 'upload' && <FileUpload onFileUploaded={fetchStats} />}
          {activeTab === 'analytics' && <AnalyticsDashboard />}
          {activeTab === 'stats' && <SystemStats stats={stats} />}
        </div>
      </div>
    </div>
  );
}