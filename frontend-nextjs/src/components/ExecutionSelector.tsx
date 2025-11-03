'use client';

import { useState, useEffect } from 'react';
import { PlayIcon, BookOpenIcon } from '@heroicons/react/24/outline';
import { RunbookExecutionViewer } from './RunbookExecutionViewer';

interface Runbook {
  id: number;
  title: string;
  confidence: number;
  status: string;
}

export function ExecutionSelector() {
  const [runbooks, setRunbooks] = useState<Runbook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRunbook, setSelectedRunbook] = useState<Runbook | null>(null);
  const [issueDescription, setIssueDescription] = useState('');

  useEffect(() => {
    fetchRunbooks();
  }, []);

  const fetchRunbooks = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/v1/runbooks/demo/');
      
      if (!response.ok) {
        throw new Error('Failed to fetch runbooks');
      }
      
      const data = await response.json();
      // Filter to only approved runbooks
      setRunbooks(data.filter((rb: Runbook) => rb.status === 'approved'));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load runbooks');
    } finally {
      setLoading(false);
    }
  };

  const handleStartExecution = (runbook: Runbook) => {
    setSelectedRunbook(runbook);
    // Pre-fill issue description from runbook title
    setIssueDescription(runbook.title.replace('Runbook: ', ''));
  };

  const handleExecutionComplete = () => {
    setSelectedRunbook(null);
    setIssueDescription('');
  };

  // If a runbook is selected, show the execution viewer
  if (selectedRunbook) {
    return (
      <div className="p-6">
        <button
          onClick={handleExecutionComplete}
          className="mb-4 text-blue-600 hover:text-blue-800 flex items-center"
        >
          ← Back to Runbook Selection
        </button>
        <RunbookExecutionViewer
          runbookId={selectedRunbook.id}
          issueDescription={issueDescription}
          onComplete={handleExecutionComplete}
        />
      </div>
    );
  }

  // Show runbook selection interface
  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">Loading approved runbooks...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2 flex items-center">
          <PlayIcon className="h-7 w-7 mr-2 text-blue-600" />
          Execute Runbook
        </h2>
        <p className="text-gray-600">
          Select an approved runbook to execute step-by-step
        </p>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {runbooks.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <BookOpenIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">No approved runbooks</h3>
          <p className="mt-2 text-gray-600">
            Generate and approve a runbook first to execute it
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {runbooks.map((runbook) => (
            <div
              key={runbook.id}
              className="border border-gray-200 rounded-lg p-6 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer"
              onClick={() => handleStartExecution(runbook)}
            >
              <div className="flex items-start justify-between mb-4">
                <PlayIcon className="h-6 w-6 text-blue-600" />
                <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded">
                  Approved
                </span>
              </div>
              
              <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
                {runbook.title}
              </h3>
              
              <div className="flex items-center justify-between mt-4 pt-4 border-t">
                <div className="text-sm text-gray-500">
                  Confidence: {((runbook.confidence || 0) * 100).toFixed(0)}%
                </div>
                <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center">
                  Execute
                  <PlayIcon className="h-4 w-4 ml-2" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

