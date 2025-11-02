'use client';

import React, { useState, useMemo } from 'react';
import { MagnifyingGlassIcon, DocumentTextIcon } from '@heroicons/react/24/outline';

interface SearchResult {
  text: string;
  score: number;
  source: string;
  title: string;
}

interface SearchResponse {
  query: string;
  results_count: number;
  results: SearchResult[];
}

// Color mapping for source types
const sourceColors: Record<string, string> = {
  'runbook': 'bg-purple-100 text-purple-800',
  'doc': 'bg-green-100 text-green-800',
  'slack': 'bg-pink-100 text-pink-800',
  'ticket': 'bg-orange-100 text-orange-800',
  'jira': 'bg-blue-100 text-blue-800',
  'servicenow': 'bg-yellow-100 text-yellow-800',
  'log': 'bg-red-100 text-red-800',
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
      <mark key={`highlight-${keyIndex++}`} className="bg-yellow-200 font-semibold">
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

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Semantic Search</h2>
        <p className="text-gray-600">Search through your knowledge base using natural language</p>
      </div>

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
                className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {results && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              Search Results ({processedResults.length}{filterSource ? ` of ${results.results_count}` : ''})
            </h3>
            <div className="flex items-center gap-4">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'score' | 'relevance')}
                className="text-sm border border-gray-300 rounded-md px-3 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="score">Sort by Score</option>
                <option value="relevance">Sort by Relevance</option>
              </select>
              <span className="text-sm text-gray-500">
                Query: "{results.query}"
              </span>
            </div>
          </div>

          {/* Source filters */}
          {availableSources.length > 0 && (
            <div className="mb-4 flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium text-gray-700">Filter by source:</span>
              <button
                onClick={() => setFilterSource(null)}
                className={`text-sm px-3 py-1 rounded-full transition-colors ${
                  filterSource === null
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                All
              </button>
              {availableSources.map((source) => (
                <button
                  key={source}
                  onClick={() => setFilterSource(source)}
                  className={`text-sm px-3 py-1 rounded-full transition-colors ${sourceColors[source] || 'bg-gray-100 text-gray-800'} ${
                    filterSource === source
                      ? 'ring-2 ring-blue-500 ring-offset-1'
                      : 'hover:opacity-80'
                  }`}
                >
                  {source}
                </button>
              ))}
            </div>
          )}

          <div className="space-y-4">
            {processedResults.map((result, index) => (
              <div
                key={index}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center">
                    <DocumentTextIcon className="h-5 w-5 text-blue-600 mr-2" />
                    <h4 className="font-medium text-gray-900">{result.title}</h4>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      sourceColors[result.source] || 'bg-gray-100 text-gray-800'
                    }`}>
                      {result.source}
                    </span>
                    <span className="text-sm text-gray-500">
                      Score: {(result.score * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
                <p className="text-gray-700 text-sm leading-relaxed">
                  {highlightText(
                    result.text.length > 200 
                      ? `${result.text.substring(0, 200)}...` 
                      : result.text,
                    query
                  )}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
