'use client';

import { useState, useEffect } from 'react';
import { 
  TicketIcon,
  PlayIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline';
import { superAdminFetch } from '@/lib/super-admin-fetch';
import { apiConfig } from '@/lib/api-config';

interface ActivityEvent {
  type: string;
  timestamp: string;
  ticket_id?: number;
  execution_id?: number;
  runbook_id?: number;
  runbook_title?: string;
  pattern_id?: number;
  pattern_confidence?: number;
  step_number?: number;
  duration_minutes?: number;
  description: string;
}

interface ActivityFeedWidgetProps {
  token: string | null;
  limit?: number;
}

export function ActivityFeedWidget({ token, limit = 20 }: ActivityFeedWidgetProps) {
  const [activities, setActivities] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;

    const fetchActivities = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await superAdminFetch(
          `${apiConfig.endpoints.superAdmin.activityFeed()}?limit=${limit}`,
          token
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch activity feed: ${response.status}`);
        }

        const data = await response.json();
        setActivities(data.activities || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load activity feed');
      } finally {
        setLoading(false);
      }
    };

    fetchActivities();
    // Refresh every 30 seconds
    const interval = setInterval(fetchActivities, 30 * 1000);
    return () => clearInterval(interval);
  }, [token, limit]);

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'ticket_created':
        return <TicketIcon className="h-4 w-4 text-primary-600" />;
      case 'pattern_selected':
      case 'approval_requested':
        return <PlayIcon className="h-4 w-4 text-secondary-600" />;
      case 'execution_completed':
        return <CheckCircleIcon className="h-4 w-4 text-success-600" />;
      case 'execution_failed':
        return <XCircleIcon className="h-4 w-4 text-red-600" />;
      default:
        return <ClockIcon className="h-4 w-4 text-neutral-400" />;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
        <div className="animate-pulse">
          <div className="h-4 bg-neutral-200 rounded w-1/3 mb-4"></div>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 bg-neutral-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl border border-red-200 p-6 shadow-sm">
        <p className="text-sm text-red-600">Failed to load activity feed</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-neutral-900 mb-4">Live Activity Feed</h2>
      
      {activities.length === 0 ? (
        <p className="text-sm text-neutral-500 text-center py-8">No recent activity</p>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {activities.map((activity, idx) => (
            <div key={idx} className="flex items-start gap-3 p-3 bg-neutral-50 rounded-lg">
              <div className="mt-0.5">
                {getActivityIcon(activity.type)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-neutral-900">
                  {activity.description}
                </p>
                <div className="flex items-center gap-2 mt-1 text-xs text-neutral-500">
                  <span>{formatTimestamp(activity.timestamp)}</span>
                  {activity.ticket_id && (
                    <>
                      <span>•</span>
                      <span>Ticket #{activity.ticket_id}</span>
                    </>
                  )}
                  {activity.runbook_title && (
                    <>
                      <span>•</span>
                      <span className="truncate">{activity.runbook_title}</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
