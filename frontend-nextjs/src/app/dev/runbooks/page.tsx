'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { apiConfig } from '@/lib/api-config';
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { 
  BookOpenIcon, 
  ArrowUpTrayIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';

interface DevRunbook {
  id: number;
  title: string;
  status: string;
  confidence: number | null;
  created_at: string;
  updated_at: string;
  promoted_from_id: number | null;
  promoted_at: string | null;
}

export default function DevRunbooksPage() {
  const { user } = useAuth();
  const [runbooks, setRunbooks] = useState<DevRunbook[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [promoting, setPromoting] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchRunbooks = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const url = apiConfig.endpoints.dev.runbooks.list(statusFilter || undefined);
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch runbooks');
      }

      const data = await response.json();
      setRunbooks(data.runbooks || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load runbooks');
      console.error('Error fetching runbooks:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchRunbooks();
    }
  }, [user, statusFilter]);

  const handlePromote = async (runbookId: number) => {
    setPromoting(runbookId);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(apiConfig.endpoints.dev.runbooks.promote(runbookId, false), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to promote runbook');
      }

      const data = await response.json();
      alert(`Runbook promoted successfully! Production runbook ID: ${data.production_runbook_id}`);
      fetchRunbooks();
    } catch (err: any) {
      setError(err.message || 'Failed to promote runbook');
      console.error('Error promoting runbook:', err);
    } finally {
      setPromoting(null);
    }
  };

  const filteredRunbooks = runbooks.filter(rb => 
    !searchQuery || rb.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'approved':
        return <Badge variant="success">Approved</Badge>;
      case 'draft':
        return <Badge variant="secondary">Draft</Badge>;
      case 'archived':
        return <Badge variant="error">Archived</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-xl bg-gradient-to-br from-yellow-100 to-orange-200">
            <BookOpenIcon className="h-6 w-6 text-yellow-600" />
          </div>
          <div>
            <h2 className="text-3xl font-bold text-neutral-900">Dev Runbooks</h2>
            <p className="text-sm text-neutral-600 mt-0.5">Create and test runbooks in development environment</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardContent padding="md">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-neutral-400" />
              <input
                type="text"
                placeholder="Search runbooks..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
            <div className="flex gap-2">
              <Button
                variant={statusFilter === '' ? 'primary' : 'ghost'}
                onClick={() => setStatusFilter('')}
              >
                All
              </Button>
              <Button
                variant={statusFilter === 'draft' ? 'primary' : 'ghost'}
                onClick={() => setStatusFilter('draft')}
              >
                Draft
              </Button>
              <Button
                variant={statusFilter === 'approved' ? 'primary' : 'ghost'}
                onClick={() => setStatusFilter('approved')}
              >
                Approved
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Runbooks List */}
      {loading ? (
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
            <div className="text-neutral-600 font-medium">Loading runbooks...</div>
          </div>
        </div>
      ) : filteredRunbooks.length === 0 ? (
        <Card>
          <CardContent padding="lg">
            <div className="text-center py-12">
              <BookOpenIcon className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
              <p className="text-neutral-600">No runbooks found</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {filteredRunbooks.map((runbook) => (
            <Card key={runbook.id}>
              <CardContent padding="md">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-neutral-900">{runbook.title}</h3>
                      {getStatusBadge(runbook.status)}
                      {runbook.promoted_at && (
                        <Badge variant="success">
                          <CheckCircleIcon className="h-4 w-4 mr-1" />
                          Promoted
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-sm text-neutral-600 mt-2">
                      {runbook.confidence && (
                        <span>Confidence: {(runbook.confidence * 100).toFixed(0)}%</span>
                      )}
                      <span>Created: {new Date(runbook.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {runbook.status === 'approved' && !runbook.promoted_at && (
                      <Button
                        variant="primary"
                        onClick={() => handlePromote(runbook.id)}
                        disabled={promoting === runbook.id}
                        leftIcon={<ArrowUpTrayIcon className="h-4 w-4" />}
                      >
                        {promoting === runbook.id ? 'Promoting...' : 'Promote to Prod'}
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

