'use client';
/**
 * Base URL for browser-facing API calls.
 *
 * In Next.js (both dev and production, including Docker), we already have a rewrite:
 *   /api/:path* -> <internal backend>/api/:path*
 *
 * To avoid hard‑coding container hostnames like http://backend:8000 into the browser,
 * we default to **same-origin** relative URLs (empty base), so all client-side fetches
 * go to `/api/...` on port 3000 and are proxied to the backend by Next.
 *
 * If you explicitly set NEXT_PUBLIC_API_BASE_URL, that absolute URL will be used instead.
 */
export const API_BASE_URL =
  (process.env.NEXT_PUBLIC_API_BASE_URL && process.env.NEXT_PUBLIC_API_BASE_URL.trim() !== '')
    ? process.env.NEXT_PUBLIC_API_BASE_URL.trim()
    : '';

const createEndpoints = (baseUrl: string) => ({
  auth: {
    login: () => `${baseUrl}/api/v1/auth/login`,
    me: () => `${baseUrl}/api/v1/auth/me`,
  },
  agent: {
    pendingApprovals: () => `${baseUrl}/api/v1/agent/pending-approvals`,
    approveStep: (sessionId: number, stepNumber: number) => 
      `${baseUrl}/api/v1/agent/${sessionId}/approve-step`,
    execution: (sessionId: number) => `${baseUrl}/api/v1/agent/${sessionId}`,
    sessions: (status?: string) => {
      const query = status ? `?status=${status}` : '';
      return `${baseUrl}/api/v1/agent/sessions${query}`;
    },
    cancelSession: (sessionId: number) => `${baseUrl}/api/v1/agent/${sessionId}/cancel`,
    deleteSession: (sessionId: number) => `${baseUrl}/api/v1/agent/${sessionId}`,
    sessionSteps: (sessionId: number) => `${baseUrl}/api/v1/agent/${sessionId}/steps`,
  },
  tickets: {
    list: (params?: { limit?: number }) => {
      const query = params ? `?limit=${params.limit || 100}` : '';
      return `${baseUrl}/api/v1/tickets/demo/tickets${query}`;
    },
    detail: (ticketId: number) => `${baseUrl}/api/v1/tickets/demo/tickets/${ticketId}`,
    webhook: (source: string) => `${baseUrl}/api/v1/tickets/webhook/${source}`,
  },
  alerts: {
    list: (params?: { status?: string; source?: string; limit?: number }) => {
      const queryParams = new URLSearchParams();
      if (params?.status) queryParams.append('status', params.status);
      if (params?.source) queryParams.append('source', params.source);
      queryParams.append('limit', String(params?.limit || 100));
      return `${baseUrl}/api/v1/alerts/alerts?${queryParams.toString()}`;
    },
    detail: (alertId: number) => `${baseUrl}/api/v1/alerts/alerts/${alertId}`,
    update: (alertId: number) => `${baseUrl}/api/v1/alerts/alerts/${alertId}`,
  },
  runbooks: {
    base: () => `${baseUrl}/api/v1/runbooks`,
    generateAgent: () => `${baseUrl}/api/v1/runbooks/demo/generate-agent`,
    detectOS: (serverName: string) => `${baseUrl}/api/v1/runbooks/demo/detect-os?server_name=${encodeURIComponent(serverName)}`,
    metrics: (runbookId: number, days?: number) => {
      const query = days ? `?days=${days}` : '';
      return `${baseUrl}/api/v1/analytics/demo/runbooks/${runbookId}/metrics${query}`;
    },
    calculateMetrics: (runbookId: number, days?: number) => {
      const query = days ? `?days=${days}` : '';
      return `${baseUrl}/api/v1/analytics/demo/runbooks/${runbookId}/calculate-metrics${query}`;
    },
    versions: (runbookId: number) => `${baseUrl}/api/v1/runbooks/demo/${runbookId}/versions`,
    createVersion: (runbookId: number) => `${baseUrl}/api/v1/runbooks/demo/${runbookId}/versions`,
    versionDiff: (runbookId: number, versionId1: number, versionId2: number) =>
      `${baseUrl}/api/v1/runbooks/demo/${runbookId}/versions/${versionId1}/diff/${versionId2}`,
    setCurrentVersion: (versionId: number) => `${baseUrl}/api/v1/runbooks/demo/versions/${versionId}/set-current`,
    verifyCitations: (runbookId: number) => `${baseUrl}/api/v1/runbooks/demo/${runbookId}/citations/verify`,
    citationHealth: (runbookId: number) => `${baseUrl}/api/v1/runbooks/demo/${runbookId}/citations/health`,
  },
  analytics: {
    runbookQuality: (days?: number) => {
      const query = days ? `?days=${days}` : '';
      return `${baseUrl}/api/v1/analytics/demo/runbook-quality${query}`;
    },
    decisionEngine: (days?: number) => {
      const query = days ? `?days=${days}` : '';
      return `${baseUrl}/api/v1/analytics/demo/decision-engine${query}`;
    },
    decisionEngineTrends: (periodType?: string) => {
      const query = periodType ? `?period_type=${periodType}` : '';
      return `${baseUrl}/api/v1/analytics/demo/decision-engine/trends${query}`;
    },
  },
  resolution: {
    createFlow: (ticketId: number) => `${baseUrl}/api/v1/resolution/demo/tickets/${ticketId}/create-flow`,
    autoResolve: (ticketId: number) => `${baseUrl}/api/v1/resolution/demo/tickets/${ticketId}/auto-resolve`,
    flowStatus: (flowId: number) => `${baseUrl}/api/v1/resolution/demo/flows/${flowId}`,
    advancePhase: (flowId: number) => `${baseUrl}/api/v1/resolution/demo/flows/${flowId}/advance`,
    completeFlow: (flowId: number) => `${baseUrl}/api/v1/resolution/demo/flows/${flowId}/complete`,
  },
  executions: {
    createSession: () => `${baseUrl}/api/v1/agent/execute`,
  },
  settings: {
    executionMode: () => `${baseUrl}/api/v1/settings/execution-mode/demo`,
    ticketingConnections: () => `${baseUrl}/api/v1/settings/ticketing-connections`,
    ticketingTools: () => `${baseUrl}/api/v1/settings/ticketing-tools`,
    ticketingConnection: (connectionId: number) => 
      `${baseUrl}/api/v1/settings/ticketing-connections/${connectionId}`,
    ticketingConnectionTest: (connectionId: number) => 
      `${baseUrl}/api/v1/settings/ticketing-connections/${connectionId}/test`,
    ticketingConnectionDelete: (connectionId: number) => 
      `${baseUrl}/api/v1/settings/ticketing-connections/${connectionId}`,
  },
  connectors: {
    credentials: () => `${baseUrl}/api/v1/connectors/credentials`,
    infrastructureConnections: () => `${baseUrl}/api/v1/connectors/infrastructure-connections`,
    infrastructureConnection: (connectionId: number) => 
      `${baseUrl}/api/v1/connectors/infrastructure-connections/${connectionId}`,
    infrastructureConnectionTest: (connectionId: number) => 
      `${baseUrl}/api/v1/connectors/infrastructure-connections/${connectionId}/test`,
    infrastructureConnectionDiscover: (connectionId: number) => 
      `${baseUrl}/api/v1/connectors/infrastructure-connections/${connectionId}/discover`,
    infrastructureConnectionTestCommand: (connectionId: number) => 
      `${baseUrl}/api/v1/connectors/infrastructure-connections/${connectionId}/test-command`,
    infrastructureConnectionsImport: () => `${baseUrl}/api/v1/connectors/infrastructure-connections/import-excel`,
    monitoringConnectors: () => `${baseUrl}/api/v1/connectors/monitoring`,
    monitoringConnections: () => `${baseUrl}/api/v1/connectors/monitoring-connections`,
    monitoringConnection: (connectionId: number) =>
      `${baseUrl}/api/v1/connectors/monitoring-connections/${connectionId}`,
  },
  system: {
    health: () => `${baseUrl}/api/v1/test/health-detailed`,
    healthDetailed: () => `${baseUrl}/api/v1/test/health-detailed`,
    testUi: () => `${baseUrl}/docs`,
    docs: () => `${baseUrl}/docs`,
  },
  network: {
    clusters: () => `${baseUrl}/api/v1/network/clusters`,
    clusterDevices: (clusterId: string) => `${baseUrl}/api/v1/network/clusters/${clusterId}/devices`,
  },
  superAdmin: {
    auth: {
      login: () => `${baseUrl}/api/v1/super-admin/auth/login`,
      me: () => `${baseUrl}/api/v1/super-admin/auth/me`,
    },
    overview: () => `${baseUrl}/api/v1/super-admin/overview`,
    tenants: () => `${baseUrl}/api/v1/super-admin/tenants`,
    tenant: (tenantId: number) => `${baseUrl}/api/v1/super-admin/tenants/${tenantId}`,
    createTenant: () => `${baseUrl}/api/v1/super-admin/tenants`,
    updateTenant: (tenantId: number) => `${baseUrl}/api/v1/super-admin/tenants/${tenantId}`,
    deleteTenant: (tenantId: number) => `${baseUrl}/api/v1/super-admin/tenants/${tenantId}`,
    tenantUsers: (tenantId: number) => `${baseUrl}/api/v1/super-admin/tenants/${tenantId}/users`,
    createTenantUser: (tenantId: number) => `${baseUrl}/api/v1/super-admin/tenants/${tenantId}/users`,
    updateTenantUser: (tenantId: number, userId: number) => `${baseUrl}/api/v1/super-admin/tenants/${tenantId}/users/${userId}`,
    deleteTenantUser: (tenantId: number, userId: number) => `${baseUrl}/api/v1/super-admin/tenants/${tenantId}/users/${userId}`,
  },
  decision: {
    recommendation: (ticketId: number) => `${baseUrl}/api/v1/decision/demo/tickets/${ticketId}/recommendation`,
    patterns: (ticketId: number) => `${baseUrl}/api/v1/decision/demo/tickets/${ticketId}/patterns`,
    context: (ticketId: number, timeWindowHours?: number) => {
      const query = timeWindowHours ? `?time_window_hours=${timeWindowHours}` : '';
      return `${baseUrl}/api/v1/decision/demo/tickets/${ticketId}/context${query}`;
    },
    patternFeedback: (patternId: number) => `${baseUrl}/api/v1/decision/demo/patterns/${patternId}/feedback`,
    recommendationFeedback: () => `${baseUrl}/api/v1/decision/demo/recommendations/feedback`,
    ticketFeedback: (ticketId: number) => `${baseUrl}/api/v1/decision/demo/tickets/${ticketId}/feedback`,
    deprecatePattern: (patternId: number) => `${baseUrl}/api/v1/decision/demo/patterns/${patternId}/deprecate`,
    restorePattern: (patternId: number) => `${baseUrl}/api/v1/decision/demo/patterns/${patternId}/restore`,
    qualityReport: (minScore?: number, includeDeprecated?: boolean) => {
      const params = new URLSearchParams();
      if (minScore !== undefined) params.append('min_quality_score', minScore.toString());
      if (includeDeprecated) params.append('include_deprecated', 'true');
      const query = params.toString() ? `?${params.toString()}` : '';
      return `${baseUrl}/api/v1/decision/demo/patterns/quality-report${query}`;
    },
    updateQualityScore: (patternId: number) => `${baseUrl}/api/v1/decision/demo/patterns/${patternId}/update-quality-score`,
    prunePatterns: (maxScore?: number, minAge?: number) => {
      const params = new URLSearchParams();
      if (maxScore !== undefined) params.append('max_quality_score', maxScore.toString());
      if (minAge !== undefined) params.append('min_age_days', minAge.toString());
      const query = params.toString() ? `?${params.toString()}` : '';
      return `${baseUrl}/api/v1/decision/demo/patterns/prune${query}`;
    },
    runbookConfidence: (runbookId: number) => `${baseUrl}/api/v1/decision/demo/runbooks/${runbookId}/confidence`,
    recommendationConfidence: (recommendationId: number) => `${baseUrl}/api/v1/decision/demo/recommendations/${recommendationId}/confidence`,
  },
  tenantAdmin: {
    dashboard: () => `${baseUrl}/api/v1/tenant-admin/dashboard`,
    customers: () => `${baseUrl}/api/v1/tenant-admin/customers`,
    customer: (customerId: number) => `${baseUrl}/api/v1/tenant-admin/customers/${customerId}`,
    customerUsers: (customerId: number) => `${baseUrl}/api/v1/tenant-admin/customers/${customerId}/users`,
    customerUser: (customerId: number, userId: number) => `${baseUrl}/api/v1/tenant-admin/customers/${customerId}/users/${userId}`,
    customerSubscription: (customerId: number) => `${baseUrl}/api/v1/tenant-admin/customers/${customerId}/subscription`,
  },
  clientAdmin: {
    dashboard: () => `${baseUrl}/api/v1/client-admin/dashboard`,
    users: () => `${baseUrl}/api/v1/client-admin/users`,
    user: (userId: number) => `${baseUrl}/api/v1/client-admin/users/${userId}`,
    billing: () => `${baseUrl}/api/v1/client-admin/billing`,
    nodes: () => `${baseUrl}/api/v1/client-admin/nodes`,
    activateNode: (nodeId: number) => `${baseUrl}/api/v1/client-admin/nodes/${nodeId}/activate`,
    deactivateNode: (nodeId: number) => `${baseUrl}/api/v1/client-admin/nodes/${nodeId}/deactivate`,
  },
});

export const apiConfig = {
  baseUrl: API_BASE_URL,
  baseURL: API_BASE_URL, // Support both for compatibility
  apiURL: `${API_BASE_URL}/api/v1`,
  endpoints: createEndpoints(API_BASE_URL),
  buildUrl: (path: string) => {
    // Remove leading slash if present, then add baseUrl
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return `${API_BASE_URL}${cleanPath}`;
  },
};

export default apiConfig;
