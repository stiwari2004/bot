'use client';

import { useState, useEffect, useCallback } from 'react';
import type { Runbook } from '../types';
import { authFetch } from '@/lib/auth-fetch';

export function useRunbooks() {
  const [runbooks, setRunbooks] = useState<Runbook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchRunbooks = useCallback(async () => {
    // Check if user is authenticated before fetching
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    if (!token) {
      setRunbooks([]);
      setError(null);
      setLoading(false);
      return;
    }

    try {
      const response = await authFetch(`/api/v1/runbooks/demo/`);
      if (!response.ok) {
        // Handle 401 gracefully
        if (response.status === 401) {
          setRunbooks([]);
          setError(null);
          setLoading(false);
          return;
        }
        throw new Error('Failed to fetch runbooks');
      }
      const data = await response.json();
      setRunbooks(data);
      setError(null);
    } catch (err) {
      // Don't set error for 401
      if (!(err instanceof Error && err.message.includes('401'))) {
        setError(err instanceof Error ? err.message : 'Failed to fetch runbooks');
      } else {
        setRunbooks([]);
        setError(null);
      }
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



