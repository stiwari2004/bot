'use client';

import { useState } from 'react';
import {
  ClockIcon,
  MagnifyingGlassIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { useChangesData } from '../hooks/useChangesData';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import type { ChangeTicket, SuppressedTicket } from '../hooks/useChangesData';

export function Changes() {
  const {
    changes,
    loading,
    error,
    selectedChange,
    setSelectedChange,
    suppressedTickets,
    loadingSuppressed,
    fetchChanges,
    unsuppressTickets,
  } = useChangesData();

  const [searchQuery, setSearchQuery] = useState('');
  const [unsuppressing, setUnsuppressing] = useState<number | null>(null);

  // Filter changes by search query
  const filteredChanges = changes.filter((change) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      change.title.toLowerCase().includes(query) ||
      change.external_id.toLowerCase().includes(query) ||
      change.source.toLowerCase().includes(query) ||
      change.description?.toLowerCase().includes(query)
    );
  });

  const handleUnsuppress = async (changeTicketId: number) => {
    if (!confirm('Are you sure you want to unsuppress all tickets for this change window?')) {
      return;
    }

    try {
      setUnsuppressing(changeTicketId);
      await unsuppressTickets(changeTicketId);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to unsuppress tickets');
    } finally {
      setUnsuppressing(null);
    }
  };

  const getStatusColor = (status: string): 'success' | 'warning' | 'primary' | 'error' => {
    switch (status) {
      case 'scheduled':
        return 'primary';
      case 'in_progress':
        return 'warning';
      case 'completed':
        return 'success';
      case 'cancelled':
        return 'error';
      default:
        return 'primary';
    }
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const isActive = (change: ChangeTicket) => {
    const now = new Date();
    const start = new Date(change.start_time);
    const end = new Date(change.end_time);
    return now >= start && now <= end && change.status === 'in_progress';
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
          <span className="ml-3 text-neutral-600 font-medium">Loading changes...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Card variant="outlined" className="border-error-200 bg-error-50">
          <CardContent padding="md">
            <div className="flex items-center gap-3">
              <ExclamationTriangleIcon className="h-5 w-5 text-error-600" />
              <p className="text-error-800">{error}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-neutral-500 font-bold mb-1">Change Management</p>
          <h2 className="text-3xl font-bold text-neutral-900 mb-1">Active Changes</h2>
          <p className="text-sm text-neutral-600">
            Monitor scheduled and in-progress change windows
          </p>
        </div>
        <Button
          variant="outline"
          onClick={fetchChanges}
          className="flex items-center gap-2"
        >
          <ArrowPathIcon className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Search */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <MagnifyingGlassIcon className="h-5 w-5 text-neutral-400" />
        </div>
        <input
          type="text"
          placeholder="Search changes by title, ID, source..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="block w-full pl-10 pr-3 py-2.5 border border-neutral-300 rounded-lg placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 bg-white"
        />
      </div>

      {filteredChanges.length === 0 ? (
        <Card variant="outlined">
          <CardContent padding="lg">
            <div className="text-center py-12">
              <ClockIcon className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
              <p className="text-neutral-600 font-medium">
                {searchQuery ? 'No changes match your search' : 'No active changes'}
              </p>
              <p className="text-sm text-neutral-500 mt-2">
                {searchQuery
                  ? 'Try adjusting your search criteria'
                  : 'Change windows will appear here when scheduled or in progress'}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredChanges.map((change) => {
            const isExpanded = selectedChange === change.id;
            const currentlyActive = isActive(change);
            
            return (
              <Card key={change.id} variant="outlined" className="hover:shadow-lg transition-shadow">
                <CardContent padding="lg">
                  <div className="space-y-4">
                    {/* Header */}
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-lg font-bold text-neutral-900">{change.title}</h3>
                          <Badge variant={getStatusColor(change.status)}>
                            {change.status.replace('_', ' ').toUpperCase()}
                          </Badge>
                          {currentlyActive && (
                            <Badge variant="warning">ACTIVE NOW</Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-4 text-sm text-neutral-600">
                          <span className="font-medium">{change.external_id}</span>
                          <span className="text-neutral-400">•</span>
                          <span className="capitalize">{change.source}</span>
                          {change.change_type && (
                            <>
                              <span className="text-neutral-400">•</span>
                              <span className="capitalize">{change.change_type}</span>
                            </>
                          )}
                        </div>
                        {change.description && (
                          <p className="text-sm text-neutral-600 mt-2 line-clamp-2">{change.description}</p>
                        )}
                      </div>
                    </div>

                    {/* Time Information */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3 border-t border-neutral-200">
                      <div>
                        <p className="text-xs text-neutral-500 font-semibold mb-1 uppercase tracking-wide">Start Time</p>
                        <p className="text-sm text-neutral-900 font-medium">{formatDateTime(change.start_time)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-neutral-500 font-semibold mb-1 uppercase tracking-wide">End Time</p>
                        <p className="text-sm text-neutral-900 font-medium">{formatDateTime(change.end_time)}</p>
                      </div>
                    </div>

                    {/* Affected Services/Environments */}
                    {(change.affected_services && change.affected_services.length > 0) ||
                    (change.affected_environments && change.affected_environments.length > 0) ? (
                      <div className="pt-3 border-t border-neutral-200 space-y-3">
                        {change.affected_services && change.affected_services.length > 0 && (
                          <div>
                            <p className="text-xs text-neutral-500 font-semibold mb-2 uppercase tracking-wide">Affected Services</p>
                            <div className="flex flex-wrap gap-2">
                              {change.affected_services.map((service, idx) => (
                                <Badge key={idx} variant="secondary">{service}</Badge>
                              ))}
                            </div>
                          </div>
                        )}
                        {change.affected_environments && change.affected_environments.length > 0 && (
                          <div>
                            <p className="text-xs text-neutral-500 font-semibold mb-2 uppercase tracking-wide">Environments</p>
                            <div className="flex flex-wrap gap-2">
                              {change.affected_environments.map((env, idx) => (
                                <Badge key={idx} variant="secondary">{env}</Badge>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : null}

                    {/* Expand/Collapse and Suppressed Tickets */}
                    <div className="pt-3 border-t border-neutral-200">
                      <div className="flex items-center justify-between">
                        <button
                          onClick={() => setSelectedChange(isExpanded ? null : change.id)}
                          className="flex items-center gap-2 text-sm font-medium text-primary-600 hover:text-primary-700"
                        >
                          {isExpanded ? (
                            <>
                              <ChevronUpIcon className="h-4 w-4" />
                              Hide Suppressed Tickets
                            </>
                          ) : (
                            <>
                              <ChevronDownIcon className="h-4 w-4" />
                              Show Suppressed Tickets
                            </>
                          )}
                        </button>
                        {change.suppression_enabled && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleUnsuppress(change.id)}
                            disabled={unsuppressing === change.id}
                            className="text-sm"
                          >
                            {unsuppressing === change.id ? 'Unsuppressing...' : 'Unsuppress All Tickets'}
                          </Button>
                        )}
                      </div>

                      {isExpanded && (
                        <div className="mt-4 pt-4 border-t border-neutral-200">
                          {loadingSuppressed ? (
                            <div className="flex items-center justify-center py-4">
                              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
                              <span className="ml-2 text-sm text-neutral-600">Loading suppressed tickets...</span>
                            </div>
                          ) : suppressedTickets.length > 0 ? (
                            <div className="space-y-2">
                              <p className="text-sm font-semibold text-neutral-900 mb-3">
                                Suppressed Tickets ({suppressedTickets.length})
                              </p>
                              <div className="space-y-2 max-h-96 overflow-y-auto">
                                {suppressedTickets.map((ticket) => (
                                  <Card key={ticket.id} variant="outlined" className="bg-neutral-50">
                                    <CardContent padding="sm">
                                      <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                          <div className="flex items-center gap-2 mb-1">
                                            <p className="text-sm font-medium text-neutral-900">{ticket.title}</p>
                                            <Badge variant="warning">Suppressed</Badge>
                                          </div>
                                          <div className="flex items-center gap-3 text-xs text-neutral-600">
                                            <span className="capitalize">{ticket.severity}</span>
                                            <span className="text-neutral-400">•</span>
                                            <span className="uppercase">{ticket.environment}</span>
                                            {ticket.service && (
                                              <>
                                                <span className="text-neutral-400">•</span>
                                                <span>{ticket.service}</span>
                                              </>
                                            )}
                                          </div>
                                          {ticket.suppression_reason && (
                                            <p className="text-xs text-neutral-500 mt-1 italic">
                                              {ticket.suppression_reason}
                                            </p>
                                          )}
                                          <p className="text-xs text-neutral-500 mt-1">
                                            Suppressed at {formatDateTime(ticket.suppressed_at)}
                                          </p>
                                        </div>
                                      </div>
                                    </CardContent>
                                  </Card>
                                ))}
                              </div>
                            </div>
                          ) : (
                            <div className="text-center py-6 text-sm text-neutral-500">
                              <CheckCircleIcon className="h-8 w-8 text-neutral-400 mx-auto mb-2" />
                              <p>No suppressed tickets for this change window</p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {filteredChanges.length > 0 && (
        <div className="text-center text-sm text-neutral-500">
          Showing {filteredChanges.length} active change window{filteredChanges.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}

