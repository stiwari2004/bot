'use client';

import { useState } from 'react';
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

export function SearchDemo() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('query', query);

      const response = await fetch('http://localhost:8000/api/v1/demo/search-demo', {
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
              Search Results ({results.results_count})
            </h3>
            <span className="text-sm text-gray-500">
              Query: "{results.query}"
            </span>
          </div>

          <div className="space-y-4">
            {results.results.map((result, index) => (
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
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {result.source}
                    </span>
                    <span className="text-sm text-gray-500">
                      Score: {(result.score * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
                <p className="text-gray-700 text-sm leading-relaxed">
                  {result.text.length > 200 
                    ? `${result.text.substring(0, 200)}...` 
                    : result.text
                  }
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
