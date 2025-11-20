'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import apiConfig from '@/lib/api-config';
import { useExecutionEvents, ExecutionEventRecord } from './useExecutionEvents';
import type {
  ExecutionSessionSummary,
  ExecutionSessionDetail,
  ExecutionStep,
  RunbookOption,
  ConnectorType,
  ControlAction,
  ConnectionInfo,
  ConsoleLine,
  NetworkClusterOption,
  NetworkDeviceOption,
} from '../types';
import {
  createEventKey,
  formatDate,
  formatDuration,
  formatShortDuration,
  formatConsoleTimestamp,
  parseMetadataObject,
  deriveSandboxProfile,
  normalizeConnectorType,
  normalizeCredentialAlias,
  defaultAliasForConnector,
  deriveHostFromSpec,
  mergeConnectionDefaults,
  buildTranscriptEntry,
} from '../services/utils';

const API_BASE = apiConfig.baseUrl;

export interface UseAgentWorkspaceOptions {
  initialSessionId?: number | null;
}

export interface UseAgentWorkspaceReturn {
  // State
  sessions: ExecutionSessionSummary[];
  loadingSessions: boolean;
  sessionError: string | null;
  activeSessionId: number | null;
  setActiveSessionId: (id: number | null) => void;
  activeSession: ExecutionSessionDetail | null;
  loadingDetail: boolean;
  detailError: string | null;
  eventHistory: ExecutionEventRecord[];
  connected: boolean;
  now: number;
  
  // Connection modal state
  connectModalOpen: boolean;
  setConnectModalOpen: (open: boolean) => void;
  connectConnectorType: ConnectorType;
  setConnectConnectorType: (type: ConnectorType) => void;
  connectSubmitting: boolean;
  connectError: string | null;
  runbooks: RunbookOption[];
  runbooksLoading: boolean;
  
  // Connection form fields
  connectHost: string;
  setConnectHost: (host: string) => void;
  connectDomain: string;
  setConnectDomain: (domain: string) => void;
  connectUsername: string;
  setConnectUsername: (username: string) => void;
  connectPassword: string;
  setConnectPassword: (password: string) => void;
  connectCredentialAlias: string;
  setConnectCredentialAlias: (alias: string) => void;
  connectRunbookId: number | null;
  setConnectRunbookId: (id: number | null) => void;
  connectDescription: string;
  setConnectDescription: (desc: string) => void;
  connectEnvironment: string;
  setConnectEnvironment: (env: string) => void;
  connectPort: string;
  setConnectPort: (port: string) => void;
  connectUseSsl: boolean;
  setConnectUseSsl: (use: boolean) => void;
  connectPrivateKey: string;
  setConnectPrivateKey: (key: string) => void;
  connectInstanceId: string;
  setConnectInstanceId: (id: string) => void;
  connectRegion: string;
  setConnectRegion: (region: string) => void;
  
  // Network fields
  networkClusters: NetworkClusterOption[];
  networkClustersLoading: boolean;
  networkClusterError: string | null;
  selectedClusterId: string;
  setSelectedClusterId: (id: string) => void;
  clusterDevices: NetworkDeviceOption[];
  clusterDevicesLoading: boolean;
  selectedDeviceId: string;
  setSelectedDeviceId: (id: string) => void;
  networkEnablePassword: string;
  setNetworkEnablePassword: (password: string) => void;
  
  // Azure fields
  azureResourceId: string;
  setAzureResourceId: (id: string) => void;
  azureBastionHost: string;
  setAzureBastionHost: (host: string) => void;
  azureTargetHost: string;
  setAzureTargetHost: (host: string) => void;
  azureTenantId: string;
  setAzureTenantId: (id: string) => void;
  azureClientId: string;
  setAzureClientId: (id: string) => void;
  azureClientSecret: string;
  setAzureClientSecret: (secret: string) => void;
  
  // GCP fields
  gcpProjectId: string;
  setGcpProjectId: (id: string) => void;
  gcpZone: string;
  setGcpZone: (zone: string) => void;
  gcpInstanceName: string;
  setGcpInstanceName: (name: string) => void;
  gcpTargetHost: string;
  setGcpTargetHost: (host: string) => void;
  
  // Manual command state
  commandInput: string;
  setCommandInput: (cmd: string) => void;
  commandReason: string;
  setCommandReason: (reason: string) => void;
  commandSubmitting: boolean;
  commandError: string | null;
  
  // Control state
  controlBusy: ControlAction | null;
  controlError: string | null;
  
  // Step action state
  stepActionBusy: number | null;
  stepActionError: string | null;
  
  // Computed values
  connectionInfo: ConnectionInfo;
  consoleLines: ConsoleLine[];
  connectionLabel: string;
  selectedRunbook: RunbookOption | null;
  runbookPolicy: any;
  
  // Actions
  fetchSessions: () => Promise<void>;
  fetchSessionDetail: (sessionId: number) => Promise<void>;
  handleManualCommandSubmit: () => Promise<void>;
  handleControlAction: (action: ControlAction) => Promise<void>;
  handleStepApproval: (step: ExecutionStep, approve: boolean) => Promise<void>;
  handleConnectSubmit: () => Promise<void>;
  closeConnectModal: () => void;
  resetConnectForm: () => void;
}

export function useAgentWorkspace(
  options: UseAgentWorkspaceOptions = {}
): UseAgentWorkspaceReturn {
  const { initialSessionId = null } = options;
  const workspaceEnabled =
    process.env.NEXT_PUBLIC_AGENT_WORKSPACE_ENABLED !== 'false';

  // Session state
  const [sessions, setSessions] = useState<ExecutionSessionSummary[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(initialSessionId);
  const [activeSession, setActiveSession] = useState<ExecutionSessionDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [initialEvents, setInitialEvents] = useState<ExecutionEventRecord[]>([]);
  const eventMapRef = useRef<Map<string, ExecutionEventRecord>>(new Map());
  const [eventHistory, setEventHistory] = useState<ExecutionEventRecord[]>([]);
  const [now, setNow] = useState(() => Date.now());
  const activeSessionIdRef = useRef<number | null>(initialSessionId);

  // Connection modal state
  const [connectModalOpen, setConnectModalOpen] = useState(false);
  const [connectConnectorType, setConnectConnectorType] = useState<ConnectorType>('winrm');
  const [connectSubmitting, setConnectSubmitting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [runbooks, setRunbooks] = useState<RunbookOption[]>([]);
  const [runbooksLoading, setRunbooksLoading] = useState(false);
  const lastPrefillRunbookIdRef = useRef<number | null>(null);

  // Connection form fields
  const [connectHost, setConnectHost] = useState('');
  const [connectDomain, setConnectDomain] = useState('');
  const [connectUsername, setConnectUsername] = useState('');
  const [connectPassword, setConnectPassword] = useState('');
  const [connectCredentialAlias, setConnectCredentialAlias] = useState('');
  const [connectRunbookId, setConnectRunbookId] = useState<number | null>(null);
  const [connectDescription, setConnectDescription] = useState('');
  const [connectEnvironment, setConnectEnvironment] = useState('');
  const [connectPort, setConnectPort] = useState('');
  const [connectUseSsl, setConnectUseSsl] = useState(false);
  const [connectPrivateKey, setConnectPrivateKey] = useState('');
  const [connectInstanceId, setConnectInstanceId] = useState('');
  const [connectRegion, setConnectRegion] = useState('');

  // Network fields
  const [networkClusters, setNetworkClusters] = useState<NetworkClusterOption[]>([]);
  const [networkClustersLoading, setNetworkClustersLoading] = useState(false);
  const [networkClusterError, setNetworkClusterError] = useState<string | null>(null);
  const [selectedClusterId, setSelectedClusterId] = useState('');
  const [clusterDevices, setClusterDevices] = useState<NetworkDeviceOption[]>([]);
  const [clusterDevicesLoading, setClusterDevicesLoading] = useState(false);
  const [selectedDeviceId, setSelectedDeviceId] = useState('');
  const [networkEnablePassword, setNetworkEnablePassword] = useState('');

  // Azure fields
  const [azureResourceId, setAzureResourceId] = useState('');
  const [azureBastionHost, setAzureBastionHost] = useState('');
  const [azureTargetHost, setAzureTargetHost] = useState('');
  const [azureTenantId, setAzureTenantId] = useState('');
  const [azureClientId, setAzureClientId] = useState('');
  const [azureClientSecret, setAzureClientSecret] = useState('');

  // GCP fields
  const [gcpProjectId, setGcpProjectId] = useState('');
  const [gcpZone, setGcpZone] = useState('');
  const [gcpInstanceName, setGcpInstanceName] = useState('');
  const [gcpTargetHost, setGcpTargetHost] = useState('');

  // Manual command state
  const [commandInput, setCommandInput] = useState('');
  const [commandReason, setCommandReason] = useState('');
  const [commandSubmitting, setCommandSubmitting] = useState(false);
  const [commandError, setCommandError] = useState<string | null>(null);

  // Control state
  const [controlBusy, setControlBusy] = useState<ControlAction | null>(null);
  const [controlError, setControlError] = useState<string | null>(null);

  // Step action state
  const [stepActionBusy, setStepActionBusy] = useState<number | null>(null);
  const [stepActionError, setStepActionError] = useState<string | null>(null);

  const { events: liveBatch, connected } = useExecutionEvents(
    activeSessionId,
    workspaceEnabled
  );

  const upsertEvents = useCallback((incoming: ExecutionEventRecord[]) => {
    if (!incoming || incoming.length === 0) return;
    const map = eventMapRef.current;
    incoming.forEach((evt) => {
      const key = createEventKey(evt);
      map.set(key, evt);
    });
    const sorted = Array.from(map.values()).sort((a, b) => {
      const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
      const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
      return aTime - bTime;
    });
    setEventHistory(sorted);
  }, []);

  useEffect(() => {
    if (initialEvents.length > 0) {
      upsertEvents(initialEvents);
    }
  }, [initialEvents, upsertEvents]);

  useEffect(() => {
    if (liveBatch.length > 0) {
      upsertEvents(liveBatch);
    }
  }, [liveBatch, upsertEvents]);

  useEffect(() => {
    const interval = window.setInterval(() => setNow(Date.now()), 30_000);
    return () => window.clearInterval(interval);
  }, []);

  const fetchSessions = useCallback(async () => {
    setLoadingSessions(true);
    setSessionError(null);
    try {
      const response = await fetch(
        `${API_BASE}/api/v1/executions/demo/executions?limit=50`
      );
      if (!response.ok) {
        throw new Error(`Failed to fetch sessions (${response.status})`);
      }
      const data = await response.json();
      const items: ExecutionSessionSummary[] = Array.isArray(data.sessions)
        ? data.sessions.map((item: any) => ({
            id: item.id,
            runbook_id: item.runbook_id,
            runbook_title: item.runbook_title ?? 'Runbook',
            status: item.status ?? 'pending',
            started_at: item.started_at,
            completed_at: item.completed_at,
          }))
        : [];
      setSessions(items);
      if (!activeSessionIdRef.current && items.length > 0) {
        const firstId = items[0].id;
        activeSessionIdRef.current = firstId;
        setActiveSessionId(firstId);
      }
    } catch (error: any) {
      setSessionError(error?.message || 'Failed to load sessions');
    } finally {
      setLoadingSessions(false);
    }
  }, []);

  const fetchSessionDetail = useCallback(
    async (sessionId: number) => {
      setLoadingDetail(true);
      setDetailError(null);
      try {
        const [detailRes, eventsRes] = await Promise.all([
          fetch(`${API_BASE}/api/v1/executions/demo/sessions/${sessionId}`),
          fetch(
            `${API_BASE}/api/v1/executions/demo/sessions/${sessionId}/events?limit=200`
          ),
        ]);
        if (!detailRes.ok) {
          throw new Error(`Failed to fetch session (${detailRes.status})`);
        }
        const detail = await detailRes.json();
        const normalized: ExecutionSessionDetail = {
          id: detail.id,
          runbook_id: detail.runbook_id,
          runbook_title: detail.runbook_title ?? 'Runbook',
          status: detail.status ?? 'pending',
          started_at: detail.started_at,
          completed_at: detail.completed_at,
          issue_description: detail.issue_description,
          current_step: detail.current_step,
          waiting_for_approval: detail.waiting_for_approval,
          sandbox_profile: detail.sandbox_profile,
          steps: Array.isArray(detail.steps) ? detail.steps : [],
          connection: detail.connection ?? null,
        };
        setActiveSession(normalized);

        if (eventsRes.ok) {
          const eventsPayload = await eventsRes.json();
          const normalizedEvents: ExecutionEventRecord[] = Array.isArray(
            eventsPayload
          )
            ? eventsPayload.map((evt: any) => ({
                stream_id: evt.stream_id,
                event: evt.event,
                payload: evt.payload,
                step_number: evt.step_number,
                created_at: evt.created_at,
              }))
            : [];
          eventMapRef.current = new Map();
          setInitialEvents(normalizedEvents);
        } else {
          eventMapRef.current = new Map();
          setInitialEvents([]);
        }
      } catch (error: any) {
        setDetailError(error?.message || 'Failed to load session');
      } finally {
        setLoadingDetail(false);
      }
    },
    []
  );

  const loadRunbooks = useCallback(async () => {
    setRunbooksLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/runbooks/demo`);
      if (!response.ok) {
        throw new Error(`Failed to load runbooks (${response.status})`);
      }
      const payload = await response.json();
      const collection = Array.isArray(payload?.runbooks)
        ? payload.runbooks
        : Array.isArray(payload?.items)
        ? payload.items
        : Array.isArray(payload)
        ? payload
        : [];
      const options: RunbookOption[] = collection.map((item: any) => {
        const metadata = parseMetadataObject(item.meta_data);
        return {
          id: item.id,
          title: item.title ?? `Runbook #${item.id}`,
          description:
            item.description ??
            item.summary ??
            metadata?.issue_description ??
            null,
          metadata,
        };
      });
      setRunbooks(options);
    } catch (error: any) {
      console.error('Failed to load runbooks', error);
      setConnectError(error?.message || 'Failed to load runbooks');
    } finally {
      setRunbooksLoading(false);
    }
  }, []);

  const resetConnectForm = useCallback(() => {
    setConnectConnectorType('winrm');
    setConnectHost('');
    setConnectDomain('');
    setConnectUsername('');
    setConnectPassword('');
    setConnectCredentialAlias('');
    setConnectRunbookId(null);
    setConnectDescription('');
    setConnectEnvironment('');
    setConnectError(null);
    setConnectPort('');
    setConnectUseSsl(false);
    setConnectPrivateKey('');
    setConnectInstanceId('');
    setConnectRegion('');
    lastPrefillRunbookIdRef.current = null;
    setNetworkClusters([]);
    setNetworkClustersLoading(false);
    setNetworkClusterError(null);
    setSelectedClusterId('');
    setClusterDevices([]);
    setClusterDevicesLoading(false);
    setSelectedDeviceId('');
    setNetworkEnablePassword('');
    setAzureResourceId('');
    setAzureBastionHost('');
    setAzureTargetHost('');
    setAzureTenantId('');
    setAzureClientId('');
    setAzureClientSecret('');
    setGcpProjectId('');
    setGcpZone('');
    setGcpInstanceName('');
    setGcpTargetHost('');
  }, []);

  const closeConnectModal = useCallback(() => {
    setConnectModalOpen(false);
    resetConnectForm();
  }, [resetConnectForm]);

  // Computed values
  const sortedRunbooks = useMemo(
    () => [...runbooks].sort((a, b) => a.title.localeCompare(b.title)),
    [runbooks]
  );

  const selectedRunbook = useMemo(
    () => runbooks.find((r) => r.id === connectRunbookId) ?? null,
    [runbooks, connectRunbookId]
  );

  const runbookPolicy = useMemo(() => {
    if (!selectedRunbook) return null;
    const metadata = selectedRunbook.metadata ?? {};
    const spec = metadata.runbook_spec ?? {};
    const connectionDefaults = mergeConnectionDefaults(
      spec.connection,
      spec.target
    );
    const connectorHint = normalizeConnectorType(
      connectionDefaults.type || connectionDefaults.connector_type,
      spec.service || metadata.service
    );
    const env =
      (spec.env ??
        metadata.env ??
        metadata.environment ??
        metadata.run_environment ??
        '') || '';
    const risk = (spec.risk ?? metadata.risk ?? '') || '';
    const reviewRequired = Boolean(
      spec.review_required ??
        metadata.review_required ??
        metadata?.policy?.review_required ??
        false
    );
    const hostCandidate = deriveHostFromSpec(spec);
    const credentialAlias = normalizeCredentialAlias(
      connectionDefaults.credential_source ??
        metadata.credential_source ??
        metadata.credential_alias,
      connectorHint
    );
    const sandboxProfile =
      metadata.sandbox_profile || deriveSandboxProfile(env, risk);
    return {
      env,
      risk,
      reviewRequired,
      connectorHint,
      credentialAlias,
      sandboxProfile,
      connectionDefaults,
      hostCandidate,
    };
  }, [selectedRunbook]);

  const connectionLabel = useMemo(() => {
    if (!workspaceEnabled) return 'disabled';
    return connected ? 'connected' : 'connecting...';
  }, [connected, workspaceEnabled]);

  const connectionInfo: ConnectionInfo = useMemo(() => {
    const info: ConnectionInfo = {
      sandboxProfile: activeSession?.sandbox_profile,
    };

    if (activeSession?.connection) {
      const sessionConn = activeSession.connection as Record<string, any>;
      const target = (sessionConn.target as Record<string, any>) || {};
      info.host = sessionConn.host ?? target.host;
      info.environment = sessionConn.environment ?? target.environment;
      info.service = sessionConn.service ?? target.service;
      info.connector =
        sessionConn.connector_type ?? sessionConn.connector;
      info.credentialSource = sessionConn.credential_source;
    }

    const reversedEvents = [...eventHistory].reverse();
    const forwardEvents = eventHistory;

    const assignmentEvent = reversedEvents.find(
      (evt) => evt.event === 'worker.assignment_received'
    );
    if (assignmentEvent) {
      const assignmentPayload = assignmentEvent.payload?.payload ?? {};
      const metadata = assignmentPayload.metadata ?? {};
      const target = metadata.target ?? {};
      info.host = target.host ?? metadata.host ?? info.host;
      info.environment =
        target.environment ??
        metadata.environment ??
        assignmentPayload.environment ??
        info.environment;
      info.service =
        target.service ?? metadata.service ?? assignmentPayload.service;
      info.connector =
        metadata.connector_type ??
        assignmentPayload.connector_type ??
        info.connector;
      info.credentialSource =
        metadata.credential_source ??
        metadata.credential_provider ??
        info.credentialSource;
      info.workerId = assignmentEvent.payload?.worker_id ?? info.workerId;
    }

    const connectionEvent = reversedEvents.find(
      (evt) => evt.event === 'agent.connection_established'
    );
    if (connectionEvent) {
      info.host = info.host ?? connectionEvent.payload?.host;
      info.connector =
        info.connector ?? connectionEvent.payload?.connector_type;
      info.credentialSource =
        info.credentialSource ?? connectionEvent.payload?.credential_source;
      info.workerId =
        connectionEvent.payload?.worker_id ?? info.workerId;
    }

    const connectionTimestamp = connectionEvent?.created_at
      ? Date.parse(connectionEvent.created_at)
      : undefined;
    const sessionStartEvent =
      forwardEvents.find((evt) => evt.event === 'session.queued') ||
      forwardEvents.find((evt) => evt.event === 'session.created');
    const sessionStartTimestamp = sessionStartEvent?.created_at
      ? Date.parse(sessionStartEvent.created_at)
      : undefined;
    if (
      connectionTimestamp &&
      sessionStartTimestamp &&
      !Number.isNaN(connectionTimestamp) &&
      !Number.isNaN(sessionStartTimestamp)
    ) {
      info.connectionLatencyMs = Math.max(
        0,
        connectionTimestamp - sessionStartTimestamp
      );
      info.connectionEstablishedAt = connectionEvent?.created_at;
    }

    const policyEvent = reversedEvents.find(
      (evt) => evt.event === 'session.policy'
    );
    if (policyEvent) {
      info.slaMinutes = policyEvent.payload?.sla_minutes ?? info.slaMinutes;
      info.sandboxProfile =
        policyEvent.payload?.profile ?? info.sandboxProfile;
    }

    const approvalEvent = reversedEvents.find(
      (evt) => evt.event === 'approval.policy'
    );
    if (approvalEvent) {
      info.approvalMode = approvalEvent.payload?.mode ?? info.approvalMode;
    }

    if (info.slaMinutes && activeSession?.started_at) {
      const startedAt = new Date(activeSession.started_at).getTime();
      if (!Number.isNaN(startedAt)) {
        const deadlineMs = startedAt + info.slaMinutes * 60 * 1000;
        info.slaDeadline = new Date(deadlineMs);
        info.slaRemainingMs = Math.max(0, deadlineMs - now);
      }
    }

    const lastCommandEvent = reversedEvents.find(
      (evt) =>
        evt.event === 'session.command.completed' ||
        evt.event === 'session.command.failed'
    );
    if (lastCommandEvent) {
      const streamId =
        lastCommandEvent.payload?.stream_id ?? lastCommandEvent.stream_id;
      let durationMs =
        typeof lastCommandEvent.payload?.duration_ms === 'number'
          ? lastCommandEvent.payload?.duration_ms
          : undefined;
      if (
        !durationMs &&
        streamId &&
        lastCommandEvent.created_at &&
        forwardEvents.length > 0
      ) {
        const requestEvent = forwardEvents.find(
          (evt) =>
            evt.event === 'session.command.requested' &&
            (evt.payload?.stream_id ?? evt.stream_id) === streamId
        );
        if (requestEvent?.created_at) {
          const startedTs = Date.parse(requestEvent.created_at);
          const finishedTs = Date.parse(lastCommandEvent.created_at);
          if (!Number.isNaN(startedTs) && !Number.isNaN(finishedTs)) {
            durationMs = Math.max(0, finishedTs - startedTs);
          }
        }
      }
      info.lastCommandDurationMs = durationMs;
      info.lastCommandStatus =
        lastCommandEvent.event === 'session.command.failed'
          ? 'error'
          : 'success';
      info.lastCommandCompletedAt = lastCommandEvent.created_at;
      if (
        typeof lastCommandEvent.payload?.retry_count === 'number' &&
        lastCommandEvent.payload?.retry_count > 0
      ) {
        info.lastCommandRetries = lastCommandEvent.payload?.retry_count;
      }
    }

    return info;
  }, [activeSession, eventHistory, now]);

  const consoleLines = useMemo(() => {
    const lines: ConsoleLine[] = [];
    if (eventHistory.length === 0) {
      return lines;
    }

    const commandRequests = new Map<
      string,
      { timestamp?: number; command?: string; reason?: string }
    >();

    const sessionStartEvent =
      eventHistory.find((evt) => evt.event === 'session.queued') ||
      eventHistory.find((evt) => evt.event === 'session.created');
    const sessionStartTimestamp = sessionStartEvent?.created_at
      ? Date.parse(sessionStartEvent.created_at)
      : undefined;

    eventHistory.forEach((evt) => {
      const eventName = (evt.event || '').toLowerCase();
      const payload = evt.payload ?? {};
      const timestampLabel = formatConsoleTimestamp(evt.created_at);
      const numericTimestamp = evt.created_at ? Date.parse(evt.created_at) : undefined;
      const baseKey = createEventKey(evt);

      const pushLine = (line: ConsoleLine) => {
        lines.push(line);
      };

      if (eventName === 'agent.connection_established') {
        const connector = payload.connector_type ?? payload.metadata?.connector_type;
        const targetHost = payload.host ?? 'target host';
        const latency =
          numericTimestamp &&
          sessionStartTimestamp &&
          !Number.isNaN(numericTimestamp) &&
          !Number.isNaN(sessionStartTimestamp)
            ? Math.max(0, numericTimestamp - sessionStartTimestamp)
            : undefined;
        const meta = formatShortDuration(latency);
        pushLine({
          key: `${baseKey}:connection`,
          text: `Connected to ${targetHost}${connector ? ` (${connector})` : ''}`,
          tone: 'success',
          timestamp: timestampLabel,
          meta: meta ? `after ${meta}` : undefined,
        });
        return;
      }

      if (eventName === 'session.command.requested') {
        const rawCommand =
          typeof payload.command === 'string'
            ? payload.command
            : payload.command
            ? JSON.stringify(payload.command, null, 2)
            : '<no command>';
        const commandText = rawCommand.trim().length > 0 ? rawCommand.trim() : '<no command>';
        const reasonText =
          typeof payload.reason === 'string' && payload.reason.trim().length > 0
            ? payload.reason.trim()
            : undefined;
        const streamId = payload.stream_id ?? evt.stream_id ?? baseKey;
        commandRequests.set(streamId, {
          timestamp: numericTimestamp,
          command: commandText,
          reason: reasonText,
        });
        pushLine({
          key: `${baseKey}:prompt`,
          text: `> ${commandText}`,
          tone: 'prompt',
          timestamp: timestampLabel,
        });
        return;
      }

      if (eventName === 'session.command.completed' || eventName === 'session.command.failed') {
        const streamId = payload.stream_id ?? evt.stream_id ?? baseKey;
        let durationMs =
          typeof payload.duration_ms === 'number' ? payload.duration_ms : undefined;
        if (
          !durationMs &&
          commandRequests.get(streamId)?.timestamp &&
          numericTimestamp &&
          !Number.isNaN(numericTimestamp)
        ) {
          const request = commandRequests.get(streamId);
          if (request?.timestamp) {
            durationMs = Math.max(0, numericTimestamp - request.timestamp);
          }
        }
        const metaParts = [
          formatShortDuration(durationMs),
          payload.exit_code !== undefined && payload.exit_code !== null
            ? `exit ${payload.exit_code}`
            : undefined,
        ];
        const meta = metaParts.filter(Boolean).join(' · ') || undefined;
        const success = eventName === 'session.command.completed';
        const message = success
          ? payload.message || 'Command completed'
          : payload.error || 'Command failed';
        pushLine({
          key: `${baseKey}:result`,
          text: `${success ? '✔' : '✖'} ${message}`,
          tone: success ? 'success' : 'error',
          timestamp: timestampLabel,
          meta,
        });

        const rawOutput =
          typeof payload.output === 'string'
            ? payload.output
            : payload.stdout || payload.detail || payload.stderr;
        if (rawOutput) {
          const outputText =
            typeof rawOutput === 'string'
              ? rawOutput
              : JSON.stringify(rawOutput, null, 2);
          const linesOut = outputText.split(/\r?\n/);
          linesOut.forEach((text, idx) => {
            if (text.trim().length === 0) return;
            pushLine({
              key: `${baseKey}:out:${idx}`,
              text,
              tone: success ? 'output' : 'error',
              timestamp: idx === 0 ? timestampLabel : undefined,
            });
          });
        }

        commandRequests.delete(streamId);
        return;
      }
    });

    return lines;
  }, [eventHistory]);

  // Action handlers
  const handleManualCommandSubmit = useCallback(async () => {
    if (!activeSessionId) return;
    if (!commandInput.trim()) {
      setCommandError('Enter a command to run.');
      return;
    }
    setCommandSubmitting(true);
    setCommandError(null);
    try {
      const connector = connectionInfo.connector?.toLowerCase();
      const shellHint =
        connector === 'winrm'
          ? 'powershell'
          : connector === 'ssh' ||
            connector === 'aws_ssm' ||
            connector === 'azure_bastion' ||
            connector === 'gcp_iap'
          ? 'bash'
          : connector === 'network_cluster' || connector === 'network_device'
          ? 'cli'
          : undefined;
      const response = await fetch(
        `${API_BASE}/api/v1/executions/demo/sessions/${activeSessionId}/commands`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            command: commandInput.trim(),
            reason: commandReason.trim() || undefined,
            shell: shellHint,
          }),
        }
      );
      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        const detail =
          (errorBody && (errorBody.detail || errorBody.message)) ||
          `Failed to submit command (status ${response.status})`;
        throw new Error(detail);
      }
      setCommandInput('');
      setCommandReason('');
      if (activeSessionId) {
        await fetchSessionDetail(activeSessionId);
      }
      await fetchSessions();
    } catch (error: any) {
      setCommandError(error?.message || 'Failed to submit command');
    } finally {
      setCommandSubmitting(false);
    }
  }, [
    activeSessionId,
    commandInput,
    commandReason,
    fetchSessionDetail,
    fetchSessions,
    connectionInfo.connector,
  ]);

  const handleControlAction = useCallback(
    async (action: ControlAction) => {
      if (!activeSessionId) return;
      if (controlBusy) return;

      setControlBusy(action);
      setControlError(null);

      let reason: string | undefined;
      if (action === 'rollback' && typeof window !== 'undefined') {
        const confirmed = window.confirm(
          'Trigger rollback for this execution session?'
        );
        if (!confirmed) {
          setControlBusy(null);
          return;
        }
        reason = window.prompt('Rollback reason (optional)') ?? undefined;
      }

      try {
        const response = await fetch(
          `${API_BASE}/api/v1/executions/demo/sessions/${activeSessionId}/control`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              action,
              reason,
            }),
          }
        );
        if (!response.ok) {
          const errorBody = await response.json().catch(() => null);
          const detail =
            (errorBody && (errorBody.detail || errorBody.message)) ||
            `Failed to ${action} session (status ${response.status})`;
          throw new Error(detail);
        }
        await fetchSessionDetail(activeSessionId);
        await fetchSessions();
      } catch (error: any) {
        setControlError(error?.message || `Failed to ${action} session`);
      } finally {
        setControlBusy(null);
      }
    },
    [activeSessionId, controlBusy, fetchSessionDetail, fetchSessions]
  );

  const handleStepApproval = useCallback(
    async (step: ExecutionStep, approve: boolean) => {
      if (!activeSessionId) return;
      if (step.step_number === undefined || step.step_number === null) {
        setStepActionError('Step number missing for approval update.');
        return;
      }
      setStepActionBusy(step.step_number);
      setStepActionError(null);
      try {
        const response = await fetch(
          `${API_BASE}/api/v1/executions/demo/sessions/${activeSessionId}/steps`,
          {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              step_number: step.step_number,
              step_type: step.step_type ?? 'main',
              completed: Boolean(step.completed),
              approved: approve,
            }),
          }
        );
        if (!response.ok) {
          const errorBody = await response.json().catch(() => null);
          const detail =
            (errorBody && (errorBody.detail || errorBody.message)) ||
            'Failed to update step approval';
          throw new Error(detail);
        }
        await fetchSessionDetail(activeSessionId);
        await fetchSessions();
      } catch (error: any) {
        setStepActionError(error?.message || 'Failed to update step approval');
      } finally {
        setStepActionBusy(null);
      }
    },
    [activeSessionId, fetchSessionDetail, fetchSessions]
  );

  const handleConnectSubmit = useCallback(async () => {
    if (!connectRunbookId) {
      setConnectError('Select a runbook to execute.');
      return;
    }

    const connectorType = connectConnectorType;
    const environment = connectEnvironment.trim() || undefined;
    const requiresHost = connectorType === 'winrm' || connectorType === 'ssh';
    const host = connectHost.trim();

    if (requiresHost && !host) {
      setConnectError('Target host is required.');
      return;
    }

    setConnectSubmitting(true);
    setConnectError(null);

    const currentRunbook = selectedRunbook;
    const policy = runbookPolicy;

    if (!currentRunbook) {
      setConnectSubmitting(false);
      setConnectError('Select a runbook to execute.');
      return;
    }

    if (policy?.reviewRequired) {
      setConnectSubmitting(false);
      setConnectError(
        'This runbook requires approval before remote execution. Request approval or pick another runbook.'
      );
      return;
    }

    const metadata: Record<string, any> = {
      environment: environment || policy?.env || 'prod',
      service: policy?.connectionDefaults?.service || currentRunbook.metadata?.service,
    };

    if (connectorType === 'winrm' || connectorType === 'ssh') {
      metadata.target = {
        host: host,
        domain: connectDomain.trim() || undefined,
        port: connectPort ? Number(connectPort) : undefined,
        use_ssl: connectUseSsl || undefined,
      };
      metadata.connection = {
        type: connectorType,
        username: connectUsername.trim() || undefined,
        password: connectPassword.trim() || undefined,
        credential_alias: connectCredentialAlias.trim() || undefined,
        private_key: connectPrivateKey.trim() || undefined,
      };
    } else if (connectorType === 'aws_ssm') {
      metadata.target = {
        instance_id: connectInstanceId.trim(),
        region: connectRegion.trim() || 'us-east-1',
      };
      metadata.connection = {
        type: connectorType,
        credential_alias: connectCredentialAlias.trim() || undefined,
      };
    } else if (connectorType === 'network_cluster' || connectorType === 'network_device') {
      metadata.target = {
        cluster_id: selectedClusterId || undefined,
        device_id: connectorType === 'network_device' ? selectedDeviceId : undefined,
      };
      metadata.connection = {
        type: connectorType,
        enable_password: networkEnablePassword.trim() || undefined,
        credential_alias: connectCredentialAlias.trim() || undefined,
      };
    } else if (connectorType === 'azure_bastion') {
      metadata.target = {
        resource_id: azureResourceId.trim(),
        bastion_host: azureBastionHost.trim(),
        target_host: azureTargetHost.trim(),
      };
      metadata.connection = {
        type: connectorType,
        tenant_id: azureTenantId.trim() || undefined,
        client_id: azureClientId.trim() || undefined,
        client_secret: azureClientSecret.trim() || undefined,
        credential_alias: connectCredentialAlias.trim() || undefined,
      };
    } else if (connectorType === 'gcp_iap') {
      metadata.target = {
        project_id: gcpProjectId.trim(),
        zone: gcpZone.trim(),
        instance_name: gcpInstanceName.trim(),
        target_host: gcpTargetHost.trim(),
      };
      metadata.connection = {
        type: connectorType,
        credential_alias: connectCredentialAlias.trim() || undefined,
      };
    }

    metadata.sandbox_profile = policy?.sandboxProfile ?? metadata.sandbox_profile ?? 'default';

    if (currentRunbook.metadata?.runbook_spec) {
      metadata.runbook_spec = currentRunbook.metadata.runbook_spec;
    }

    metadata.runbook_context = {
      id: connectRunbookId,
      title: currentRunbook.title,
      env: metadata.environment || null,
      risk: policy?.risk || null,
    };

    const body: Record<string, any> = {
      runbook_id: connectRunbookId,
      metadata,
    };

    const description = connectDescription.trim();
    if (description) {
      body.issue_description = description;
    }

    try {
      const response = await fetch(`${API_BASE}/api/v1/executions/demo/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        const detail =
          (errorBody && (errorBody.detail || errorBody.message)) ||
          `Failed to create session (status ${response.status})`;
        throw new Error(detail);
      }
      const payload = await response.json();
      const newSessionId =
        typeof payload?.id === 'number'
          ? payload.id
          : typeof payload?.session_id === 'number'
          ? payload.session_id
          : null;

      resetConnectForm();
      setConnectModalOpen(false);

      await fetchSessions();

      if (newSessionId) {
        activeSessionIdRef.current = newSessionId;
        setActiveSessionId(newSessionId);
        await fetchSessionDetail(newSessionId);
      }
    } catch (error: any) {
      setConnectError(error?.message || 'Failed to start remote session');
    } finally {
      setConnectSubmitting(false);
    }
  }, [
    connectConnectorType,
    connectRunbookId,
    connectHost,
    connectUsername,
    connectPassword,
    connectCredentialAlias,
    connectDomain,
    connectEnvironment,
    connectDescription,
    connectPort,
    connectUseSsl,
    connectPrivateKey,
    connectInstanceId,
    connectRegion,
    networkClusters,
    selectedClusterId,
    clusterDevices,
    selectedDeviceId,
    networkEnablePassword,
    azureResourceId,
    azureBastionHost,
    azureTargetHost,
    azureTenantId,
    azureClientId,
    azureClientSecret,
    gcpProjectId,
    gcpZone,
    gcpInstanceName,
    gcpTargetHost,
    resetConnectForm,
    fetchSessions,
    fetchSessionDetail,
    selectedRunbook,
    runbookPolicy,
  ]);

  // Effects
  useEffect(() => {
    if (
      initialSessionId !== null &&
      initialSessionId !== undefined &&
      initialSessionId !== activeSessionIdRef.current
    ) {
      activeSessionIdRef.current = initialSessionId;
      setActiveSessionId(initialSessionId);
      fetchSessions();
    }
    if (
      initialSessionId === null &&
      activeSessionIdRef.current !== null
    ) {
      activeSessionIdRef.current = null;
      setActiveSessionId(null);
    }
  }, [initialSessionId, fetchSessions]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  useEffect(() => {
    activeSessionIdRef.current = activeSessionId;
    if (activeSessionId) {
      fetchSessionDetail(activeSessionId);
    } else {
      setActiveSession(null);
      setInitialEvents([]);
      eventMapRef.current = new Map();
      setEventHistory([]);
    }
  }, [activeSessionId, fetchSessionDetail]);

  useEffect(() => {
    if (!connectModalOpen) return;
    if (runbooks.length === 0 && !runbooksLoading) {
      void loadRunbooks();
    }
  }, [connectModalOpen, loadRunbooks, runbooks.length, runbooksLoading]);

  return {
    // State
    sessions,
    loadingSessions,
    sessionError,
    activeSessionId,
    setActiveSessionId,
    activeSession,
    loadingDetail,
    detailError,
    eventHistory,
    connected,
    now,
    
    // Connection modal state
    connectModalOpen,
    setConnectModalOpen,
    connectConnectorType,
    setConnectConnectorType,
    connectSubmitting,
    connectError,
    runbooks: sortedRunbooks,
    runbooksLoading,
    
    // Connection form fields
    connectHost,
    setConnectHost,
    connectDomain,
    setConnectDomain,
    connectUsername,
    setConnectUsername,
    connectPassword,
    setConnectPassword,
    connectCredentialAlias,
    setConnectCredentialAlias,
    connectRunbookId,
    setConnectRunbookId,
    connectDescription,
    setConnectDescription,
    connectEnvironment,
    setConnectEnvironment,
    connectPort,
    setConnectPort,
    connectUseSsl,
    setConnectUseSsl,
    connectPrivateKey,
    setConnectPrivateKey,
    connectInstanceId,
    setConnectInstanceId,
    connectRegion,
    setConnectRegion,
    
    // Network fields
    networkClusters,
    networkClustersLoading,
    networkClusterError,
    selectedClusterId,
    setSelectedClusterId,
    clusterDevices,
    clusterDevicesLoading,
    selectedDeviceId,
    setSelectedDeviceId,
    networkEnablePassword,
    setNetworkEnablePassword,
    
    // Azure fields
    azureResourceId,
    setAzureResourceId,
    azureBastionHost,
    setAzureBastionHost,
    azureTargetHost,
    setAzureTargetHost,
    azureTenantId,
    setAzureTenantId,
    azureClientId,
    setAzureClientId,
    azureClientSecret,
    setAzureClientSecret,
    
    // GCP fields
    gcpProjectId,
    setGcpProjectId,
    gcpZone,
    setGcpZone,
    gcpInstanceName,
    setGcpInstanceName,
    gcpTargetHost,
    setGcpTargetHost,
    
    // Manual command state
    commandInput,
    setCommandInput,
    commandReason,
    setCommandReason,
    commandSubmitting,
    commandError,
    
    // Control state
    controlBusy,
    controlError,
    
    // Step action state
    stepActionBusy,
    stepActionError,
    
    // Computed values
    connectionInfo,
    consoleLines,
    connectionLabel,
    selectedRunbook,
    runbookPolicy,
    
    // Actions
    fetchSessions,
    fetchSessionDetail,
    handleManualCommandSubmit,
    handleControlAction,
    handleStepApproval,
    handleConnectSubmit,
    closeConnectModal,
    resetConnectForm,
  };
}

