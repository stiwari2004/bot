'use client';

import { useState } from 'react';
import {
  BellIcon,
  MagnifyingGlassIcon,
  ExclamationTriangleIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline';
import { AlertDetailModal } from './AlertDetailModal';
import { useAlertsData } from '../hooks/useAlertsData';
import type { Alert } from '../types';

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
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">Loading alerts...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2 flex items-center">
          <BellIcon className="h-7 w-7 mr-2 text-orange-600" />
          Alerts
        </h2>
        <p className="text-gray-600">View alerts from monitoring tools (Prometheus, Datadog, Azure Monitor, Splunk)</p>
        <p className="text-sm text-gray-500 mt-1">
          Alerts are used for validation and matching with tickets. Tickets come from ticketing tools.
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />
            <p className="text-red-800 font-medium">Error</p>
          </div>
          <p className="text-red-700 mt-2 text-sm">{error}</p>
        </div>
      )}

      {/* Filters and Search */}
      <div className="mb-6 space-y-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search alerts..."
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <div>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
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
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
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
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Sources</option>
              <option value="prometheus">Prometheus</option>
              <option value="datadog">Datadog</option>
              <option value="azure_monitor">Azure Monitor</option>
              <option value="splunk">Splunk</option>
            </select>
          </div>
        </div>
      </div>

      {/* Alerts List */}
      {filteredAlerts.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <BellIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p>No alerts found</p>
          <p className="text-sm mt-2">
            {searchQuery || filterStatus !== 'all' || filterSeverity !== 'all' || filterSource !== 'all'
              ? 'Try adjusting your filters'
              : 'Alerts will appear here when monitoring tools send webhooks'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredAlerts.map((alert) => (
            <div
              key={alert.id}
              onClick={() => setSelectedAlert(alert.id)}
              className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2 flex-wrap">
                    <h3 className="font-medium text-gray-900">{alert.title}</h3>
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(
                        alert.status
                      )}`}
                    >
                      {alert.status}
                    </span>
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(
                        alert.severity
                      )}`}
                    >
                      {alert.severity}
                    </span>
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${getSourceColor(
                        alert.source
                      )}`}
                    >
                      {alert.source}
                    </span>
                    {alert.matched_ticket_id && (
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        Matched Ticket #{alert.matched_ticket_id}
                      </span>
                    )}
                  </div>
                  {alert.description && (
                    <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                      {alert.description}
                    </p>
                  )}
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>Received: {new Date(alert.received_at).toLocaleString()}</span>
                    {alert.starts_at && (
                      <span>Started: {new Date(alert.starts_at).toLocaleString()}</span>
                    )}
                    {alert.service && <span>Service: {alert.service}</span>}
                    {alert.environment && <span>Env: {alert.environment}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <ArrowRightIcon className="h-5 w-5 text-gray-400" />
                </div>
              </div>
            </div>
          ))}
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

