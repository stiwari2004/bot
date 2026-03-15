'use client';

import { useState } from 'react';
import { BookOpenIcon, EyeIcon, TrashIcon, CheckCircleIcon, PlayIcon, MagnifyingGlassIcon, ChartBarIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { RunbookMetrics } from '@/components/RunbookMetrics';
import { useRunbooks } from '../hooks/useRunbooks';
import { useRunbookActions } from '../hooks/useRunbookActions';
import type { Runbook } from '../types';
import { Card, CardHeader, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

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

interface RunbookListProps {
  onSessionLaunched?: (sessionId: number) => void;
}

export function RunbookList({ onSessionLaunched }: RunbookListProps) {
  const [selectedRunbook, setSelectedRunbook] = useState<Runbook | null>(null);
  const [launchingId, setLaunchingId] = useState<number | null>(null);
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

  const handleExecute = async (runbook: Runbook) => {
    if (!onSessionLaunched) return;
    setLaunchingId(runbook.id);
    try {
      const res = await fetch('/api/v1/executions/demo/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          runbook_id: runbook.id,
          issue_description: runbook.meta_data?.issue_description || runbook.title,
        }),
      });
      if (!res.ok) throw new Error('Failed to start session');
      const data = await res.json();
      onSessionLaunched(data.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start execution');
    } finally {
      setLaunchingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <div className="text-neutral-600 font-medium">Loading runbooks...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-xl bg-gradient-to-br from-primary-100 to-secondary-200">
            <BookOpenIcon className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h2 className="text-3xl font-bold text-neutral-900">Runbooks</h2>
            <p className="text-sm text-neutral-600 mt-0.5">View and manage all generated runbooks</p>
          </div>
        </div>
      </div>

      {runbooks.length > 0 && (
        <Card>
          <CardContent padding="md">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-neutral-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search runbooks by title, issue, or content..."
                className="block w-full pl-10 pr-4 py-2.5 border border-neutral-300 rounded-lg leading-5 bg-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all text-neutral-900"
              />
            </div>
          </CardContent>
        </Card>
      )}

      {error && (
        <Card variant="outlined" className="border-error-200 bg-error-50">
          <CardContent padding="md">
            <div className="flex items-center justify-between">
              <p className="text-error-800">{error}</p>
              <Button variant="ghost" size="sm" onClick={() => setError(null)}>
                Dismiss
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {runbooks.length === 0 ? (
        <Card>
          <CardContent padding="lg">
            <div className="text-center py-12">
              <div className="mx-auto w-16 h-16 rounded-full bg-neutral-100 flex items-center justify-center mb-4">
                <BookOpenIcon className="h-8 w-8 text-neutral-400" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-900 mb-1">No runbooks</h3>
              <p className="text-sm text-neutral-600">Get started by generating your first runbook.</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Runbook List */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-neutral-900">
              {searchQuery ? `Search Results (${runbooks.length})` : `All Runbooks (${runbooks.length})`}
            </h3>
            {runbooks.length === 0 ? (
              <Card>
                <CardContent padding="md">
                  <div className="text-center py-8">
                    <p className="text-sm text-neutral-600">No runbooks found matching "{searchQuery}"</p>
                  </div>
                </CardContent>
              </Card>
            ) : (
              runbooks.map((runbook) => (
                <Card
                  key={runbook.id}
                  hover
                  onClick={() => setSelectedRunbook(runbook)}
                  variant={selectedRunbook?.id === runbook.id ? 'elevated' : 'default'}
                  className={selectedRunbook?.id === runbook.id ? 'border-primary-300 bg-primary-50' : ''}
                >
                  <CardContent padding="md">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                          <h4 className="font-semibold text-neutral-900">{runbook.title}</h4>
                          {runbook.status && (
                            <Badge
                              variant={runbook.status === 'approved' ? 'success' : runbook.status === 'draft' ? 'warning' : 'secondary'}
                              size="sm"
                            >
                              {runbook.status.charAt(0).toUpperCase() + runbook.status.slice(1)}
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-neutral-600 mb-3 line-clamp-2">
                          {runbook.meta_data.issue_description}
                        </p>
                        <div className="flex items-center gap-4 text-xs text-neutral-500">
                          <span className="font-medium">Confidence: {(runbook.confidence * 100).toFixed(0)}%</span>
                          <span className="font-medium">Sources: {runbook.meta_data.sources_used}</span>
                          <span>{new Date(runbook.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-2 flex-shrink-0">
                        <div className="flex items-center gap-2">
                          {runbook.status === 'approved' && onSessionLaunched && (
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleExecute(runbook);
                              }}
                              disabled={launchingId === runbook.id}
                              isLoading={launchingId === runbook.id}
                              leftIcon={<PlayIcon className="h-3 w-3" />}
                            >
                              {launchingId === runbook.id ? 'Starting…' : 'Execute'}
                            </Button>
                          )}
                          {runbook.status === 'draft' && (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleApprove(runbook.id);
                              }}
                              disabled={approving === runbook.id}
                              isLoading={approving === runbook.id}
                              leftIcon={<CheckCircleIcon className="h-3 w-3" />}
                            >
                              Approve
                            </Button>
                          )}
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedRunbook(runbook);
                            }}
                            className="p-1.5 text-neutral-400 hover:text-primary-600 hover:bg-primary-50 rounded transition-colors"
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
                            className="p-1.5 text-neutral-400 hover:text-error-600 hover:bg-error-50 rounded transition-colors"
                            title="Delete Runbook"
                          >
                            <TrashIcon className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>

          {/* Runbook Viewer */}
          <div className="lg:sticky lg:top-6 lg:h-fit">
            {selectedRunbook ? (
              <Card variant="elevated">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-neutral-900">Runbook Details</h3>
                    <div className="flex items-center gap-2">
                      <Badge variant="success" size="sm">
                        {(selectedRunbook.confidence * 100).toFixed(0)}% confidence
                      </Badge>
                      {selectedRunbook.status && (
                        <Badge
                          variant={selectedRunbook.status === 'approved' ? 'success' : selectedRunbook.status === 'draft' ? 'warning' : 'secondary'}
                          size="sm"
                        >
                          {selectedRunbook.status.charAt(0).toUpperCase() + selectedRunbook.status.slice(1)}
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent padding="md">
                  <div className="prose max-w-none max-h-96 overflow-y-auto text-neutral-700">
                    <div 
                      dangerouslySetInnerHTML={{ 
                        __html: formatMarkdown(selectedRunbook.body_md) 
                      }}
                    />
                  </div>

                  <div className="mt-4 pt-4 border-t border-neutral-200 text-sm text-neutral-500">
                    <p className="font-medium">Generated: {new Date(selectedRunbook.created_at).toLocaleString()}</p>
                    <p className="mt-1">Query: "{selectedRunbook.meta_data.search_query}"</p>
                  </div>

                  <div className="mt-4 flex gap-2">
                    {selectedRunbook.status === 'approved' && onSessionLaunched && (
                      <Button
                        variant="primary"
                        onClick={() => handleExecute(selectedRunbook)}
                        disabled={launchingId === selectedRunbook.id}
                        isLoading={launchingId === selectedRunbook.id}
                        leftIcon={<PlayIcon className="h-4 w-4" />}
                        className="flex-1"
                      >
                        {launchingId === selectedRunbook.id ? 'Starting…' : 'Execute'}
                      </Button>
                    )}
                    {selectedRunbook.status === 'draft' && (
                      <>
                        <Button
                          variant="primary"
                          onClick={() => handleApprove(selectedRunbook.id)}
                          disabled={approving === selectedRunbook.id}
                          isLoading={approving === selectedRunbook.id}
                          leftIcon={<CheckCircleIcon className="h-4 w-4" />}
                          className="flex-1"
                        >
                          Approve & Index
                        </Button>
                        {showForceApprove && approving !== selectedRunbook.id && (
                          <Button
                            variant="warning"
                            onClick={() => handleApprove(selectedRunbook.id, true)}
                            size="sm"
                          >
                            Force Approve
                          </Button>
                        )}
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent padding="lg">
                  <div className="text-center py-12">
                    <div className="mx-auto w-16 h-16 rounded-full bg-neutral-100 flex items-center justify-center mb-4">
                      <BookOpenIcon className="h-8 w-8 text-neutral-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-neutral-900 mb-1">Select a runbook</h3>
                    <p className="text-sm text-neutral-600">Choose a runbook from the list to view its details.</p>
                  </div>
                </CardContent>
              </Card>
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



