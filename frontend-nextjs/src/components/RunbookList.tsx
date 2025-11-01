'use client';

import { useState, useEffect } from 'react';
import { BookOpenIcon, EyeIcon, TrashIcon, CheckCircleIcon } from '@heroicons/react/24/outline';

interface Runbook {
  id: number;
  title: string;
  body_md: string;
  confidence: number;
  status?: string;
  meta_data: {
    issue_description: string;
    sources_used: number;
    search_query: string;
    generated_by: string;
  };
  created_at: string;
}

export function RunbookList() {
  const [runbooks, setRunbooks] = useState<Runbook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRunbook, setSelectedRunbook] = useState<Runbook | null>(null);
  const [approving, setApproving] = useState<number | null>(null);

  useEffect(() => {
    fetchRunbooks();
  }, []);

  const fetchRunbooks = async () => {
    try {
      const response = await fetch(`/api/v1/runbooks/demo/`);
      if (!response.ok) {
        throw new Error('Failed to fetch runbooks');
      }
      const data = await response.json();
      setRunbooks(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch runbooks');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this runbook?')) return;

    try {
      const response = await fetch(`/api/v1/runbooks/demo/${id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete runbook');
      }

      // Refetch the list instead of filtering (more reliable)
      await fetchRunbooks();
      if (selectedRunbook?.id === id) {
        setSelectedRunbook(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete runbook');
    }
  };

  const handleApprove = async (id: number) => {
    setApproving(id);
    setError(null);

    try {
      const response = await fetch(`/api/v1/runbooks/demo/${id}/approve`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to approve runbook');
      }

      // Refetch the list to update status
      await fetchRunbooks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve runbook');
    } finally {
      setApproving(null);
    }
  };

  const formatMarkdown = (markdown: string) => {
    // First, extract code blocks to preserve them
    const codeBlocks: string[] = [];
    let processedMarkdown = markdown.replace(/```[\s\S]*?```/g, (match) => {
      const placeholder = `__CODE_BLOCK_${codeBlocks.length}__`;
      codeBlocks.push(match);
      return placeholder;
    });

    // Process markdown without code blocks
    processedMarkdown = processedMarkdown
      .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold text-gray-900 mb-4">$1</h1>')
      .replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold text-gray-800 mb-3 mt-6">$1</h2>')
      .replace(/^### (.*$)/gim, '<h3 class="text-lg font-medium text-gray-700 mb-2 mt-4">$1</h3>')
      .replace(/^\- (.*$)/gim, '<li class="ml-4 text-gray-700">$1</li>')
      .replace(/\n\n/gim, '</p><p class="mb-4 text-gray-700">')
      .replace(/^(?!<[h|l|p|d])/gim, '<p class="mb-4 text-gray-700">')
      .replace(/(?<!>)$/gim, '</p>');

    // Restore code blocks with proper formatting
    codeBlocks.forEach((block, index) => {
      const placeholder = `__CODE_BLOCK_${index}__`;
      const formattedBlock = block
        .replace(/```yaml\n?([\s\S]*?)\n?```/g, '<pre class="bg-gray-100 border border-gray-300 p-4 rounded-lg overflow-x-auto my-4"><code class="text-sm">$1</code></pre>')
        .replace(/```bash\n?([\s\S]*?)\n?```/g, '<pre class="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto my-4"><code class="text-sm">$1</code></pre>')
        .replace(/```([\s\S]*?)\n?```/g, '<pre class="bg-gray-100 border border-gray-300 p-4 rounded-lg overflow-x-auto my-4"><code class="text-sm">$1</code></pre>');
      processedMarkdown = processedMarkdown.replace(placeholder, formattedBlock);
    });

    return processedMarkdown;
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">Loading runbooks...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Generated Runbooks</h2>
        <p className="text-gray-600">View and manage your AI-generated troubleshooting guides</p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
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
            <h3 className="text-lg font-medium text-gray-900">All Runbooks ({runbooks.length})</h3>
            {runbooks.map((runbook) => (
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
                    <div className="flex items-center space-x-2 mb-1">
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
                  <div className="flex items-center space-x-2">
                    {runbook.status === 'draft' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleApprove(runbook.id);
                        }}
                        disabled={approving === runbook.id}
                        className="p-1 text-green-600 hover:text-green-800 disabled:opacity-50"
                        title="Approve & Publish"
                      >
                        <CheckCircleIcon className="h-4 w-4" />
                      </button>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedRunbook(runbook);
                      }}
                      className="p-1 text-gray-400 hover:text-gray-600"
                    >
                      <EyeIcon className="h-4 w-4" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(runbook.id);
                      }}
                      className="p-1 text-gray-400 hover:text-red-600"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Runbook Viewer */}
          <div className="lg:sticky lg:top-6 lg:h-fit">
            {selectedRunbook ? (
              <div className="border border-gray-200 rounded-lg p-6">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900">Runbook Details</h3>
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                    {(selectedRunbook.confidence * 100).toFixed(0)}% confidence
                  </span>
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
    </div>
  );
}
