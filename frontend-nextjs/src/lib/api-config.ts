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
    changePassword: () => `${baseUrl}/api/v1/auth/change-password`,
    forgotPassword: () => `${baseUrl}/api/v1/auth/forgot-password`,
    resetPassword: () => `${baseUrl}/api/v1/auth/reset-password`,
    verifyEmail: () => `${baseUrl}/api/v1/auth/verify-email`,
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
    webhook: (source: string) => `${baseUrl}/api/v1/tickets/webhook/${source}`,
  },
  runbooks: {
    base: () => `${baseUrl}/api/v1/runbooks`,
    // Authenticated, multi-tenant generate endpoint
    generateAgent: () => `${baseUrl}/api/v1/runbooks/generate-agent`,
    // Demo-only endpoints (used by legacy/demo flows)
    generateAgentDemo: () => `${baseUrl}/api/v1/runbooks/demo/generate-agent`,
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
    reviewStatus: (runbookId: number) => `${baseUrl}/api/v1/runbooks/demo/${runbookId}/review-status`,
    stepApprove: (runbookId: number) => `${baseUrl}/api/v1/runbooks/demo/${runbookId}/steps/approve`,
    stepUpdateCommand: (runbookId: number) => `${baseUrl}/api/v1/runbooks/demo/${runbookId}/steps/command`,
    stepRegenerate: (runbookId: number) => `${baseUrl}/api/v1/runbooks/demo/${runbookId}/steps/regenerate`,
  },
  provisioning: {
    list: () => `${baseUrl}/api/v1/provisioning/projects`,
    provision: () => `${baseUrl}/api/v1/provisioning/provision`,
    project: (id: number) => `${baseUrl}/api/v1/provisioning/projects/${id}`,
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
    // Agent session endpoints (solve-first, crystallise-after)
    agentSessions: () => `${baseUrl}/api/v1/executions/demo/agent-sessions`,
    agentSessionEvents: (sessionId: number) => `${baseUrl}/api/v1/executions/demo/sessions/${sessionId}/events`,
    agentSessionStepReview: (sessionId: number) => `${baseUrl}/api/v1/executions/demo/agent-sessions/${sessionId}/step-review`,
    agentSessionReview: (sessionId: number) => `${baseUrl}/api/v1/executions/demo/agent-sessions/${sessionId}/review`,
    agentSessionDetail: (sessionId: number) => `${baseUrl}/api/v1/executions/demo/sessions/${sessionId}`,
    agentSessionPlan: (sessionId: number) => `${baseUrl}/api/v1/executions/demo/agent-sessions/${sessionId}/plan`,
    agentSessionSetExclusions: (sessionId: number) => `${baseUrl}/api/v1/executions/demo/agent-sessions/${sessionId}/set-exclusions`,
    agentSessionEscalate: (sessionId: number) => `${baseUrl}/api/v1/executions/demo/agent-sessions/${sessionId}/escalate`,
    agentSessionRetry: (sessionId: number) => `${baseUrl}/api/v1/executions/demo/agent-sessions/${sessionId}/retry`,
    agentSessionFeedback: (sessionId: number) => `${baseUrl}/api/v1/executions/demo/agent-sessions/${sessionId}/feedback`,
    agentSessionConfirmResolution: (sessionId: number) => `${baseUrl}/api/v1/executions/demo/agent-sessions/${sessionId}/confirm-resolution`,
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
    monitoringConnections: () => `${baseUrl}/api/v1/connectors/monitoring-connections`,
    monitoringConnection: (connectionId: number) =>
      `${baseUrl}/api/v1/connectors/monitoring-connections/${connectionId}`,
    testMonitoringConnection: (connectionId: number) =>
      `${baseUrl}/api/v1/connectors/monitoring-connections/${connectionId}/test`,
    deleteMonitoringConnection: (connectionId: number) =>
      `${baseUrl}/api/v1/connectors/monitoring-connections/${connectionId}`,
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
    testMonitoringConnection: (connectionId: number) =>
      `${baseUrl}/api/v1/connectors/monitoring-connections/${connectionId}/test`,
    deleteMonitoringConnection: (connectionId: number) =>
      `${baseUrl}/api/v1/connectors/monitoring-connections/${connectionId}`,
  },
  discovery: {
    run: () => `${baseUrl}/api/v1/discovery/run`,
    runs: (params?: { limit?: number; status?: string }) => {
      const q = new URLSearchParams();
      if (params?.limit) q.append('limit', String(params.limit));
      if (params?.status) q.append('status', params.status);
      const query = q.toString() ? `?${q.toString()}` : '';
      return `${baseUrl}/api/v1/discovery/runs${query}`;
    },
    current: () => `${baseUrl}/api/v1/discovery/current`,
    assets: (params?: { run_id?: number; source?: string }) => {
      const q = new URLSearchParams();
      if (params?.run_id != null) q.append('run_id', String(params.run_id));
      if (params?.source) q.append('source', params.source);
      const query = q.toString() ? `?${q.toString()}` : '';
      return `${baseUrl}/api/v1/discovery/assets${query}`;
    },
    adopt: () => `${baseUrl}/api/v1/discovery/adopt`,
    ingest: () => `${baseUrl}/api/v1/discovery/ingest`,
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
    licensePlans: () => `${baseUrl}/api/v1/license-plans`,
    licensePlan: (planId: number) => `${baseUrl}/api/v1/license-plans/${planId}`,
    initializeLicensePlans: () => `${baseUrl}/api/v1/license-plans/initialize`,
    licensePlanFeatures: () => `${baseUrl}/api/v1/license-plans/features/list`,
    auth: {
      login: () => `${baseUrl}/api/v1/super-admin/auth/login`,
      me: () => `${baseUrl}/api/v1/super-admin/auth/me`,
    },
    overview: () => `${baseUrl}/api/v1/super-admin/overview`,
    activityFeed: () => `${baseUrl}/api/v1/super-admin/activity-feed`,
    connectorHealth: () => `${baseUrl}/api/v1/super-admin/connector-health`,
    dashboard: {
      overview: () => `${baseUrl}/api/v1/super-admin/dashboard/overview`,
      tenants: () => `${baseUrl}/api/v1/super-admin/dashboard/tenants`,
      revenue: () => `${baseUrl}/api/v1/super-admin/dashboard/revenue`,
      trials: () => `${baseUrl}/api/v1/super-admin/dashboard/trials`,
      exportTenants: (format: 'csv' | 'pdf' = 'csv') => `${baseUrl}/api/v1/super-admin/dashboard/export/tenants?format=${format}`,
      exportRevenue: (format: 'csv' | 'pdf' = 'csv') => `${baseUrl}/api/v1/super-admin/dashboard/export/revenue?format=${format}`,
      exportOverview: (format: 'csv' | 'pdf' = 'csv') => `${baseUrl}/api/v1/super-admin/dashboard/export/overview?format=${format}`,
      preferences: () => `${baseUrl}/api/v1/super-admin/dashboard/preferences`,
      websocket: () => {
        // Return relative path - will be converted to full URL in the hook
        return '/api/v1/super-admin/dashboard/ws';
      },
    },
    reporting: {
      generateCustom: () => `${baseUrl}/api/v1/super-admin/reports/generate`,
      scheduledReports: () => `${baseUrl}/api/v1/super-admin/reports/scheduled`,
      scheduledReport: (reportId: number) => `${baseUrl}/api/v1/super-admin/reports/scheduled/${reportId}`,
      createScheduled: () => `${baseUrl}/api/v1/super-admin/reports/scheduled`,
      updateScheduled: (reportId: number) => `${baseUrl}/api/v1/super-admin/reports/scheduled/${reportId}`,
      deleteScheduled: (reportId: number) => `${baseUrl}/api/v1/super-admin/reports/scheduled/${reportId}`,
      executeScheduled: (reportId: number) => `${baseUrl}/api/v1/super-admin/reports/scheduled/${reportId}/execute`,
    },
    inquiries: () => `${baseUrl}/api/v1/super-admin/inquiries`,
    inquiry: (inquiryId: number) => `${baseUrl}/api/v1/super-admin/inquiries/${inquiryId}`,
    updateInquiryStatus: (inquiryId: number) => `${baseUrl}/api/v1/super-admin/inquiries/${inquiryId}`,
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
  permissions: {
    list: () => `${baseUrl}/api/v1/permissions`,
    get: (id: number) => `${baseUrl}/api/v1/permissions/${id}`,
    initialize: () => `${baseUrl}/api/v1/permissions/initialize`,
  },
  roles: {
    list: () => `${baseUrl}/api/v1/roles`,
    get: (id: number) => `${baseUrl}/api/v1/roles/${id}`,
    create: () => `${baseUrl}/api/v1/roles`,
    update: (id: number) => `${baseUrl}/api/v1/roles/${id}`,
    delete: (id: number) => `${baseUrl}/api/v1/roles/${id}`,
    getPermissions: (id: number) => `${baseUrl}/api/v1/roles/${id}/permissions`,
    initialize: () => `${baseUrl}/api/v1/roles/initialize`,
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
    runbookFeedback: (ticketId: number) => `${baseUrl}/api/v1/decision/demo/tickets/${ticketId}/runbook-feedback`,
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
    explanation: (ticketId: number, recommendationId?: number) => {
      const query = recommendationId ? `?recommendation_id=${recommendationId}` : '';
      return `${baseUrl}/api/v1/decision/demo/tickets/${ticketId}/explanation${query}`;
    },
    explain: (ticketId: number) => `${baseUrl}/api/v1/decision/demo/tickets/${ticketId}/explain`,
  },
  workspace: {
    pendingApprovals: () => `${baseUrl}/api/v1/workspace/demo/workspace/pending-approvals`,
    approve: (sessionId: number, stepId: number) => `${baseUrl}/api/v1/workspace/demo/workspace/approve/${sessionId}/${stepId}`,
    tuneParameters: (sessionId: number, stepId: number) => `${baseUrl}/api/v1/workspace/demo/workspace/tune-parameters/${sessionId}/${stepId}`,
    auditTrail: (sessionId: number) => `${baseUrl}/api/v1/workspace/demo/workspace/audit-trail/${sessionId}`,
  },
  auditLog: {
    list: (params?: { from_ts?: number; to_ts?: number; session_id?: number; event_type?: string; limit?: number }) => {
      const search = new URLSearchParams();
      if (params?.from_ts != null) search.append('from_ts', String(params.from_ts));
      if (params?.to_ts != null) search.append('to_ts', String(params.to_ts));
      if (params?.session_id != null) search.append('session_id', String(params.session_id));
      if (params?.event_type) search.append('event_type', params.event_type);
      if (params?.limit != null) search.append('limit', String(params.limit));
      const q = search.toString();
      return `${baseUrl}/api/v1/audit-log${q ? `?${q}` : ''}`;
    },
    export: (params?: { from_ts?: number; to_ts?: number; session_id?: number; event_type?: string; limit?: number }) => {
      const search = new URLSearchParams();
      if (params?.from_ts != null) search.append('from_ts', String(params.from_ts));
      if (params?.to_ts != null) search.append('to_ts', String(params.to_ts));
      if (params?.session_id != null) search.append('session_id', String(params.session_id));
      if (params?.event_type) search.append('event_type', params.event_type);
      if (params?.limit != null) search.append('limit', String(params.limit));
      const q = search.toString();
      return `${baseUrl}/api/v1/audit-log/export${q ? `?${q}` : ''}`;
    },
  },
  quarantine: {
    status: (runbookId: number, versionId?: number) => {
      const query = versionId ? `?runbook_version_id=${versionId}` : '';
      return `${baseUrl}/api/v1/quarantine/demo/quarantine/status/${runbookId}${query}`;
    },
    quarantine: (runbookId: number) => `${baseUrl}/api/v1/quarantine/demo/quarantine/quarantine/${runbookId}`,
    release: (runbookId: number) => `${baseUrl}/api/v1/quarantine/demo/quarantine/release/${runbookId}`,
    pendingReview: () => `${baseUrl}/api/v1/quarantine/demo/quarantine/pending-review`,
    failurePatterns: (runbookId: number, versionId?: number) => {
      const query = versionId ? `?runbook_version_id=${versionId}` : '';
      return `${baseUrl}/api/v1/quarantine/demo/quarantine/failure-patterns/${runbookId}${query}`;
    },
  },
  versioning: {
    createVersion: (runbookId: number) => `${baseUrl}/api/v1/versioning/demo/runbooks/${runbookId}/versions`,
    getVersions: (runbookId: number) => `${baseUrl}/api/v1/versioning/demo/runbooks/${runbookId}/versions`,
    compareVersions: (versionId1: number, versionId2: number) => `${baseUrl}/api/v1/versioning/demo/versions/${versionId1}/compare/${versionId2}`,
    rollback: (runbookId: number) => `${baseUrl}/api/v1/versioning/demo/runbooks/${runbookId}/rollback`,
    requestPromotion: (runbookId: number) => `${baseUrl}/api/v1/versioning/demo/runbooks/${runbookId}/promote`,
    approvePromotion: () => `${baseUrl}/api/v1/versioning/demo/deployment-approvals/approve`,
    rejectPromotion: () => `${baseUrl}/api/v1/versioning/demo/deployment-approvals/reject`,
    pendingApprovals: () => `${baseUrl}/api/v1/versioning/demo/deployment-approvals/pending`,
  },
  remediation: {
    effectiveness: (periodStart?: string, periodEnd?: string, periodType?: string) => {
      const params = new URLSearchParams();
      if (periodStart) params.append('period_start', periodStart);
      if (periodEnd) params.append('period_end', periodEnd);
      if (periodType) params.append('period_type', periodType);
      const query = params.toString() ? `?${params.toString()}` : '';
      return `${baseUrl}/api/v1/analytics/demo/remediation/effectiveness${query}`;
    },
    trends: (periodType?: string, periods?: number) => {
      const params = new URLSearchParams();
      if (periodType) params.append('period_type', periodType);
      if (periods) params.append('periods', periods.toString());
      const query = params.toString() ? `?${params.toString()}` : '';
      return `${baseUrl}/api/v1/analytics/demo/remediation/trends${query}`;
    },
    failingSteps: (periodStart?: string, periodEnd?: string, limit?: number) => {
      const params = new URLSearchParams();
      if (periodStart) params.append('period_start', periodStart);
      if (periodEnd) params.append('period_end', periodEnd);
      if (limit) params.append('limit', limit.toString());
      const query = params.toString() ? `?${params.toString()}` : '';
      return `${baseUrl}/api/v1/analytics/demo/remediation/failing-steps${query}`;
    },
  },
  incidents: {
    generatePackage: (ticketId: number) => `${baseUrl}/api/v1/incidents/demo/incidents/${ticketId}/generate-package`,
    getPackage: (ticketId: number) => `${baseUrl}/api/v1/incidents/demo/incidents/${ticketId}/package`,
    listPackages: () => `${baseUrl}/api/v1/incidents/demo/incidents/packages`,
  },
  tenantAdmin: {
    dashboard: {
      overview: () => `${baseUrl}/api/v1/tenant-admin/dashboard/overview`,
      exportOverview: (format: 'csv' | 'pdf' = 'csv') => `${baseUrl}/api/v1/tenant-admin/dashboard/export/overview?format=${format}`,
    },
    customers: () => `${baseUrl}/api/v1/tenant-admin/customers`,
    customer: (customerId: number) => `${baseUrl}/api/v1/tenant-admin/customers/${customerId}`,
    customerUsers: (customerId: number) => `${baseUrl}/api/v1/tenant-admin/customers/${customerId}/users`,
    customerUser: (customerId: number, userId: number) => `${baseUrl}/api/v1/tenant-admin/customers/${customerId}/users/${userId}`,
    customerSubscription: (customerId: number) => `${baseUrl}/api/v1/tenant-admin/customers/${customerId}/subscription`,
    discovery: {
      run: () => `${baseUrl}/api/v1/tenant-admin/discovery/run`,
      runs: (params?: { limit?: number; status?: string }) => {
        const q = new URLSearchParams();
        if (params?.limit) q.append('limit', String(params.limit));
        if (params?.status) q.append('status', params.status);
        const query = q.toString() ? `?${q.toString()}` : '';
        return `${baseUrl}/api/v1/tenant-admin/discovery/runs${query}`;
      },
      current: () => `${baseUrl}/api/v1/tenant-admin/discovery/current`,
      assets: (params?: { run_id?: number; source?: string }) => {
        const q = new URLSearchParams();
        if (params?.run_id != null) q.append('run_id', String(params.run_id));
        if (params?.source) q.append('source', params.source);
        const query = q.toString() ? `?${q.toString()}` : '';
        return `${baseUrl}/api/v1/tenant-admin/discovery/assets${query}`;
      },
      adopt: () => `${baseUrl}/api/v1/tenant-admin/discovery/adopt`,
      adoptBulk: () => `${baseUrl}/api/v1/tenant-admin/discovery/adopt-bulk`,
      token: () => `${baseUrl}/api/v1/tenant-admin/discovery/token`,
      tokenRotate: () => `${baseUrl}/api/v1/tenant-admin/discovery/token/rotate`,
      tokenStatus: () => `${baseUrl}/api/v1/tenant-admin/discovery/token/status`,
      ingestUrl: () => `${baseUrl}/api/v1/tenant-admin/discovery/ingest`,
    },
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
  changeTickets: {
    list: (status?: string, activeOnly?: boolean) => {
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      if (activeOnly) params.append('active_only', 'true');
      const query = params.toString() ? `?${params.toString()}` : '';
      return `${baseUrl}/api/v1/change-tickets${query}`;
    },
    get: (changeTicketId: number) => `${baseUrl}/api/v1/change-tickets/${changeTicketId}`,
    suppressedTickets: (changeTicketId?: number) => {
      const query = changeTicketId ? `?change_ticket_id=${changeTicketId}` : '';
      return `${baseUrl}/api/v1/change-tickets/suppressed-tickets${query}`;
    },
    unsuppressTickets: (changeTicketId: number) => 
      `${baseUrl}/api/v1/change-tickets/${changeTicketId}/unsuppress-tickets`,
  },
  dev: {
    runbooks: {
      list: (statusFilter?: string) => {
        const query = statusFilter ? `?status_filter=${statusFilter}` : '';
        return `${baseUrl}/api/v1/dev/runbooks${query}`;
      },
      get: (runbookId: number) => `${baseUrl}/api/v1/dev/runbooks/${runbookId}`,
      promote: (runbookId: number, dryRun?: boolean) => {
        const query = dryRun ? '?dry_run=true' : '';
        return `${baseUrl}/api/v1/dev/runbooks/${runbookId}/promote${query}`;
      },
      pendingPromotion: () => `${baseUrl}/api/v1/dev/runbooks/pending-promotion`,
    },
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
