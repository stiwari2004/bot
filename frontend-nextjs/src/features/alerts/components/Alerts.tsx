'use client';

import { useState, useEffect, useRef } from 'react';
import {
  BellIcon,
  MagnifyingGlassIcon,
  ExclamationTriangleIcon,
  ArrowRightIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';
import { AlertDetailModal } from './AlertDetailModal';
import { useAlertsData } from '../hooks/useAlertsData';
import type { Alert } from '../types';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

export function Alerts() {
  const {
    alerts,
    loading,
    error,
    selectedAlert,
    setSelectedAlert,
    alertDetail,
    loadingDetail,
    filterStatus,
    setFilterStatus,
    filterSeverity,
    setFilterSeverity,
    filterSource,
    setFilterSource,
    searchQuery,
    setSearchQuery,
    fetchAlerts,
    updateAlert,
    getStatusColor,
    getSeverityColor,
    getSourceColor,
    filteredAlerts,
  } = useAlertsData();

  const [newAlertId, setNewAlertId] = useState<number | null>(null);
  const [showNewAlertToast, setShowNewAlertToast] = useState(false);
  const hasInitializedRef = useRef(false);

  // Detect new alerts from polling results and show a toast when a new one arrives.
  useEffect(() => {
    if (!filteredAlerts || filteredAlerts.length === 0) {
      return;
    }
    const latest = filteredAlerts[0];
    if (!latest) {
      return;
    }

    if (!hasInitializedRef.current) {
      hasInitializedRef.current = true;
      setNewAlertId(latest.id);
      return;
    }

    if (newAlertId !== null && latest.id === newAlertId) {
      return;
    }

    setNewAlertId(latest.id);
    setShowNewAlertToast(true);
  }, [filteredAlerts, newAlertId]);

  const handleUpdateAlert = async (alertId: number, status: string, notes?: string) => {
    try {
      await updateAlert(alertId, status, notes);
      // Refresh alerts list after update
      await fetchAlerts();
    } catch (err) {
      console.error('Error updating alert:', err);
      throw err;
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
          <span className="ml-3 text-neutral-600 font-medium">Loading alerts...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 relative">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-xl bg-gradient-to-br from-warning-100 to-warning-200">
            <BellIcon className="h-6 w-6 text-warning-600" />
          </div>
          <div>
            <h2 className="text-3xl font-bold text-neutral-900">Alerts</h2>
            <p className="text-sm text-neutral-600 mt-0.5">View alerts from monitoring tools (Prometheus, Datadog, Azure Monitor, Splunk)</p>
            <p className="text-xs text-neutral-500 mt-1">
              Alerts are used for validation and matching with tickets. Tickets come from ticketing tools.
            </p>
          </div>
        </div>
      </div>

      {error && (
        <Card variant="outlined" className="border-error-200 bg-error-50">
          <CardContent padding="md">
            <div className="flex items-center gap-3">
              <ExclamationTriangleIcon className="h-5 w-5 text-error-600 flex-shrink-0" />
              <div>
                <p className="text-error-800 font-semibold">Error</p>
                <p className="text-error-700 text-sm mt-1">{error}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters and Search */}
      <Card>
        <CardContent padding="md">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[250px]">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <MagnifyingGlassIcon className="h-5 w-5 text-neutral-400" />
                </div>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search alerts by title, description, or source..."
                  className="block w-full pl-10 pr-4 py-2.5 border border-neutral-300 rounded-lg leading-5 bg-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all text-neutral-900"
                />
              </div>
            </div>
            <div>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="px-4 py-2.5 border border-neutral-300 rounded-lg bg-white text-neutral-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all font-medium"
              >
                <option value="all">All Statuses</option>
                <option value="firing">Firing</option>
                <option value="resolved">Resolved</option>
                <option value="acknowledged">Acknowledged</option>
              </select>
            </div>
            <div>
              <select
                value={filterSeverity}
                onChange={(e) => setFilterSeverity(e.target.value)}
                className="px-4 py-2.5 border border-neutral-300 rounded-lg bg-white text-neutral-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all font-medium"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div>
              <select
                value={filterSource}
                onChange={(e) => setFilterSource(e.target.value)}
                className="px-4 py-2.5 border border-neutral-300 rounded-lg bg-white text-neutral-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all font-medium"
              >
                <option value="all">All Sources</option>
                <option value="prometheus">Prometheus</option>
                <option value="datadog">Datadog</option>
                <option value="azure_monitor">Azure Monitor</option>
                <option value="splunk">Splunk</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Alerts List */}
      {filteredAlerts.length === 0 ? (
        <Card>
          <CardContent padding="lg">
            <div className="text-center py-12">
              <div className="mx-auto w-16 h-16 rounded-full bg-neutral-100 flex items-center justify-center mb-4">
                <BellIcon className="h-8 w-8 text-neutral-400" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-900 mb-1">No alerts found</h3>
              <p className="text-sm text-neutral-600">
                {searchQuery || filterStatus !== 'all' || filterSeverity !== 'all' || filterSource !== 'all'
                  ? 'Try adjusting your filters to see more results'
                  : 'Alerts will appear here when monitoring tools send webhooks'}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {filteredAlerts.map((alert) => (
            <Card
              key={alert.id}
              hover
              onClick={() => setSelectedAlert(alert.id)}
              variant="elevated"
            >
              <CardContent padding="md">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-3 mb-3">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-semibold text-neutral-900 mb-2 line-clamp-1">
                          {alert.title}
                        </h3>
                        <div className="flex flex-wrap items-center gap-2 mb-3">
                          <Badge variant="status" status={alert.status as any} size="sm">
                            {alert.status}
                          </Badge>
                          <Badge variant="severity" severity={alert.severity as any} size="sm">
                            {alert.severity}
                          </Badge>
                          <Badge variant="secondary" size="sm">
                            {alert.source}
                          </Badge>
                          {alert.matched_ticket_id && (
                            <Badge variant="primary" size="sm">
                              Matched Ticket #{alert.matched_ticket_id}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                    {alert.description && (
                      <p className="text-sm text-neutral-600 mb-3 line-clamp-2">
                        {alert.description}
                      </p>
                    )}
                    <div className="flex flex-wrap items-center gap-4 text-xs text-neutral-500">
                      <span className="flex items-center gap-1">
                        <span className="font-medium">Received:</span>
                        {new Date(alert.received_at).toLocaleString()}
                      </span>
                      {alert.starts_at && (
                        <span className="flex items-center gap-1">
                          <span className="font-medium">Started:</span>
                          {new Date(alert.starts_at).toLocaleString()}
                        </span>
                      )}
                      {alert.service && (
                        <span className="flex items-center gap-1">
                          <span className="font-medium">Service:</span>
                          {alert.service}
                        </span>
                      )}
                      {alert.environment && (
                        <span className="flex items-center gap-1">
                          <span className="font-medium">Env:</span>
                          {alert.environment}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex-shrink-0">
                    <div className="p-2 rounded-lg bg-warning-50 text-warning-600">
                      <ArrowRightIcon className="h-5 w-5" />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* New Alert Toast */}
      {showNewAlertToast && newAlertId && (
        <div className="fixed bottom-6 right-6 z-50">
          <div className="max-w-sm bg-white shadow-lg rounded-lg border border-warning-200 p-4 flex items-start gap-3">
            <div className="mt-0.5">
              <InformationCircleIcon className="h-5 w-5 text-warning-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-neutral-900">New alert received</p>
              <p className="text-xs text-neutral-600 mt-1 line-clamp-2">
                {filteredAlerts.find((a: Alert) => a.id === newAlertId)?.title || 'A new alert has been received.'}
              </p>
              <div className="mt-3 flex items-center gap-2">
                <Button
                  variant="primary"
                  size="xs"
                  onClick={() => {
                    setSelectedAlert(newAlertId);
                    setShowNewAlertToast(false);
                  }}
                >
                  View alert
                </Button>
                <Button
                  variant="ghost"
                  size="xs"
                  onClick={() => setShowNewAlertToast(false)}
                >
                  Dismiss
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Alert Detail Modal */}
      {selectedAlert && (
        <AlertDetailModal
          alert={alertDetail}
          loading={loadingDetail}
          onClose={() => setSelectedAlert(null)}
          onUpdate={handleUpdateAlert}
        />
      )}
    </div>
  );
}

