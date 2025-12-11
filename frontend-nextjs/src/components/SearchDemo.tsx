'use client';

import React, { useState, useMemo, useEffect } from 'react';
import { MagnifyingGlassIcon, DocumentTextIcon, PlayIcon, BookOpenIcon, CheckCircleIcon } from '@heroicons/react/24/outline';
import { RunbookExecutionViewer } from '@/features/executions';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface SearchResult {
  text: string;
  score: number;
  source: string;
  title: string;
  runbook_id?: number;
}

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

interface SearchResponse {
  query: string;
  results_count: number;
  results: SearchResult[];
}

// Color mapping for source types
const sourceColors: Record<string, string> = {
  'runbook': 'bg-secondary-100 text-secondary-800',
  'doc': 'bg-success-100 text-success-800',
  'slack': 'bg-pink-100 text-pink-800',
  'ticket': 'bg-warning-100 text-warning-800',
  'jira': 'bg-primary-100 text-primary-800',
  'servicenow': 'bg-warning-100 text-warning-800',
  'log': 'bg-error-100 text-error-800',
};

// Highlight search terms in text
function highlightText(text: string, query: string): React.JSX.Element[] {
  if (!query.trim()) {
    return [<span key="0">{text}</span>];
  }
  
  const queryWords = query.toLowerCase().split(/\s+/).filter(w => w.length > 0);
  const parts: React.JSX.Element[] = [];
  let lastIndex = 0;
  let keyIndex = 0;
  
  // Create a regex pattern to match any of the query words
  const pattern = new RegExp(`(${queryWords.join('|')})`, 'gi');
  const matches = Array.from(text.matchAll(pattern));
  
  for (const match of matches) {
    const matchIndex = match.index!;
    const matchLength = match[0].length;
    
    // Add text before the match
    if (matchIndex > lastIndex) {
      parts.push(<span key={`text-${keyIndex++}`}>{text.substring(lastIndex, matchIndex)}</span>);
    }
    
    // Add the highlighted match
    parts.push(
      <mark key={`highlight-${keyIndex++}`} className="bg-warning-200 font-semibold">
        {text.substring(matchIndex, matchIndex + matchLength)}
      </mark>
    );
    
    lastIndex = matchIndex + matchLength;
  }
  
  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(<span key={`text-${keyIndex++}`}>{text.substring(lastIndex)}</span>);
  }
  
  return parts.length > 0 ? parts : [<span key="0">{text}</span>];
}

export function SearchDemo() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'score' | 'relevance'>('score');
  const [filterSource, setFilterSource] = useState<string | null>(null);
  const [selectedRunbook, setSelectedRunbook] = useState<Runbook | null>(null);
  const [loadingRunbook, setLoadingRunbook] = useState(false);
  const [executingRunbook, setExecutingRunbook] = useState<number | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('query', query);

      const response = await fetch(`/api/v1/demo/search-demo`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  // Compute filtered and sorted results
  const processedResults = useMemo(() => {
    if (!results) return [];
    
    let filtered = results.results;
    
    // Filter by source if selected
    if (filterSource) {
      filtered = filtered.filter(r => r.source === filterSource);
    }
    
    // Sort by score (already sorted by backend, but we maintain it)
    if (sortBy === 'score') {
      filtered = [...filtered].sort((a, b) => b.score - a.score);
    }
    
    return filtered;
  }, [results, filterSource, sortBy]);

  // Get unique source types from results
  const availableSources = useMemo(() => {
    if (!results) return [];
    return Array.from(new Set(results.results.map(r => r.source))).sort();
  }, [results]);

  // Fetch runbook by ID
  const fetchRunbook = async (runbookId: number) => {
    setLoadingRunbook(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/v1/runbooks/demo/${runbookId}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch runbook');
      }
      
      const data = await response.json();
      setSelectedRunbook(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch runbook');
    } finally {
      setLoadingRunbook(false);
    }
  };

  // Format markdown function (same as RunbookList)
  const formatMarkdown = (markdown: string) => {
    // Simple markdown to HTML conversion
    let html = markdown
      // Headers
      .replace(/^### (.*$)/gim, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>')
      .replace(/^## (.*$)/gim, '<h2 class="text-xl font-bold mt-6 mb-3">$1</h2>')
      .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mt-8 mb-4">$1</h1>')
      // Bold
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/__(.+?)__/g, '<strong>$1</strong>')
      // Italic
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/_(.+?)_/g, '<em>$1</em>')
      // Code blocks
      .replace(/```[\s\S]*?```/g, '<pre class="bg-neutral-100 p-4 rounded overflow-x-auto"><code>$&</code></pre>')
      // Inline code
      .replace(/`([^`]+)`/g, '<code class="bg-neutral-100 px-1 rounded">$1</code>')
      // Lists
      .replace(/^\* (.+)$/gim, '<li class="ml-4">$1</li>')
      .replace(/^- (.+)$/gim, '<li class="ml-4">$1</li>')
      // Links
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:underline">$1</a>');
    
    // Wrap list items in ul tags
    html = html.replace(/(<li.*<\/li>)/g, '<ul class="list-disc pl-4 my-2">$1</ul>');
    
    // Paragraphs
    return html.split('\n\n').map(p => p.trim() ? `<p class="mb-3">${p}</p>` : '').join('');
  };

  return (
    <div className="space-y-6">
      <Card variant="elevated">
        <CardHeader>
          <div className="flex items-center mb-2">
            <div className="p-1.5 rounded-lg bg-secondary-100 mr-3">
              <MagnifyingGlassIcon className="h-6 w-6 text-secondary-600" />
            </div>
            <h2 className="text-2xl font-semibold text-neutral-900">Semantic Search</h2>
          </div>
          <p className="text-sm text-neutral-600">Search through your knowledge base using natural language</p>
        </CardHeader>
      </Card>

      <Card variant="elevated">
        <CardContent padding="md">
          <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-4">
          <div className="flex-1">
            <label htmlFor="search-query" className="sr-only">
              Search query
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                id="search-query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g., network connectivity issues, database errors, server performance..."
                className="block w-full pl-10 pr-3 py-3 border-2 border-neutral-300 rounded-lg leading-5 bg-white placeholder-neutral-500 text-neutral-900 focus:outline-none focus:placeholder-neutral-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all"
              />
            </div>
          </div>
          <Button
            type="submit"
            variant="primary"
            size="lg"
            disabled={loading || !query.trim()}
            isLoading={loading}
          >
            Search
          </Button>
        </div>
          </form>
        </CardContent>
      </Card>

      {error && (
        <Card variant="elevated" className="bg-error-50 border-error-200">
          <CardContent padding="md">
            <p className="text-error-800">{error}</p>
          </CardContent>
        </Card>
      )}

      {results && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Results List */}
          <div className="lg:col-span-2 space-y-4">
            <Card variant="elevated">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-neutral-900">
                    Search Results ({processedResults.length}{filterSource ? ` of ${results.results_count}` : ''})
                  </h3>
                  <div className="flex items-center gap-4">
                    <select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value as 'score' | 'relevance')}
                      className="text-sm border-2 border-neutral-300 rounded-lg px-3 py-1 text-neutral-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all"
                    >
                      <option value="score">Sort by Score</option>
                      <option value="relevance">Sort by Relevance</option>
                    </select>
                    <span className="text-sm text-neutral-500">
                      Query: "{results.query}"
                    </span>
                  </div>
                </div>
              </CardHeader>
              <CardContent padding="md">
                {/* Source filters */}
                {availableSources.length > 0 && (
                  <div className="mb-4 flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-neutral-700">Filter by source:</span>
                    <Button
                      variant={filterSource === null ? "primary" : "outline"}
                      size="sm"
                      onClick={() => setFilterSource(null)}
                    >
                      All
                    </Button>
                    {availableSources.map((source) => (
                      <Button
                        key={source}
                        variant={filterSource === source ? "primary" : "outline"}
                        size="sm"
                        onClick={() => setFilterSource(source)}
                        className={sourceColors[source] || ''}
                      >
                        {source}
                      </Button>
                    ))}
                  </div>
                )}

                {processedResults.map((result, index) => (
                  <Card
                    key={index}
                    variant="elevated"
                    className={`cursor-pointer transition-colors ${
                      result.runbook_id && selectedRunbook?.id === result.runbook_id
                        ? 'border-primary-500 bg-primary-50'
                        : 'hover:border-primary-300'
                    }`}
                    onClick={() => {
                      if (result.runbook_id) {
                        fetchRunbook(result.runbook_id);
                      }
                    }}
                  >
                    <CardContent padding="md">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center">
                          <DocumentTextIcon className="h-5 w-5 text-primary-600 mr-2" />
                          <h4 className="font-semibold text-neutral-900">{result.title}</h4>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            sourceColors[result.source] || 'bg-neutral-100 text-neutral-800'
                          }`}>
                            {result.source}
                          </span>
                          <span className="text-sm text-neutral-500">
                            Score: {(result.score * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                      <p className="text-neutral-700 text-sm leading-relaxed">
                        {highlightText(
                          result.text.length > 200 
                            ? `${result.text.substring(0, 200)}...` 
                            : result.text,
                          query
                        )}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Runbook Viewer */}
          <div className="lg:sticky lg:top-6 lg:h-fit">
            {loadingRunbook ? (
              <Card variant="elevated">
                <CardContent padding="lg">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
                    <p className="mt-2 text-sm text-neutral-500">Loading runbook...</p>
                  </div>
                </CardContent>
              </Card>
            ) : selectedRunbook ? (
              <Card variant="elevated">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-neutral-900">Runbook Details</h3>
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-success-100 text-success-800">
                      {(selectedRunbook.confidence * 100).toFixed(0)}% confidence
                    </span>
                  </div>
                </CardHeader>
                <CardContent padding="md">
                  <div className="prose max-w-none max-h-96 overflow-y-auto">
                    <div 
                      dangerouslySetInnerHTML={{ 
                        __html: formatMarkdown(selectedRunbook.body_md) 
                      }}
                    />
                  </div>

                  <div className="mt-4 pt-4 border-t border-neutral-200 text-sm text-neutral-500">
                    <p>Generated: {new Date(selectedRunbook.created_at).toLocaleString()}</p>
                    <p>Query: "{selectedRunbook.meta_data.search_query}"</p>
                  </div>

                  <div className="mt-4 flex space-x-2">
                    {selectedRunbook.status === 'approved' && (
                      <Button
                        variant="success"
                        size="sm"
                        onClick={() => setExecutingRunbook(selectedRunbook.id)}
                        leftIcon={<PlayIcon className="h-4 w-4" />}
                        className="flex-1"
                      >
                        Execute
                      </Button>
                    )}
                    {selectedRunbook.status === 'draft' && (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled
                        leftIcon={<CheckCircleIcon className="h-4 w-4" />}
                        className="flex-1"
                        title="Approve in View Runbooks tab"
                      >
                        Approve
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card variant="elevated">
                <CardContent padding="lg">
                  <div className="text-center">
                    <div className="p-1.5 rounded-lg bg-neutral-100 mx-auto mb-4 w-fit">
                      <BookOpenIcon className="h-12 w-12 text-neutral-400" />
                    </div>
                    <h3 className="mt-2 text-sm font-semibold text-neutral-900">Select a runbook</h3>
                    <p className="mt-1 text-sm text-neutral-500">Choose a runbook from the search results to view its details.</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}
      
      {/* Execution Viewer */}
      {executingRunbook && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold text-gray-900">Execute Runbook</h2>
                <button
                  onClick={() => setExecutingRunbook(null)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              {selectedRunbook && (
                <RunbookExecutionViewer 
                  runbookId={executingRunbook} 
                  issueDescription={selectedRunbook.meta_data.issue_description}
                  onComplete={() => {
                    setExecutingRunbook(null);
                    setSelectedRunbook(null);
                  }}
                />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
