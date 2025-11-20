'use client';

import { useState, useEffect, useCallback } from 'react';
import type { Runbook } from '../types';

export function useRunbooks() {
  const [runbooks, setRunbooks] = useState<Runbook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchRunbooks = useCallback(async () => {
    try {
      const response = await fetch(`/api/v1/runbooks/demo/`);
      if (!response.ok) {
        throw new Error('Failed to fetch runbooks');
      }
      const data = await response.json();
      setRunbooks(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch runbooks');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRunbooks();
  }, [fetchRunbooks]);

  const filteredRunbooks = runbooks.filter(runbook => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      runbook.title.toLowerCase().includes(query) ||
      runbook.meta_data.issue_description.toLowerCase().includes(query) ||
      runbook.body_md.toLowerCase().includes(query)
    );
  });

  return {
    runbooks: filteredRunbooks,
    loading,
    error,
    searchQuery,
    setSearchQuery,
    fetchRunbooks,
  };
}



