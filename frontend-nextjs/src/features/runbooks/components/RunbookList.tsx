'use client';

import { useState } from 'react';
import { BookOpenIcon, EyeIcon, TrashIcon, CheckCircleIcon, PlayIcon, MagnifyingGlassIcon, ChartBarIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { RunbookExecutionViewer } from '@/features/executions';
import { RunbookMetrics } from '@/components/RunbookMetrics';
import { useRunbooks } from '../hooks/useRunbooks';
import { useRunbookActions } from '../hooks/useRunbookActions';
import type { Runbook } from '../types';

const formatMarkdown = (md: string) => {
  // Simple markdown to HTML conversion (basic)
  return md
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    .replace(/`(.*?)`/gim, '<code>$1</code>')
    .replace(/\n/gim, '<br>');
};

export function RunbookList() {
  const [selectedRunbook, setSelectedRunbook] = useState<Runbook | null>(null);
  const [executingRunbook, setExecutingRunbook] = useState<Runbook | null>(null);
  const [viewingMetricsFor, setViewingMetricsFor] = useState<number | null>(null);

  const {
    runbooks,
    loading,
    error: fetchError,
    searchQuery,
    setSearchQuery,
    fetchRunbooks,
  } = useRunbooks();

  const {
    approving,
    error: actionError,
    showForceApprove,
    setError,
    handleDelete,
    handleApprove,
  } = useRunbookActions(fetchRunbooks);

  const error = fetchError || actionError;

  if (executingRunbook) {
    return (
      <div className="p-6">
        <button
          onClick={() => setExecutingRunbook(null)}
          className="mb-4 text-blue-600 hover:text-blue-800 flex items-center"
        >
          ← Back to Runbook List
        </button>
        <RunbookExecutionViewer
          runbookId={executingRunbook.id}
          issueDescription={executingRunbook.meta_data.issue_description}
          onComplete={() => setExecutingRunbook(null)}
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-gray-600">Loading runbooks...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2 flex items-center">
          <BookOpenIcon className="h-7 w-7 mr-2 text-blue-600" />
          Runbooks
        </h2>
        <p className="text-gray-600">View and manage all generated runbooks</p>
      </div>

      {runbooks.length > 0 && (
        <div className="mb-6">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search runbooks by title, issue, or content..."
              className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
      )}

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
          <button
            onClick={() => setError(null)}
            className="mt-2 text-sm text-red-600 hover:text-red-800"
          >
            Dismiss
          </button>
        </div>
      )}

      {runbooks.length === 0 ? (
        <div className="text-center py-12">
          <BookOpenIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No runbooks</h3>
          <p className="mt-1 text-sm text-gray-500">Get started by generating your first runbook.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Runbook List */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900">
              {searchQuery ? `Search Results (${runbooks.length})` : `All Runbooks (${runbooks.length})`}
            </h3>
            {runbooks.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-sm text-gray-500">No runbooks found matching "{searchQuery}"</p>
              </div>
            ) : (
              runbooks.map((runbook) => (
                <div
                  key={runbook.id}
                  className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                    selectedRunbook?.id === runbook.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => setSelectedRunbook(runbook)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <h4 className="font-medium text-gray-900">{runbook.title}</h4>
                        {runbook.status && (
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                            runbook.status === 'draft' ? 'bg-yellow-100 text-yellow-800' :
                            runbook.status === 'approved' ? 'bg-green-100 text-green-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {runbook.status.charAt(0).toUpperCase() + runbook.status.slice(1)}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mb-2">
                        {runbook.meta_data.issue_description}
                      </p>
                      <div className="flex items-center space-x-4 text-xs text-gray-500">
                        <span>Confidence: {(runbook.confidence * 100).toFixed(0)}%</span>
                        <span>Sources: {runbook.meta_data.sources_used}</span>
                        <span>{new Date(runbook.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end space-y-2 ml-4">
                      <div className="flex items-center space-x-2">
                        {runbook.status === 'approved' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setExecutingRunbook(runbook);
                            }}
                            className="flex items-center px-3 py-1 bg-green-600 text-white text-xs font-medium rounded-lg hover:bg-green-700 transition-colors whitespace-nowrap"
                            title="Execute Runbook"
                          >
                            <PlayIcon className="h-3 w-3 mr-1" />
                            Execute
                          </button>
                        )}
                        {runbook.status === 'draft' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleApprove(runbook.id);
                            }}
                            disabled={approving === runbook.id}
                            className="p-1 text-blue-600 hover:text-blue-800 disabled:opacity-50"
                            title="Approve & Publish"
                          >
                            <CheckCircleIcon className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                      <div className="flex items-center space-x-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedRunbook(runbook);
                          }}
                          className="p-1 text-gray-400 hover:text-gray-600"
                          title="View Details"
                        >
                          <EyeIcon className="h-4 w-4" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(runbook.id, () => {
                              if (selectedRunbook?.id === runbook.id) {
                                setSelectedRunbook(null);
                              }
                            });
                          }}
                          className="p-1 text-gray-400 hover:text-red-600"
                          title="Delete Runbook"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Runbook Viewer */}
          <div className="lg:sticky lg:top-6 lg:h-fit">
            {selectedRunbook ? (
              <div className="border border-gray-200 rounded-lg p-6">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900">Runbook Details</h3>
                  <div className="flex items-center space-x-2">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                      {(selectedRunbook.confidence * 100).toFixed(0)}% confidence
                    </span>
                    {selectedRunbook.status && (
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                        selectedRunbook.status === 'draft' ? 'bg-yellow-100 text-yellow-800' :
                        selectedRunbook.status === 'approved' ? 'bg-green-100 text-green-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {selectedRunbook.status.charAt(0).toUpperCase() + selectedRunbook.status.slice(1)}
                      </span>
                    )}
                  </div>
                </div>

                <div className="prose max-w-none max-h-96 overflow-y-auto">
                  <div 
                    dangerouslySetInnerHTML={{ 
                      __html: formatMarkdown(selectedRunbook.body_md) 
                    }}
                  />
                </div>

                <div className="mt-4 pt-4 border-t border-gray-200 text-sm text-gray-500">
                  <p>Generated: {new Date(selectedRunbook.created_at).toLocaleString()}</p>
                  <p>Query: "{selectedRunbook.meta_data.search_query}"</p>
                </div>

                <div className="mt-4 flex space-x-2">
                  {selectedRunbook.status === 'approved' && (
                    <button
                      onClick={() => setExecutingRunbook(selectedRunbook)}
                      className="flex-1 flex items-center justify-center px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-colors"
                    >
                      <PlayIcon className="h-4 w-4 mr-2" />
                      Execute
                    </button>
                  )}
                  {selectedRunbook.status === 'draft' && (
                    <>
                      <button
                        onClick={() => handleApprove(selectedRunbook.id)}
                        disabled={approving === selectedRunbook.id}
                        className={`flex-1 flex items-center justify-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed`}
                      >
                        <CheckCircleIcon className="h-4 w-4 mr-2" />
                        {approving === selectedRunbook.id ? 'Approving...' : 'Approve & Index'}
                      </button>
                      {showForceApprove && approving !== selectedRunbook.id && (
                        <button
                          onClick={() => handleApprove(selectedRunbook.id, true)}
                          className="flex items-center justify-center px-3 py-2 bg-orange-600 text-white text-xs font-medium rounded-lg hover:bg-orange-700 transition-colors"
                          title="Force approve despite duplicates"
                        >
                          Force Approve
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            ) : (
              <div className="border border-gray-200 rounded-lg p-6 text-center">
                <BookOpenIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">Select a runbook</h3>
                <p className="mt-1 text-sm text-gray-500">Choose a runbook from the list to view its details.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Metrics Modal */}
      {viewingMetricsFor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Runbook Metrics</h3>
              <button
                onClick={() => setViewingMetricsFor(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>
            <div className="p-6">
              <RunbookMetrics runbookId={viewingMetricsFor} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}



