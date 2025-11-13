'use client';

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowPathIcon,
  BoltIcon,
  CheckCircleIcon,
  CommandLineIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  PlayIcon,
  ServerIcon,
  SignalIcon,
  XCircleIcon,
  XMarkIcon,
  WifiIcon,
} from '@heroicons/react/24/outline';
import apiConfig from '@/lib/api-config';
import { useExecutionEvents, ExecutionEventRecord } from './useExecutionEvents';

interface ExecutionStep {
  id?: number;
  step_number: number;
  step_type?: string;
  command?: string;
  requires_approval?: boolean;
  approved?: boolean | null;
  completed?: boolean;
  success?: boolean | null;
  sandbox_profile?: string | null;
}

interface ExecutionSessionSummary {
  id: number;
  runbook_id: number;
  runbook_title?: string;
  status: string;
  started_at?: string;
  completed_at?: string | null;
}

interface ExecutionSessionDetail extends ExecutionSessionSummary {
  issue_description?: string;
  current_step?: number | null;
  waiting_for_approval?: boolean;
  sandbox_profile?: string | null;
  steps: ExecutionStep[];
  connection?: Record<string, any> | null;
}

interface RunbookOption {
  id: number;
  title: string;
  description?: string | null;
  metadata?: Record<string, any> | null;
}

const API_BASE = apiConfig.baseUrl;

interface AgentWorkspaceProps {
  initialSessionId?: number | null;
}

type TranscriptVariant = 'info' | 'success' | 'warning' | 'error' | 'neutral';

type TranscriptEntry = {
  title: string;
  summary?: string;
  detail?: string;
  meta?: Array<{ label: string; value: string }>;
  variant: TranscriptVariant;
  icon: typeof BoltIcon;
  timestamp?: string;
  raw?: string;
};

type ConsoleLineTone = 'prompt' | 'success' | 'error' | 'info' | 'warning' | 'output';

type ConsoleLine = {
  key: string;
  text: string;
  tone: ConsoleLineTone;
  timestamp?: string;
  meta?: string;
};

type ControlAction = 'pause' | 'resume' | 'rollback';

type ConnectorType =
  | 'winrm'
  | 'ssh'
  | 'aws_ssm'
  | 'network_cluster'
  | 'network_device'
  | 'azure_bastion'
  | 'gcp_iap';

type NetworkClusterOption = {
  id: string;
  name: string;
  description?: string;
  vendor?: string;
  management_host?: string;
  transport?: string;
  default_prompt?: string;
};

type NetworkDeviceOption = {
  id: string;
  name: string;
  vendor?: string;
  model?: string;
  role?: string;
  mgmt_ip?: string;
};

type ConnectionInfo = {
  host?: string;
  connector?: string;
  environment?: string;
  service?: string;
  credentialSource?: string;
  workerId?: string;
  sandboxProfile?: string | null;
  slaMinutes?: number;
  slaDeadline?: Date;
  slaRemainingMs?: number;
  approvalMode?: string;
  connectionLatencyMs?: number;
  connectionEstablishedAt?: string;
  lastCommandDurationMs?: number;
  lastCommandStatus?: 'success' | 'error';
  lastCommandCompletedAt?: string;
  lastCommandRetries?: number;
  clusterId?: string;
  deviceId?: string;
};

const statusColor = (status: string) => {
  const normalized = status?.toLowerCase() ?? '';
  switch (normalized) {
    case 'completed':
      return 'text-green-600 bg-green-100';
    case 'failed':
      return 'text-red-600 bg-red-100';
    case 'queued':
    case 'waiting_approval':
      return 'text-amber-600 bg-amber-100';
    default:
      return 'text-blue-600 bg-blue-100';
  }
};

const formatDate = (value?: string) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

const formatDuration = (value?: number) => {
  if (value === undefined || value === null) return '—';
  const totalSeconds = Math.max(0, Math.floor(value / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
};

const formatConsoleTimestamp = (value?: string) => {
  if (!value) return undefined;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return undefined;
  return date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
};

const formatShortDuration = (value?: number) => {
  if (value === undefined || value === null || Number.isNaN(value)) return undefined;
  if (value < 1000) {
    return `${Math.max(0, Math.round(value))}ms`;
  }
  if (value < 60_000) {
    const seconds = value / 1000;
    return `${seconds < 10 ? seconds.toFixed(1) : Math.round(seconds)}s`;
  }
  if (value < 3_600_000) {
    const minutes = value / 60000;
    return `${minutes.toFixed(minutes < 10 ? 1 : 0)}m`;
  }
  const hours = value / 3_600_000;
  return `${hours.toFixed(hours < 10 ? 1 : 0)}h`;
};

const createEventKey = (event: ExecutionEventRecord) => {
  if (event.stream_id) return event.stream_id;
  const stamp = event.created_at ?? '';
  return `${event.event}-${event.step_number ?? 'x'}-${stamp}`;
};

const mergeConnectionDefaults = (
  ...sources: Array<Record<string, any> | null | undefined>
): Record<string, any> => {
  const result: Record<string, any> = {};
  sources.forEach((source) => {
    if (!source || typeof source !== 'object') return;
    Object.entries(source).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') return;
      result[key] = value;
    });
  });
  return result;
};

const deriveSandboxProfile = (env?: string, risk?: string): string => {
  const envNormalized = (env || '').toLowerCase();
  const riskNormalized = (risk || '').toLowerCase();
  if (envNormalized.startsWith('prod')) {
    return riskNormalized === 'high' ? 'prod-critical' : 'prod-standard';
  }
  if (envNormalized.startsWith('stag')) {
    return 'staging-standard';
  }
  if (envNormalized.startsWith('dev') || envNormalized.startsWith('test')) {
    return 'dev-flex';
  }
  return 'default';
};

const defaultAliasForConnector = (connector: ConnectorType): string | undefined => {
  switch (connector) {
    case 'winrm':
      return 'windows-admin';
    case 'aws_ssm':
      return 'ssm-maintenance';
    case 'ssh':
      return 'linux-admin';
    default:
      return undefined;
  }
};

const normalizeConnectorType = (
  explicit?: string,
  service?: string
): ConnectorType => {
  const normalized = (explicit || '').toLowerCase();
  if (['winrm', 'windows', 'powershell'].includes(normalized)) {
    return 'winrm';
  }
  if (['aws_ssm', 'ssm', 'sessionmanager', 'session_manager'].includes(normalized)) {
    return 'aws_ssm';
  }
  if (['network_cluster', 'network-controller', 'cluster', 'netops_cluster'].includes(normalized)) {
    return 'network_cluster';
  }
  if (['network_device', 'network-device', 'device', 'switch', 'router'].includes(normalized)) {
    return 'network_device';
  }
  if (['azure_bastion', 'azure-bastion', 'bastion', 'azure'].includes(normalized)) {
    return 'azure_bastion';
  }
  if (['gcp_iap', 'iap', 'gcp', 'google'].includes(normalized)) {
    return 'gcp_iap';
  }
  if (['ssh', 'linux', 'unix', 'posix'].includes(normalized)) {
    return 'ssh';
  }
  const serviceNormalized = (service || '').toLowerCase();
  if (serviceNormalized.includes('win')) {
    return 'winrm';
  }
  if (serviceNormalized.includes('aws') || serviceNormalized.includes('ssm')) {
    return 'aws_ssm';
  }
  if (serviceNormalized.includes('bastion') || serviceNormalized.includes('azure')) {
    return 'azure_bastion';
  }
  if (serviceNormalized.includes('iap') || serviceNormalized.includes('gcp')) {
    return 'gcp_iap';
  }
  if (serviceNormalized.includes('network') || serviceNormalized.includes('switch')) {
    return 'network_device';
  }
  return 'ssh';
};

const normalizeCredentialAlias = (
  source?: string,
  connector?: ConnectorType
): string | undefined => {
  if (!source) {
    return connector ? defaultAliasForConnector(connector) : undefined;
  }
  const trimmed = source.trim();
  if (!trimmed) {
    return connector ? defaultAliasForConnector(connector) : undefined;
  }
  if (trimmed.startsWith('alias:')) {
    return trimmed.slice(6);
  }
  if (/^(inline|vault)$/i.test(trimmed)) {
    return connector ? defaultAliasForConnector(connector) : undefined;
  }
  return trimmed;
};

const extractHostCandidateFromText = (text?: string) => {
  if (!text) return undefined;
  const pattern = /\b[a-z0-9][a-z0-9\-]{2,}\b/gi;
  const matches = text.match(pattern);
  if (!matches) return undefined;
  const prioritized = matches.find((candidate) =>
    /(prod|db|sql|web|app|srv|server|host|node|vm)/i.test(candidate)
  );
  return (prioritized || matches[0])?.toLowerCase();
};

const deriveHostFromSpec = (spec: any): string | undefined => {
  if (!spec || typeof spec !== 'object') return undefined;
  const sections = ['prechecks', 'steps', 'postchecks'];
  for (const section of sections) {
    const entries = Array.isArray(spec[section]) ? spec[section] : [];
    for (const step of entries) {
      if (!step) continue;
      const host =
        extractHostCandidateFromText(step.command) ||
        extractHostCandidateFromText(step.description);
      if (host) return host;
    }
  }
  return undefined;
};

const parseMetadataObject = (value: any): Record<string, any> | null => {
  if (!value) return null;
  if (typeof value === 'object') return value as Record<string, any>;
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return typeof parsed === 'object' && parsed !== null
        ? (parsed as Record<string, any>)
        : null;
    } catch {
      return null;
    }
  }
  return null;
};

export function AgentWorkspace({ initialSessionId = null }: AgentWorkspaceProps) {
  const workspaceEnabled =
    process.env.NEXT_PUBLIC_AGENT_WORKSPACE_ENABLED !== 'false';
  const [sessions, setSessions] = useState<ExecutionSessionSummary[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(
    initialSessionId
  );
  const [activeSession, setActiveSession] =
    useState<ExecutionSessionDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [initialEvents, setInitialEvents] = useState<ExecutionEventRecord[]>([]);
  const eventMapRef = useRef<Map<string, ExecutionEventRecord>>(new Map());
  const [eventHistory, setEventHistory] = useState<ExecutionEventRecord[]>([]);
  const [now, setNow] = useState(() => Date.now());
  const consoleRef = useRef<HTMLDivElement | null>(null);
  const lastPrefillRunbookIdRef = useRef<number | null>(null);
  const [commandInput, setCommandInput] = useState('');
  const [commandReason, setCommandReason] = useState('');
  const [commandSubmitting, setCommandSubmitting] = useState(false);
  const [commandError, setCommandError] = useState<string | null>(null);
  const [controlBusy, setControlBusy] = useState<ControlAction | null>(null);
  const [controlError, setControlError] = useState<string | null>(null);
  const [stepActionBusy, setStepActionBusy] = useState<number | null>(null);
  const [stepActionError, setStepActionError] = useState<string | null>(null);
  const activeSessionIdRef = useRef<number | null>(initialSessionId);
  const [runbooks, setRunbooks] = useState<RunbookOption[]>([]);
  const [runbooksLoading, setRunbooksLoading] = useState(false);
  const [connectModalOpen, setConnectModalOpen] = useState(false);
  const [connectConnectorType, setConnectConnectorType] =
    useState<ConnectorType>('winrm');
  const [connectSubmitting, setConnectSubmitting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
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
  const [networkClusters, setNetworkClusters] = useState<NetworkClusterOption[]>([]);
  const [networkClustersLoading, setNetworkClustersLoading] = useState(false);
  const [networkClusterError, setNetworkClusterError] = useState<string | null>(null);
  const [selectedClusterId, setSelectedClusterId] = useState('');
  const [clusterDevices, setClusterDevices] = useState<NetworkDeviceOption[]>([]);
  const [clusterDevicesLoading, setClusterDevicesLoading] = useState(false);
  const [selectedDeviceId, setSelectedDeviceId] = useState('');
  const [networkEnablePassword, setNetworkEnablePassword] = useState('');
  const [azureResourceId, setAzureResourceId] = useState('');
  const [azureBastionHost, setAzureBastionHost] = useState('');
  const [azureTargetHost, setAzureTargetHost] = useState('');
  const [gcpProjectId, setGcpProjectId] = useState('');
  const [gcpZone, setGcpZone] = useState('');
  const [gcpInstanceName, setGcpInstanceName] = useState('');
  const [gcpTargetHost, setGcpTargetHost] = useState('');

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
    setGcpProjectId('');
    setGcpZone('');
    setGcpInstanceName('');
    setGcpTargetHost('');
  }, []);

  const closeConnectModal = useCallback(() => {
    setConnectModalOpen(false);
    resetConnectForm();
  }, [resetConnectForm]);

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

  useEffect(() => {
    if (!connectModalOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  }, [connectModalOpen]);

  useEffect(() => {
    if (
      !connectModalOpen ||
      !['network_cluster', 'network_device'].includes(connectConnectorType)
    ) {
      return;
    }
    if (networkClusters.length > 0 || networkClustersLoading) {
      return;
    }
    const fetchClusters = async () => {
      setNetworkClustersLoading(true);
      setNetworkClusterError(null);
      try {
        const response = await fetch(apiConfig.endpoints.network.clusters());
        if (!response.ok) {
          throw new Error(`Failed to fetch clusters (${response.status})`);
        }
        const payload = await response.json();
        const clusters = Array.isArray(payload?.clusters)
          ? (payload.clusters as NetworkClusterOption[])
          : [];
        setNetworkClusters(clusters);
        if (clusters.length > 0 && !selectedClusterId) {
          setSelectedClusterId(clusters[0].id);
        }
      } catch (error: any) {
        console.error('Failed to load network clusters', error);
        setNetworkClusterError(
          error?.message || 'Unable to load network clusters'
        );
      } finally {
        setNetworkClustersLoading(false);
      }
    };
    void fetchClusters();
  }, [
    connectModalOpen,
    connectConnectorType,
    networkClusters.length,
    networkClustersLoading,
    selectedClusterId,
  ]);

  useEffect(() => {
    if (!connectModalOpen || connectConnectorType !== 'network_device') {
      return;
    }
    if (!selectedClusterId) {
      setClusterDevices([]);
      return;
    }
    setClusterDevicesLoading(true);
    const fetchDevices = async () => {
      try {
        const response = await fetch(
          apiConfig.endpoints.network.clusterDevices(selectedClusterId)
        );
        if (!response.ok) {
          throw new Error(`Failed to fetch devices (${response.status})`);
        }
        const payload = await response.json();
        const devices = Array.isArray(payload?.devices)
          ? (payload.devices as NetworkDeviceOption[])
          : [];
        setClusterDevices(devices);
        if (devices.length > 0 && !selectedDeviceId) {
          setSelectedDeviceId(devices[0].id);
        }
      } catch (error: any) {
        console.error('Failed to load cluster devices', error);
        setConnectError(
          error?.message || 'Unable to load devices for selected cluster'
        );
      } finally {
        setClusterDevicesLoading(false);
      }
    };
    void fetchDevices();
  }, [
    connectModalOpen,
    connectConnectorType,
    selectedClusterId,
  ]);

  useEffect(() => {
    if (connectModalOpen && runbooks.length > 0 && connectRunbookId === null) {
      setConnectRunbookId(runbooks[0].id);
    }
  }, [connectModalOpen, runbooks, connectRunbookId]);

  const sortedRunbooks = useMemo(
    () => runbooks.slice().sort((a, b) => a.title.localeCompare(b.title)),
    [runbooks]
  );

  const selectedRunbook = useMemo(
    () => sortedRunbooks.find((item) => item.id === connectRunbookId) ?? null,
    [sortedRunbooks, connectRunbookId]
  );

  const runbookPolicy = useMemo(() => {
    if (!selectedRunbook) return null;
    const metadata = selectedRunbook.metadata ?? {};
    const spec = metadata.runbook_spec ?? {};
    const connectionDefaults = mergeConnectionDefaults(
      metadata.connection_defaults,
      metadata.connection,
      metadata.target,
      metadata.connector,
      metadata.credentials?.connection,
      spec.connection_defaults,
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
    const hostCandidate =
      (typeof connectionDefaults.host === 'string' && connectionDefaults.host) ||
      deriveHostFromSpec(spec) ||
      (metadata.target && typeof metadata.target.host === 'string'
        ? metadata.target.host
        : undefined);
    const credentialAlias = normalizeCredentialAlias(
      connectionDefaults.credential_source ??
        metadata.credential_source ??
        metadata.credential_alias,
      connectorHint
    );
    const sandboxProfile =
      metadata.sandbox_profile || deriveSandboxProfile(env, risk);
    const instanceId =
      connectionDefaults.instance_id ?? connectionDefaults.instanceId;
    const region = connectionDefaults.region;
    const domain = connectionDefaults.domain;
    const username = connectionDefaults.username;
    const port = connectionDefaults.port;
    const useSsl =
      typeof connectionDefaults.use_ssl === 'boolean'
        ? connectionDefaults.use_ssl
        : undefined;
    const description =
      metadata.issue_description ||
      spec.description ||
      selectedRunbook.description ||
      '';
    return {
      env,
      risk,
      reviewRequired,
      connectorHint,
      credentialAlias,
      sandboxProfile,
      connectionDefaults,
      hostCandidate,
      instanceId,
      region,
      domain,
      username,
      port,
      useSsl,
      description: description || undefined,
    };
  }, [selectedRunbook]);

  useEffect(() => {
    if (connectConnectorType === 'winrm') {
      if (!connectUsername || connectUsername === 'root') {
        setConnectUsername('Administrator');
      }
      if (!connectPort) {
        setConnectPort(connectUseSsl ? '5986' : '5985');
      }
      if (connectInstanceId) {
        setConnectInstanceId('');
      }
      if (connectRegion) {
        setConnectRegion('');
      }
    } else if (connectConnectorType === 'ssh') {
      if (!connectUsername || connectUsername === 'Administrator') {
        setConnectUsername('root');
      }
      if (!connectPort || connectPort === '5985' || connectPort === '5986') {
        setConnectPort('22');
      }
      if (connectDomain) {
        setConnectDomain('');
      }
      if (connectUseSsl) {
        setConnectUseSsl(false);
      }
      if (connectInstanceId) {
        setConnectInstanceId('');
      }
      if (connectRegion) {
        setConnectRegion('');
      }
    } else if (connectConnectorType === 'aws_ssm') {
      if (connectHost) {
        setConnectHost('');
      }
      if (connectDomain) {
        setConnectDomain('');
      }
      if (connectPort) {
        setConnectPort('');
      }
      if (connectUseSsl) {
        setConnectUseSsl(false);
      }
      if (!connectRegion) {
        setConnectRegion('us-east-1');
      }
      if (connectUsername) {
        setConnectUsername('');
      }
      if (connectPrivateKey) {
        setConnectPrivateKey('');
      }
    } else if (
      connectConnectorType === 'network_cluster' ||
      connectConnectorType === 'network_device'
    ) {
      if (connectHost) {
        setConnectHost('');
      }
      if (connectDomain) {
        setConnectDomain('');
      }
      if (connectPort) {
        setConnectPort('');
      }
      if (connectUseSsl) {
        setConnectUseSsl(false);
      }
      if (connectInstanceId) {
        setConnectInstanceId('');
      }
      if (connectRegion) {
        setConnectRegion('');
      }
    } else if (connectConnectorType === 'azure_bastion') {
      if (connectHost) {
        setConnectHost('');
      }
      if (connectDomain) {
        setConnectDomain('');
      }
      if (connectPort) {
        setConnectPort('');
      }
      if (connectUseSsl) {
        setConnectUseSsl(false);
      }
      if (connectInstanceId) {
        setConnectInstanceId('');
      }
      if (connectRegion) {
        setConnectRegion('');
      }
    } else if (connectConnectorType === 'gcp_iap') {
      if (connectHost) {
        setConnectHost('');
      }
      if (connectDomain) {
        setConnectDomain('');
      }
      if (connectPort) {
        setConnectPort('');
      }
      if (connectUseSsl) {
        setConnectUseSsl(false);
      }
      if (connectInstanceId) {
        setConnectInstanceId('');
      }
      if (!connectRegion) {
        setConnectRegion('');
      }
    }
  }, [
    connectConnectorType,
    connectDomain,
    connectHost,
    connectPort,
    connectRegion,
    connectUseSsl,
    connectInstanceId,
    connectUsername,
    connectPrivateKey,
  ]);

  useEffect(() => {
    if (!connectModalOpen) return;
    if (!selectedRunbook || !runbookPolicy) return;
    if (lastPrefillRunbookIdRef.current === selectedRunbook.id) return;

    lastPrefillRunbookIdRef.current = selectedRunbook.id;

    const connector = runbookPolicy.connectorHint;
    setConnectConnectorType(connector);

    setConnectEnvironment(runbookPolicy.env ?? '');
    if (runbookPolicy.description) {
      setConnectDescription(runbookPolicy.description);
    } else if (selectedRunbook.description) {
      setConnectDescription(selectedRunbook.description);
    } else {
      setConnectDescription('');
    }

    if (connector === 'aws_ssm') {
      setConnectInstanceId(runbookPolicy.instanceId ?? '');
      setConnectRegion(runbookPolicy.region ?? '');
      setConnectHost('');
      setConnectDomain('');
      setConnectPort('');
      setConnectUseSsl(false);
      setSelectedClusterId('');
      setSelectedDeviceId('');
      setAzureResourceId('');
      setAzureBastionHost('');
      setAzureTargetHost('');
      setGcpProjectId('');
      setGcpZone('');
      setGcpInstanceName('');
      setGcpTargetHost('');
      setNetworkEnablePassword('');
    } else if (connector === 'network_cluster' || connector === 'network_device') {
      setConnectInstanceId('');
      setConnectRegion('');
      setConnectHost('');
      setConnectDomain('');
      setConnectPort('');
      setConnectUseSsl(false);
      const defaults = runbookPolicy.connectionDefaults ?? {};
      const clusterHint =
        defaults.cluster_id ||
        defaults.clusterId ||
        defaults.cluster?.id ||
        '';
      setSelectedClusterId(clusterHint || '');
      if (connector === 'network_device') {
        const deviceHint =
          defaults.device_id ||
          defaults.deviceId ||
          defaults.device?.id ||
          '';
        setSelectedDeviceId(deviceHint || '');
      } else {
        setSelectedDeviceId('');
      }
      setAzureResourceId('');
      setAzureBastionHost('');
      setAzureTargetHost('');
      setGcpProjectId('');
      setGcpZone('');
      setGcpInstanceName('');
      setGcpTargetHost('');
      setNetworkEnablePassword('');
    } else if (connector === 'azure_bastion') {
      setConnectInstanceId('');
      setConnectRegion('');
      setConnectHost('');
      setConnectDomain('');
      setConnectPort('');
      setConnectUseSsl(false);
      const defaults = runbookPolicy.connectionDefaults ?? {};
      setAzureResourceId(
        (defaults.resource_id || defaults.resourceId || '') as string
      );
      setAzureBastionHost(
        (defaults.bastion_host || defaults.bastionHost || '') as string
      );
      setAzureTargetHost(
        (defaults.target_host || defaults.targetHost || runbookPolicy.hostCandidate || '') as string
      );
      setSelectedClusterId('');
      setSelectedDeviceId('');
      setNetworkEnablePassword('');
      setGcpProjectId('');
      setGcpZone('');
      setGcpInstanceName('');
      setGcpTargetHost('');
    } else if (connector === 'gcp_iap') {
      setConnectInstanceId('');
      setConnectRegion('');
      setConnectHost('');
      setConnectDomain('');
      setConnectPort('');
      setConnectUseSsl(false);
      const defaults = runbookPolicy.connectionDefaults ?? {};
      setGcpProjectId(
        (defaults.project_id || defaults.projectId || '') as string
      );
      setGcpZone((defaults.zone || '') as string);
      setGcpInstanceName(
        (defaults.instance_name || defaults.instanceName || '') as string
      );
      setGcpTargetHost(
        (defaults.target_host || defaults.targetHost || runbookPolicy.hostCandidate || '') as string
      );
      setSelectedClusterId('');
      setSelectedDeviceId('');
      setNetworkEnablePassword('');
      setAzureResourceId('');
      setAzureBastionHost('');
      setAzureTargetHost('');
    } else {
      setConnectInstanceId('');
      setConnectRegion('');
      setConnectHost(runbookPolicy.hostCandidate ?? '');
      setConnectDomain(runbookPolicy.domain ?? '');
      if (runbookPolicy.port !== undefined) {
        setConnectPort(String(runbookPolicy.port));
      } else {
        setConnectPort('');
      }
      if (connector === 'winrm') {
        setConnectUseSsl(Boolean(runbookPolicy.useSsl));
      }
      setSelectedClusterId('');
      setSelectedDeviceId('');
      setNetworkEnablePassword('');
      setAzureResourceId('');
      setAzureBastionHost('');
      setAzureTargetHost('');
      setGcpProjectId('');
      setGcpZone('');
      setGcpInstanceName('');
      setGcpTargetHost('');
    }

    if (runbookPolicy.username) {
      setConnectUsername(runbookPolicy.username);
    } else if (connector === 'winrm') {
      setConnectUsername('Administrator');
    } else if (connector === 'ssh') {
      setConnectUsername('root');
    } else {
      setConnectUsername('');
    }

    const alias =
      runbookPolicy.credentialAlias ?? defaultAliasForConnector(connector);
    setConnectCredentialAlias(alias ?? '');

    setConnectPrivateKey(
      typeof runbookPolicy.connectionDefaults?.private_key === 'string'
        ? runbookPolicy.connectionDefaults.private_key
        : ''
    );
    setConnectPassword('');
  }, [connectModalOpen, selectedRunbook, runbookPolicy]);

  useEffect(() => {
    if (connectConnectorType !== 'winrm') return;
    if (!connectPort || connectPort === '5985' || connectPort === '5986') {
      setConnectPort(connectUseSsl ? '5986' : '5985');
    }
  }, [connectConnectorType, connectUseSsl, connectPort]);

  const connectionLabel = useMemo(() => {
    if (!workspaceEnabled) return 'disabled';
    return connected ? 'connected' : 'connecting...';
  }, [connected, workspaceEnabled]);

  const normalizedStatus = (activeSession?.status || '').toLowerCase();

  const connectionInfo: ConnectionInfo = useMemo(() => {
    const info: ConnectionInfo = {
      sandboxProfile: activeSession?.sandbox_profile,
    };

    if (activeSession?.connection) {
      const sessionConn = activeSession.connection as Record<string, any>;
      const target = (sessionConn.target as Record<string, any>) || {};
      const instanceId =
        sessionConn.instance_id ??
        (typeof sessionConn === 'object' && sessionConn.connection
          ? sessionConn.connection.instance_id
          : undefined) ??
        target.instance_id;
      info.host = sessionConn.host ?? target.host ?? instanceId ?? info.host;
      info.environment = sessionConn.environment ?? target.environment ?? info.environment;
      info.service = sessionConn.service ?? target.service ?? info.service;
      info.connector =
        sessionConn.connector_type ?? sessionConn.connector ?? info.connector;
      info.credentialSource =
        sessionConn.credential_source ?? info.credentialSource;
      const clusterDetails =
        sessionConn.cluster ??
        sessionConn.connection?.cluster ??
        sessionConn.metadata?.cluster;
      if (clusterDetails) {
        info.clusterId =
          clusterDetails.id ??
          clusterDetails.cluster_id ??
          clusterDetails.name ??
          info.clusterId;
      }
      const deviceDetails =
        sessionConn.device ??
        sessionConn.connection?.device ??
        sessionConn.metadata?.device ??
        target.device;
      if (deviceDetails) {
        info.deviceId =
          deviceDetails.id ??
          deviceDetails.device_id ??
          deviceDetails.name ??
          info.deviceId;
      }
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
      const instanceId =
        target.instance_id ??
        metadata.instance_id ??
        assignmentPayload.instance_id;
      info.host = target.host ?? metadata.host ?? instanceId ?? info.host;
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
      const clusterDetails =
        metadata.cluster ??
        metadata.connection?.cluster ??
        assignmentPayload.cluster;
      if (clusterDetails) {
        info.clusterId =
          clusterDetails.id ??
          clusterDetails.cluster_id ??
          clusterDetails.name ??
          info.clusterId;
      }
      const deviceDetails =
        metadata.device ??
        metadata.connection?.device ??
        target.device;
      if (deviceDetails) {
        info.deviceId =
          deviceDetails.id ??
          deviceDetails.device_id ??
          deviceDetails.name ??
          info.deviceId;
      }
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

    const clusterEvent = reversedEvents.find(
      (evt) => evt.event === 'agent.cluster_established'
    );
    if (clusterEvent) {
      info.clusterId =
        info.clusterId ?? clusterEvent.payload?.cluster_id ?? clusterEvent.payload?.cluster?.id;
      info.workerId = info.workerId ?? clusterEvent.payload?.worker_id;
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

      if (eventName === 'agent.cluster_established') {
        const clusterId = payload.cluster_id ?? payload.metadata?.cluster_id ?? 'cluster';
        pushLine({
          key: `${baseKey}:cluster`,
          text: `Cluster session ready: ${clusterId}`,
          tone: 'info',
          timestamp: timestampLabel,
        });
        return;
      }

      if (eventName === 'agent.connection_failed') {
        pushLine({
          key: `${baseKey}:connection_failed`,
          text: `Connection failed: ${
            payload.reason || payload.error || 'unknown error'
          }`,
          tone: 'error',
          timestamp: timestampLabel,
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
        const promptMetaParts = [
          payload.shell ? `shell: ${payload.shell}` : undefined,
          payload.run_as ? `run as ${payload.run_as}` : undefined,
          reasonText ? `reason: ${reasonText}` : undefined,
        ];
        const promptMeta =
          promptMetaParts.filter(Boolean).join(' · ') || undefined;
        pushLine({
          key: `${baseKey}:prompt`,
          text: `> ${commandText}`,
          tone: 'prompt',
          timestamp: timestampLabel,
          meta: promptMeta,
        });
        return;
      }

      if (eventName === 'session.command.completed' || eventName === 'session.command.failed') {
        const streamId = payload.stream_id ?? evt.stream_id ?? baseKey;
        const request = streamId ? commandRequests.get(streamId) : undefined;
        let durationMs =
          typeof payload.duration_ms === 'number' ? payload.duration_ms : undefined;
        if (
          !durationMs &&
          request?.timestamp &&
          numericTimestamp &&
          !Number.isNaN(numericTimestamp)
        ) {
          durationMs = Math.max(0, numericTimestamp - request.timestamp);
        }
        const metaParts = [
          formatShortDuration(durationMs),
          payload.exit_code !== undefined && payload.exit_code !== null
            ? `exit ${payload.exit_code}`
            : undefined,
          payload.retry_count ? `retries ${payload.retry_count}` : undefined,
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

      if (eventName === 'execution.step.started') {
        const stepNumber =
          payload.step?.step_number ?? payload.step_number ?? evt.step_number;
        const commandText = payload.step?.command ?? payload.command;
        pushLine({
          key: `${baseKey}:step-start`,
          text: `▶ Step ${stepNumber ?? '—'} started${
            commandText ? `: ${commandText}` : ''
          }`,
          tone: 'info',
          timestamp: timestampLabel,
        });
        return;
      }

      if (eventName === 'execution.step.output') {
        const rawOutput =
          payload.output ?? payload.stdout ?? payload.message ?? payload.detail;
        if (rawOutput) {
          const outputText =
            typeof rawOutput === 'string'
              ? rawOutput
              : JSON.stringify(rawOutput, null, 2);
          const segments = outputText.split(/\r?\n/);
          segments.forEach((segment, idx) => {
            if (segment.trim().length === 0) return;
            pushLine({
              key: `${baseKey}:step-output:${idx}`,
              text: segment,
              tone: 'output',
              timestamp: idx === 0 ? timestampLabel : undefined,
            });
          });
        }
        return;
      }

      if (eventName === 'execution.step.completed') {
        const stepNumber =
          payload.step?.step_number ?? payload.step_number ?? evt.step_number;
        const success = payload.success !== false;
        const stepDuration =
          typeof payload.duration_ms === 'number'
            ? payload.duration_ms
            : undefined;
        const metaParts = [
          formatShortDuration(stepDuration),
          payload.exit_code !== undefined && payload.exit_code !== null
            ? `exit ${payload.exit_code}`
            : undefined,
          payload.retry_count ? `retries ${payload.retry_count}` : undefined,
        ];
        const meta = metaParts.filter(Boolean).join(' · ') || undefined;
        pushLine({
          key: `${baseKey}:step-completed`,
          text: `${success ? '✔' : '✖'} Step ${stepNumber ?? '—'} ${
            success ? 'completed' : 'failed'
          }`,
          tone: success ? 'success' : 'error',
          timestamp: timestampLabel,
          meta,
        });
        const detailText =
          typeof payload.detail === 'string'
            ? payload.detail
            : payload.detail
            ? JSON.stringify(payload.detail, null, 2)
            : undefined;
        if (detailText) {
          detailText.split(/\r?\n/).forEach((segment: string, idx: number) => {
            if (segment.trim().length === 0) return;
            pushLine({
              key: `${baseKey}:step-detail:${idx}`,
              text: segment,
              tone: success ? 'info' : 'error',
              timestamp: idx === 0 ? timestampLabel : undefined,
            });
          });
        }
        return;
      }
    });

    return lines;
  }, [eventHistory]);

  useEffect(() => {
    if (!consoleRef.current) return;
    consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
  }, [consoleLines]);

  const commandConsoleLabel = useMemo(() => {
    const connector = connectionInfo.connector?.toLowerCase();
    if (connector === 'winrm') return 'PowerShell Console';
    if (connector === 'ssh') return 'SSH Console';
    if (connector === 'aws_ssm') return 'SSM Session Console';
    if (connector === 'network_cluster') return 'Network Cluster Console';
    if (connector === 'network_device') return 'Network Device Console';
    if (connector === 'azure_bastion') return 'Azure Bastion Console';
    if (connector === 'gcp_iap') return 'GCP IAP Console';
    return 'Manual Command Console';
  }, [connectionInfo.connector]);

  const commandPlaceholder = useMemo(() => {
    const connector = connectionInfo.connector?.toLowerCase();
    if (connector === 'winrm') return 'Get-Service';
    if (connector === 'ssh') return 'sudo systemctl restart app.service';
    if (connector === 'aws_ssm') return 'sudo tail -n 100 /var/log/syslog';
    if (connector === 'network_cluster') return 'show fabric status';
    if (connector === 'network_device') return 'show interfaces status';
    if (connector === 'azure_bastion') return 'sudo systemctl status nginx';
    if (connector === 'gcp_iap') return 'journalctl -n 100';
    return 'Enter command';
  }, [connectionInfo.connector]);

  const isWinRM = connectConnectorType === 'winrm';
  const isSSH = connectConnectorType === 'ssh';
  const isSsm = connectConnectorType === 'aws_ssm';
  const isNetworkCluster = connectConnectorType === 'network_cluster';
  const isNetworkDevice = connectConnectorType === 'network_device';
  const isAzureBastion = connectConnectorType === 'azure_bastion';
  const isGcpIap = connectConnectorType === 'gcp_iap';
  const supportsUsername = [
    'winrm',
    'ssh',
    'aws_ssm',
    'network_cluster',
    'network_device',
    'azure_bastion',
    'gcp_iap',
  ].includes(connectConnectorType);
  const supportsPassword = [
    'winrm',
    'ssh',
    'network_cluster',
    'network_device',
    'azure_bastion',
    'gcp_iap',
    'aws_ssm',
  ].includes(connectConnectorType);
  const usernamePlaceholder = isWinRM
    ? 'Administrator'
    : isSSH
    ? 'root'
    : isNetworkCluster
    ? 'netops'
    : isNetworkDevice
    ? 'device-admin'
    : isAzureBastion || isGcpIap
    ? 'ops-user'
    : isSsm
    ? 'ec2-user (optional)'
    : 'operator';

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

    if (policy?.risk && policy.risk.toLowerCase() === 'high') {
      const confirmed = window.confirm(
        'This runbook is marked as HIGH risk. Confirm that you have approval to proceed.'
      );
      if (!confirmed) {
        setConnectSubmitting(false);
        setConnectError('Execution cancelled. Approval required for high-risk runbooks.');
        return;
      }
    }

    const metadata: Record<string, any> = {
      connector_type: connectorType,
    };

    if (environment) {
      metadata.environment = environment;
    }

    const credentialsPayload: Record<string, string> = {};

    if (connectorType === 'winrm') {
      const username = connectUsername.trim() || 'Administrator';
      const password = connectPassword || undefined;
      const domain = connectDomain.trim() || undefined;
      const useSsl = connectUseSsl;
      const parsedPort = Number.parseInt(connectPort, 10);
      const port =
        Number.isFinite(parsedPort) && parsedPort > 0
          ? parsedPort
          : useSsl
          ? 5986
          : 5985;
      metadata.shell = 'powershell';
      metadata.target = {
        host,
        service: 'windows_server',
        ...(environment ? { environment } : {}),
      };
      metadata.connection = {
        type: 'winrm',
        host,
        port,
        transport: useSsl ? 'https' : 'http',
        shell: 'powershell',
        use_ssl: useSsl,
      };
      if (username) {
        credentialsPayload.username = username;
      }
      if (domain) {
        credentialsPayload.domain = domain;
      }
      if (password) {
        credentialsPayload.password = password;
      }
    } else if (connectorType === 'ssh') {
      const username = connectUsername.trim() || 'root';
      const password = connectPassword || undefined;
      const privateKey = connectPrivateKey.trim() || undefined;
      const parsedPort = Number.parseInt(connectPort, 10);
      const port =
        Number.isFinite(parsedPort) && parsedPort > 0 ? parsedPort : 22;
      metadata.shell = 'bash';
      metadata.target = {
        host,
        service: 'linux_server',
        ...(environment ? { environment } : {}),
      };
      metadata.connection = {
        type: 'ssh',
        host,
        port,
        shell: 'bash',
        username,
      };
      if (username) {
        credentialsPayload.username = username;
      }
      if (password) {
        credentialsPayload.password = password;
      }
      if (privateKey) {
        credentialsPayload.private_key = privateKey;
      }
    } else if (connectorType === 'aws_ssm') {
      const instanceId = connectInstanceId.trim();
      const region = connectRegion.trim();
      if (!instanceId) {
        setConnectSubmitting(false);
        setConnectError('Instance ID is required for AWS SSM sessions.');
        return;
      }
      if (!region) {
        setConnectSubmitting(false);
        setConnectError('Region is required for AWS SSM sessions.');
        return;
      }
      metadata.shell = 'bash';
      metadata.target = {
        instance_id: instanceId,
        region,
        service: 'aws_ec2',
        ...(environment ? { environment } : {}),
      };
      metadata.connection = {
        type: 'aws_ssm',
        instance_id: instanceId,
        region,
      };
      if (connectUsername.trim()) {
        credentialsPayload.username = connectUsername.trim();
      }
      if (connectPassword) {
        credentialsPayload.password = connectPassword;
      }
    } else if (connectorType === 'network_cluster') {
      if (!selectedClusterId) {
        setConnectSubmitting(false);
        setConnectError('Select a network cluster to connect.');
        return;
      }
      const cluster = networkClusters.find((item) => item.id === selectedClusterId);
      if (!cluster) {
        setConnectSubmitting(false);
        setConnectError('Selected cluster details unavailable.');
        return;
      }
      metadata.shell = 'cli';
      metadata.cluster = cluster;
      metadata.connection = {
        type: 'network_cluster',
        cluster,
        host: cluster.management_host,
      };
      metadata.target = {
        cluster_id: cluster.id,
        host: cluster.management_host,
        service: 'network_cluster',
        vendor: cluster.vendor,
      };
      if (connectUsername.trim()) {
        credentialsPayload.username = connectUsername.trim();
      }
      if (connectPassword) {
        credentialsPayload.password = connectPassword;
      }
    } else if (connectorType === 'network_device') {
      if (!selectedClusterId) {
        setConnectSubmitting(false);
        setConnectError('Select the parent network cluster.');
        return;
      }
      if (!selectedDeviceId) {
        setConnectSubmitting(false);
        setConnectError('Select a network device to connect.');
        return;
      }
      const cluster = networkClusters.find((item) => item.id === selectedClusterId);
      const device = clusterDevices.find((item) => item.id === selectedDeviceId);
      if (!cluster || !device) {
        setConnectSubmitting(false);
        setConnectError('Unable to resolve cluster/device metadata.');
        return;
      }
      metadata.shell = 'cli';
      metadata.cluster = cluster;
      metadata.device = device;
      metadata.connection = {
        type: 'network_device',
        cluster,
        device,
        host: device.mgmt_ip ?? device.id,
      };
      metadata.target = {
        cluster_id: cluster.id,
        device_id: device.id,
        host: device.mgmt_ip ?? device.id,
        service: 'network_device',
        vendor: device.vendor,
      };
      if (connectUsername.trim()) {
        credentialsPayload.username = connectUsername.trim();
      }
      if (connectPassword) {
        credentialsPayload.password = connectPassword;
      }
      if (networkEnablePassword.trim()) {
        credentialsPayload.enable_password = networkEnablePassword.trim();
      }
    } else if (connectorType === 'azure_bastion') {
      const resourceId = azureResourceId.trim();
      const bastionHost = azureBastionHost.trim();
      const targetHost = azureTargetHost.trim();
      if (!resourceId || !bastionHost || !targetHost) {
        setConnectSubmitting(false);
        setConnectError(
          'Azure Bastion requires resource ID, bastion host, and target host.'
        );
        return;
      }
      metadata.shell = 'bash';
      metadata.connection = {
        type: 'azure_bastion',
        resource_id: resourceId,
        bastion_host: bastionHost,
        target_host: targetHost,
        host: targetHost,
      };
      metadata.target = {
        host: targetHost,
        service: 'azure_vm',
        environment,
      };
      if (connectUsername.trim()) {
        credentialsPayload.username = connectUsername.trim();
      }
      if (connectPassword) {
        credentialsPayload.password = connectPassword;
      }
    } else if (connectorType === 'gcp_iap') {
      const projectId = gcpProjectId.trim();
      const zone = gcpZone.trim();
      const instanceName = gcpInstanceName.trim();
      if (!projectId || !zone || !instanceName) {
        setConnectSubmitting(false);
        setConnectError(
          'GCP IAP requires project ID, zone, and instance name.'
        );
        return;
      }
      metadata.shell = 'bash';
      metadata.connection = {
        type: 'gcp_iap',
        project_id: projectId,
        zone,
        instance_name: instanceName,
        target_host: gcpTargetHost.trim() || undefined,
        host: gcpTargetHost.trim() || undefined,
      };
      metadata.target = {
        project_id: projectId,
        zone,
        instance_name: instanceName,
        host: gcpTargetHost.trim() || undefined,
        service: 'gcp_compute',
        environment,
      };
      if (connectUsername.trim()) {
        credentialsPayload.username = connectUsername.trim();
      }
      if (connectPassword) {
        credentialsPayload.password = connectPassword;
      }
    }

    const credentialAlias =
      connectCredentialAlias.trim() || policy?.credentialAlias || undefined;
    if (credentialAlias) {
      metadata.credential_source = `alias:${credentialAlias}`;
    } else if (Object.keys(credentialsPayload).length > 0) {
      metadata.credential_source = 'inline';
    }

    if (!credentialAlias && Object.keys(credentialsPayload).length > 0) {
      metadata.credentials = credentialsPayload;
    }

    if (metadata.connection && metadata.credential_source) {
      metadata.connection.credential_source = metadata.credential_source;
    }

    if (policy?.env && !metadata.environment) {
      metadata.environment = policy.env;
    }

    metadata.sandbox_profile = policy?.sandboxProfile ?? metadata.sandbox_profile ?? 'default';

    if (currentRunbook.metadata?.runbook_spec) {
      metadata.runbook_spec = currentRunbook.metadata.runbook_spec;
    }

    if (
      currentRunbook.metadata?.runbook_spec?.service &&
      !metadata.service
    ) {
      metadata.service = currentRunbook.metadata.runbook_spec.service;
    }

    metadata.runbook_context = {
      id: connectRunbookId,
      title: currentRunbook.title,
      env: metadata.environment || null,
      risk: policy?.risk || null,
    };

    const policyPayload: Record<string, any> = {};
    if (policy?.risk) {
      policyPayload.risk = policy.risk;
    }
    if (policy?.reviewRequired) {
      policyPayload.review_required = true;
    }
    if (Object.keys(policyPayload).length > 0) {
      metadata.policy = policyPayload;
    }

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

  const transcriptStyles: Record<
    TranscriptVariant,
    { container: string; icon: string; title: string }
  > = {
    info: {
      container: 'border-blue-200 bg-blue-50',
      icon: 'text-blue-600',
      title: 'text-blue-800',
    },
    success: {
      container: 'border-green-200 bg-green-50',
      icon: 'text-green-600',
      title: 'text-green-800',
    },
    warning: {
      container: 'border-amber-200 bg-amber-50',
      icon: 'text-amber-600',
      title: 'text-amber-800',
    },
    error: {
      container: 'border-red-200 bg-red-50',
      icon: 'text-red-600',
      title: 'text-red-800',
    },
    neutral: {
      container: 'border-gray-200 bg-gray-50',
      icon: 'text-gray-500',
      title: 'text-gray-800',
    },
  };

  const consoleToneStyles: Record<ConsoleLineTone, string> = {
    prompt: 'text-sky-300',
    success: 'text-emerald-300',
    error: 'text-red-300',
    warning: 'text-amber-300',
    info: 'text-cyan-300',
    output: 'text-gray-100',
  };

  const riskBadgeStyles: Record<string, string> = {
    high: 'bg-red-100 text-red-700',
    medium: 'bg-amber-100 text-amber-700',
    low: 'bg-green-100 text-green-700',
    default: 'bg-gray-100 text-gray-700',
  };

  const buildTranscriptEntry = (evt: ExecutionEventRecord): TranscriptEntry => {
    const eventName = (evt.event || '').toLowerCase();
    const payload = evt.payload ?? {};
    const stepNumber =
      evt.step_number ??
      payload?.step_number ??
      payload?.step?.step_number ??
      payload?.step?.number;

    const metaFromPairs = (
      pairs: Array<[string, string | number | boolean | undefined | null | Record<string, any>]>
    ) =>
      pairs
        .filter(([, value]) => value !== undefined && value !== null && value !== '')
        .map(([label, value]) => {
          if (typeof value === 'string') {
            return { label, value };
          }
          if (typeof value === 'number' || typeof value === 'boolean') {
            return { label, value: String(value) };
          }
          return { label, value: JSON.stringify(value) };
        });

    const entry: TranscriptEntry = {
      title: evt.event || 'Event',
      summary: undefined,
      detail: undefined,
      meta: undefined,
      variant: 'neutral',
      icon: InformationCircleIcon,
      timestamp: evt.created_at,
      raw: undefined,
    };

    const toDetailString = (value: any) => {
      if (value === null || value === undefined) return undefined;
      if (typeof value === 'string') return value;
      return JSON.stringify(value, null, 2);
    };

    if (eventName === 'session.created') {
      entry.title = 'Session created';
      entry.summary = `Runbook ${payload.runbook_id ?? ''} queued for ticket ${
        payload.ticket_id ?? '—'
      }`;
      entry.variant = 'info';
      entry.icon = BoltIcon;
      entry.meta = metaFromPairs([
        ['Status', payload.status],
        ['Tenant', payload.tenant_id],
      ]);
    } else if (eventName === 'session.queued') {
      entry.title = 'Session queued';
      entry.summary = `Assignment scheduled (stream ${payload.stream_id ?? '—'})`;
      entry.variant = 'info';
      entry.icon = BoltIcon;
      entry.meta = metaFromPairs([
        ['Status', payload.status],
        ['Stream', payload.stream_id],
      ]);
    } else if (eventName === 'session.policy') {
      entry.title = 'Sandbox policy applied';
      entry.summary = `Profile ${payload.profile ?? 'default'} with SLA ${
        payload.sla_minutes ?? '—'
      } min`;
      entry.variant = 'info';
      entry.icon = ServerIcon;
    } else if (eventName === 'approval.policy') {
      entry.title = 'Approval policy enforced';
      entry.summary = `Mode ${payload.mode ?? 'per_step'} (SLA ${
        payload.sla_minutes ?? '—'
      } min)`;
      entry.variant = 'warning';
      entry.icon = ExclamationTriangleIcon;
    } else if (eventName === 'worker.assignment_received') {
      entry.title = 'Worker assignment received';
      entry.summary = `Worker ${payload.worker_id ?? '—'} accepted the job`;
      entry.variant = 'info';
      entry.icon = ServerIcon;
      entry.meta = metaFromPairs([
        ['Assignment', payload.assignment_id],
        ['Step count', payload.payload?.steps?.length],
      ]);
    } else if (eventName === 'worker.assignment_acknowledged') {
      entry.title = 'Worker assignment acknowledged';
      entry.summary = `Worker ${payload.worker_id ?? '—'} acknowledged assignment ${
        payload.assignment_id ?? '—'
      }`;
      entry.variant = 'success';
      entry.icon = CheckCircleIcon;
    } else if (eventName === 'worker.assignment_empty') {
      entry.title = 'No executable steps';
      entry.summary = `Worker ${payload.worker_id ?? '—'} reported no steps to run.`;
      entry.variant = 'warning';
      entry.icon = ExclamationTriangleIcon;
    } else if (eventName === 'agent.connection_established') {
      const host = payload.host ?? 'target host';
      entry.title = 'Connection established';
      entry.summary = `Worker ${payload.worker_id ?? '—'} connected to ${host}.`;
      entry.variant = 'success';
      entry.icon = ServerIcon;
      entry.meta = metaFromPairs([
        ['Connector', payload.connector_type],
        ['Environment', payload.environment],
        ['Credential source', payload.credential_source],
      ]);
    } else if (eventName === 'agent.cluster_established') {
      entry.title = 'Cluster session ready';
      entry.summary = `Cluster ${payload.cluster_id ?? '—'} connection prepared.`;
      entry.variant = 'info';
      entry.icon = ServerIcon;
      entry.meta = metaFromPairs([
        ['Worker', payload.worker_id],
        ['Cluster', payload.cluster_id],
      ]);
    } else if (eventName === 'execution.step.started') {
      entry.title = `Step ${stepNumber ?? '—'} started`;
      const commandText =
        payload.step?.command ||
        payload.command ||
        payload?.step?.description ||
        'Executing step';
      entry.summary = commandText;
      entry.variant = 'info';
      entry.icon = PlayIcon;
      entry.meta = metaFromPairs([
        ['Worker', payload.worker_id],
        ['Sandbox', payload.step?.sandbox_profile],
        ['Blast radius', payload.step?.blast_radius],
      ]);
    } else if (eventName === 'execution.step.output') {
      entry.title = `Step ${stepNumber ?? '—'} output`;
      entry.variant = 'neutral';
      entry.icon = CommandLineIcon;
      entry.detail =
        toDetailString(payload.output) ??
        toDetailString(payload.message) ??
        toDetailString(payload.stdout);
      entry.meta = metaFromPairs([['Worker', payload.worker_id]]);
    } else if (eventName === 'execution.step.completed') {
      const success = payload.success !== false;
      entry.title = `Step ${stepNumber ?? '—'} ${success ? 'completed' : 'failed'}`;
      entry.summary = success
        ? `Worker ${payload.worker_id ?? '—'} marked step successful.`
        : `Worker ${payload.worker_id ?? '—'} reported failure.`;
      entry.variant = success ? 'success' : 'error';
      entry.icon = success ? CheckCircleIcon : XCircleIcon;
      entry.meta = metaFromPairs([
        ['Worker', payload.worker_id],
        ['Success', success],
        ['Duration (ms)', payload.duration_ms],
        ['Retries', payload.retry_count],
      ]);
      entry.detail = toDetailString(payload.detail);
    } else if (eventName === 'session.command.requested') {
      const commandText =
        typeof payload.command === 'string'
          ? payload.command
          : toDetailString(payload.command);
      const shortSummary =
        typeof payload.reason === 'string' && payload.reason.length > 0
          ? payload.reason
          : typeof commandText === 'string' && commandText.length > 0
          ? commandText.length > 80
            ? `${commandText.slice(0, 77)}…`
            : commandText
          : 'Manual command submitted.';
      entry.title = 'Manual command queued';
      entry.summary = shortSummary;
      entry.detail =
        typeof commandText === 'string'
          ? commandText
          : toDetailString(payload.command) ?? undefined;
      entry.variant = 'info';
      entry.icon = CommandLineIcon;
      entry.meta = metaFromPairs([
        ['Shell', payload.shell],
        ['Run as', payload.run_as],
        ['Stream', payload.stream_id],
        ['User', payload.user_id],
      ]);
    } else if (eventName === 'session.command.completed') {
      entry.title = 'Manual command completed';
      entry.summary = payload.message || 'Manual command finished executing.';
      entry.detail = toDetailString(payload.output);
      entry.variant = 'success';
      entry.icon = CheckCircleIcon;
      entry.meta = metaFromPairs([
        ['Exit code', payload.exit_code],
        ['Duration (ms)', payload.duration_ms],
        ['Retries', payload.retry_count],
      ]);
    } else if (eventName === 'session.command.failed') {
      entry.title = 'Manual command failed';
      entry.summary = payload.error || 'Manual command reported an error.';
      entry.detail = toDetailString(payload.output ?? payload.stderr);
      entry.variant = 'error';
      entry.icon = XCircleIcon;
      entry.meta = metaFromPairs([
        ['Exit code', payload.exit_code],
        ['Stream', payload.stream_id],
        ['Duration (ms)', payload.duration_ms],
        ['Retries', payload.retry_count],
      ]);
    } else if (eventName === 'session.paused') {
      entry.title = 'Session paused';
      entry.summary = payload.reason || 'Session paused by operator.';
      entry.variant = 'warning';
      entry.icon = ExclamationTriangleIcon;
      entry.meta = metaFromPairs([
        ['Previous status', payload.previous_status],
        ['User', payload.user_id],
      ]);
    } else if (eventName === 'session.resumed') {
      entry.title = 'Session resumed';
      entry.summary = payload.reason || 'Session resumed.';
      entry.variant = 'success';
      entry.icon = CheckCircleIcon;
      entry.meta = metaFromPairs([
        ['Previous status', payload.previous_status],
        ['User', payload.user_id],
      ]);
    } else if (eventName === 'session.rollback_requested') {
      entry.title = 'Rollback requested';
      entry.summary = payload.reason || 'Rollback flow initiated.';
      entry.variant = 'warning';
      entry.icon = ExclamationTriangleIcon;
      entry.meta = metaFromPairs([
        ['Previous status', payload.previous_status],
        ['User', payload.user_id],
        ['Command stream', payload.command_stream_id],
      ]);
    } else if (eventName === 'session.worker_complete') {
      entry.title = 'Worker completed session';
      entry.summary = `Worker ${payload.worker_id ?? '—'} finished assigned steps.`;
      entry.variant = 'success';
      entry.icon = CheckCircleIcon;
    } else if (eventName === 'session.completed') {
      entry.title = 'Session completed';
      entry.summary = `Execution finished with status ${payload.status ?? 'completed'}.`;
      entry.variant = 'success';
      entry.icon = CheckCircleIcon;
    } else if (eventName === 'session.failed') {
      entry.title = 'Session failed';
      entry.summary = payload.reason || 'Execution terminated with errors.';
      entry.variant = 'error';
      entry.icon = XCircleIcon;
      entry.detail = toDetailString(payload);
    } else {
      entry.summary = payload.message || undefined;
      entry.raw = JSON.stringify(payload, null, 2);
    }

    if (!entry.meta || entry.meta.length === 0) {
      entry.meta = undefined;
    }

    if (!entry.detail && entry.raw && entry.raw.length > 400) {
      // For large payloads avoid duplicating detail text
      entry.detail = undefined;
    }

    if (!entry.raw && entry.summary && entry.summary.length > 0 && !payload?.message) {
      entry.raw = undefined;
    } else if (!entry.raw && (!entry.summary || entry.summary.length === 0)) {
      entry.raw = JSON.stringify(payload, null, 2);
    }

    return entry;
  };

  if (!workspaceEnabled) {
    return (
      <div className="p-6 bg-white border border-gray-200 rounded-2xl shadow-sm">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Agent Workspace disabled
        </h2>
        <p className="text-sm text-gray-600">
          Set <code>NEXT_PUBLIC_AGENT_WORKSPACE_ENABLED=true</code> to enable
          the live execution workspace.
        </p>
      </div>
    );
  }

  return (
    <>
      {connectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 p-4">
          <div className="w-full max-w-3xl overflow-hidden rounded-2xl bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
              <div>
                <h3 className="text-base font-semibold text-gray-900">
                  Connect to Configuration Item
                </h3>
                <p className="text-xs text-gray-500">
                  Launch a remote session across servers, network clusters/devices, or cloud connectors to execute runbook steps.
                </p>
              </div>
              <button
                type="button"
                disabled={connectSubmitting}
                onClick={closeConnectModal}
                className="rounded-full p-1 text-gray-400 transition hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:text-gray-300"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
            <form
              onSubmit={(event: FormEvent<HTMLFormElement>) => {
                event.preventDefault();
                void handleConnectSubmit();
              }}
            >
              <div className="px-6 py-5 space-y-5">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div className="md:col-span-2">
                    <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                      Connector
                    </label>
                    <select
                      value={connectConnectorType}
                      onChange={(event) =>
                        setConnectConnectorType(event.target.value as ConnectorType)
                      }
                      disabled={connectSubmitting}
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                    >
                      <option value="winrm">Windows (WinRM)</option>
                      <option value="ssh">Linux / Unix (SSH)</option>
                      <option value="aws_ssm">AWS SSM Session</option>
                      <option value="network_cluster">Network Cluster (Controller)</option>
                      <option value="network_device">Network Device (via Cluster)</option>
                      <option value="azure_bastion">Azure Bastion</option>
                      <option value="gcp_iap">GCP IAP Tunnel</option>
                    </select>
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                      Runbook
                    </label>
                    <select
                      value={connectRunbookId ?? ''}
                      onChange={(event) => {
                        const value = event.target.value;
                        setConnectRunbookId(value ? Number(value) : null);
                      }}
                      disabled={runbooksLoading || connectSubmitting}
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                    >
                      <option value="" disabled>
                        {runbooksLoading
                          ? 'Loading runbooks…'
                          : 'Select a runbook to pair with this session'}
                      </option>
                      {sortedRunbooks.map((runbook) => (
                        <option key={runbook.id} value={runbook.id}>
                          {runbook.title}
                        </option>
                      ))}
                    </select>
                    {selectedRunbook?.description && (
                      <p className="mt-1 text-xs text-gray-500">
                        {selectedRunbook.description}
                      </p>
                    )}
                    {runbookPolicy && (
                      <div className="mt-3 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-600">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-gray-700">
                            Policy &amp; Context
                          </span>
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${
                              riskBadgeStyles[
                                (runbookPolicy.risk || '').toLowerCase() || 'default'
                              ] || riskBadgeStyles.default
                            }`}
                          >
                            Risk:{' '}
                            {runbookPolicy.risk
                              ? runbookPolicy.risk.toUpperCase()
                              : 'N/A'}
                          </span>
                        </div>
                        <dl className="mt-2 grid grid-cols-1 gap-y-1 sm:grid-cols-2 sm:gap-x-4">
                          <div>
                            <dt className="text-gray-500">Environment</dt>
                            <dd className="text-gray-700 font-medium">
                              {runbookPolicy.env || '—'}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-gray-500">Sandbox Profile</dt>
                            <dd className="text-gray-700 font-medium">
                              {runbookPolicy.sandboxProfile}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-gray-500">Approval Required</dt>
                            <dd className="text-gray-700 font-medium">
                              {runbookPolicy.reviewRequired ? 'Yes' : 'No'}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-gray-500">Suggested Connector</dt>
                            <dd className="text-gray-700 font-medium">
                              {runbookPolicy.connectorHint.toUpperCase()}
                            </dd>
                          </div>
                          {runbookPolicy.credentialAlias && (
                            <div>
                              <dt className="text-gray-500">Credential Alias</dt>
                              <dd className="text-gray-700 font-medium">
                                {runbookPolicy.credentialAlias}
                              </dd>
                            </div>
                          )}
                        </dl>
                        {runbookPolicy.reviewRequired && (
                          <div className="mt-2 rounded-md border border-red-200 bg-red-50 px-2 py-1 text-[11px] text-red-700">
                            Approval required before executing this runbook.
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  {(isWinRM || isSSH) && (
                    <div>
                      <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                        Target Host
                      </label>
                      <input
                        type="text"
                        autoFocus
                        value={connectHost}
                        onChange={(event) => setConnectHost(event.target.value)}
                        disabled={connectSubmitting}
                        placeholder="server01.corp.local"
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                      />
                    </div>
                  )}
                  {isSsm && (
                    <div>
                      <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                        Instance ID
                      </label>
                      <input
                        type="text"
                        value={connectInstanceId}
                        onChange={(event) => setConnectInstanceId(event.target.value)}
                        disabled={connectSubmitting}
                        placeholder="i-0a1b2c3d4e5f6g7h"
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                      />
                    </div>
                  )}
                  <div>
                    <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                      Environment
                    </label>
                    <input
                      type="text"
                      value={connectEnvironment}
                      onChange={(event) => setConnectEnvironment(event.target.value)}
                      disabled={connectSubmitting}
                      placeholder="production"
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                    />
                  </div>
                  {(isNetworkCluster || isNetworkDevice) && (
                    <div className="md:col-span-2">
                      <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                        Network Cluster
                      </label>
                      <select
                        value={selectedClusterId}
                        onChange={(event) => setSelectedClusterId(event.target.value)}
                        disabled={connectSubmitting || networkClustersLoading}
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                      >
                        <option value="">
                          {networkClustersLoading
                            ? 'Loading clusters…'
                            : 'Select network cluster'}
                        </option>
                        {networkClusters.map((cluster) => (
                          <option key={cluster.id} value={cluster.id}>
                            {cluster.name} ({cluster.vendor ?? 'vendor unknown'})
                          </option>
                        ))}
                      </select>
                      {networkClusterError && (
                        <p className="mt-1 text-xs text-red-600">
                          {networkClusterError}
                        </p>
                      )}
                    </div>
                  )}
                  {isNetworkDevice && (
                    <>
                      <div className="md:col-span-2">
                        <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                          Network Device
                        </label>
                        <select
                          value={selectedDeviceId}
                          onChange={(event) => setSelectedDeviceId(event.target.value)}
                          disabled={
                            connectSubmitting ||
                            clusterDevicesLoading ||
                            !selectedClusterId
                          }
                          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                        >
                          <option value="">
                            {clusterDevicesLoading
                              ? 'Loading devices…'
                              : 'Select network device'}
                          </option>
                          {clusterDevices.map((device) => (
                            <option key={device.id} value={device.id}>
                              {device.name} ({device.mgmt_ip ?? 'IP unknown'})
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                          Enable Password (optional)
                        </label>
                        <input
                          type="password"
                          value={networkEnablePassword}
                          onChange={(event) =>
                            setNetworkEnablePassword(event.target.value)
                          }
                          disabled={connectSubmitting}
                          placeholder="••••••••"
                          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                        />
                      </div>
                    </>
                  )}
                  {isAzureBastion && (
                    <>
                      <div className="md:col-span-2">
                        <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                          Target Resource ID
                        </label>
                        <input
                          type="text"
                          value={azureResourceId}
                          onChange={(event) => setAzureResourceId(event.target.value)}
                          disabled={connectSubmitting}
                          placeholder="/subscriptions/.../resourceGroups/.../providers/Microsoft.Compute/virtualMachines/vm01"
                          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                          Bastion Host
                        </label>
                        <input
                          type="text"
                          value={azureBastionHost}
                          onChange={(event) => setAzureBastionHost(event.target.value)}
                          disabled={connectSubmitting}
                          placeholder="bastion-vnet.azure.com"
                          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                          Target Host (VM)
                        </label>
                        <input
                          type="text"
                          value={azureTargetHost}
                          onChange={(event) => setAzureTargetHost(event.target.value)}
                          disabled={connectSubmitting}
                          placeholder="vm01.internal.corp"
                          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                        />
                      </div>
                    </>
                  )}
                  {isGcpIap && (
                    <>
                      <div>
                        <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                          Project ID
                        </label>
                        <input
                          type="text"
                          value={gcpProjectId}
                          onChange={(event) => setGcpProjectId(event.target.value)}
                          disabled={connectSubmitting}
                          placeholder="my-gcp-project"
                          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                          Zone
                        </label>
                        <input
                          type="text"
                          value={gcpZone}
                          onChange={(event) => setGcpZone(event.target.value)}
                          disabled={connectSubmitting}
                          placeholder="us-central1-a"
                          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                          Instance Name
                        </label>
                        <input
                          type="text"
                          value={gcpInstanceName}
                          onChange={(event) => setGcpInstanceName(event.target.value)}
                          disabled={connectSubmitting}
                          placeholder="compute-instance-01"
                          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                          Target Host (optional)
                        </label>
                        <input
                          type="text"
                          value={gcpTargetHost}
                          onChange={(event) => setGcpTargetHost(event.target.value)}
                          disabled={connectSubmitting}
                          placeholder="10.10.10.10"
                          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                        />
                      </div>
                    </>
                  )}
                  {(isWinRM || isSSH) && (
                    <div>
                      <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                        Port
                      </label>
                      <input
                        type="text"
                        value={connectPort}
                        onChange={(event) => setConnectPort(event.target.value)}
                        disabled={connectSubmitting}
                        placeholder={isWinRM ? '5985' : '22'}
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                      />
                    </div>
                  )}
                  {isWinRM && (
                    <div>
                      <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                        Domain
                      </label>
                      <input
                        type="text"
                        value={connectDomain}
                        onChange={(event) => setConnectDomain(event.target.value)}
                        disabled={connectSubmitting}
                        placeholder="CORP"
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                      />
                    </div>
                  )}
                  {isSsm && (
                    <div>
                      <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                        AWS Region
                      </label>
                      <input
                        type="text"
                        value={connectRegion}
                        onChange={(event) => setConnectRegion(event.target.value)}
                        disabled={connectSubmitting}
                        placeholder="us-east-1"
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                      />
                    </div>
                  )}
                  {supportsUsername && (
                    <div>
                      <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                        Username
                      </label>
                      <input
                        type="text"
                        value={connectUsername}
                        onChange={(event) => setConnectUsername(event.target.value)}
                        disabled={connectSubmitting}
                        placeholder={usernamePlaceholder}
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                      />
                    </div>
                  )}
                  {supportsPassword && (
                    <div>
                      <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                        Password
                      </label>
                      <input
                        type="password"
                        value={connectPassword}
                        onChange={(event) => setConnectPassword(event.target.value)}
                        disabled={connectSubmitting}
                        placeholder="••••••••"
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                      />
                      <p className="mt-1 text-[11px] text-gray-500">
                        Leave blank when using a stored credential alias.
                      </p>
                    </div>
                  )}
                  {isWinRM && (
                    <div className="flex items-center gap-2">
                      <input
                        id="winrm-ssl"
                        type="checkbox"
                        checked={connectUseSsl}
                        onChange={(event) => setConnectUseSsl(event.target.checked)}
                        disabled={connectSubmitting}
                        className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <label
                        htmlFor="winrm-ssl"
                        className="text-xs font-medium text-gray-600 uppercase tracking-wide"
                      >
                        Use HTTPS (5986)
                      </label>
                    </div>
                  )}
                  {isSSH && (
                    <div className="md:col-span-2">
                      <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                        Private Key (optional)
                      </label>
                      <textarea
                        value={connectPrivateKey}
                        onChange={(event) => setConnectPrivateKey(event.target.value)}
                        disabled={connectSubmitting}
                        rows={4}
                        placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                      />
                    </div>
                  )}
                  <div className="md:col-span-2">
                    <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                      Credential Alias (optional)
                    </label>
                    <input
                      type="text"
                      value={connectCredentialAlias}
                      onChange={(event) => setConnectCredentialAlias(event.target.value)}
                      disabled={connectSubmitting}
                      placeholder="vault/windows/svc_troubleshoot"
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                    />
                    <p className="mt-1 text-[11px] text-gray-500">
                      Reference an existing secret (Vault, SSM, etc). Inline credentials will be used only if no alias is provided.
                    </p>
                  </div>
                  {isSsm && (
                    <div className="md:col-span-2 text-[11px] text-gray-500">
                      AWS SSM sessions use the worker&apos;s IAM role unless a credential alias is supplied.
                    </div>
                  )}
                </div>
                <div>
                  <label className="block text-xs font-medium uppercase tracking-wide text-gray-600">
                    Session Notes (optional)
                  </label>
                  <textarea
                    value={connectDescription}
                    onChange={(event) => setConnectDescription(event.target.value)}
                    disabled={connectSubmitting}
                    rows={3}
                    placeholder="Context for this remote troubleshooting session…"
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                  />
                </div>
              </div>
              <div className="flex flex-col gap-3 border-t border-gray-200 bg-gray-50 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
                {connectError ? (
                  <p className="text-xs text-red-600">{connectError}</p>
                ) : (
                  <p className="text-xs text-gray-500">
                    Credentials are sent to the worker securely and never logged.
                  </p>
                )}
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={connectSubmitting}
                    onClick={closeConnectModal}
                    className="inline-flex items-center rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={connectSubmitting || runbooksLoading}
                    className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 disabled:cursor-not-allowed disabled:bg-blue-400"
                  >
                    {connectSubmitting ? 'Launching…' : 'Launch Session'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
      <div className="grid lg:grid-cols-[320px,1fr] gap-4">
      <aside className="bg-white border border-gray-200 rounded-2xl shadow-sm p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">
            Active Sessions
          </h2>
          <button
            onClick={fetchSessions}
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
          >
            <ArrowPathIcon className="h-4 w-4" />
            Refresh
          </button>
        </div>
        {loadingSessions ? (
          <div className="text-sm text-gray-500">Loading sessions…</div>
        ) : sessionError ? (
          <div className="text-sm text-red-600">{sessionError}</div>
        ) : sessions.length === 0 ? (
          <div className="text-sm text-gray-500">
            No execution sessions found.
          </div>
        ) : (
          <ul className="space-y-2">
            {sessions.map((session) => (
              <li key={session.id}>
                <button
                  onClick={() => setActiveSessionId(session.id)}
                  className={`w-full text-left px-3 py-2 rounded-xl border transition-colors ${
                    activeSessionId === session.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-blue-300'
                  }`}
                >
                  <div className="flex items-center justify-between text-sm font-semibold text-gray-800">
                    <span>Session #{session.id}</span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(
                        session.status
                      )}`}
                    >
                      {session.status}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-gray-500 line-clamp-2">
                    {session.runbook_title}
                  </div>
                  <div className="mt-1 text-[11px] text-gray-400">
                    Started {formatDate(session.started_at)}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      <section className="bg-white border border-gray-200 rounded-2xl shadow-sm p-6 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="inline-flex items-center gap-2 text-sm font-semibold text-gray-700">
              <BoltIcon className="h-4 w-4 text-blue-600" />
              Live Execution Feed
            </div>
            <div className="text-xs text-gray-500">
              WebSocket: {connectionLabel}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="inline-flex items-center gap-2 text-xs text-gray-500">
              {connected ? (
                <SignalIcon className="h-4 w-4 text-green-500" />
              ) : (
                <WifiIcon className="h-4 w-4 text-amber-500" />
              )}
              {activeSession ? `Session #${activeSession.id}` : 'Select a session'}
            </div>
            <button
              type="button"
              onClick={() => {
                setConnectError(null);
                setConnectModalOpen(true);
              }}
              className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
            >
              <ServerIcon className="h-4 w-4 text-white" />
              Connect to CI
            </button>
          </div>
        </div>

        {loadingDetail ? (
          <div className="text-sm text-gray-500">Loading session details…</div>
        ) : detailError ? (
          <div className="text-sm text-red-600">{detailError}</div>
        ) : !activeSession ? (
          <div className="text-sm text-gray-500">
            Select a session to view live updates.
          </div>
        ) : (
          <div className="space-y-6">
            <div className="border border-gray-200 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-800 mb-2">
                Session Overview
              </h3>
              <dl className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-gray-500">Runbook</dt>
                  <dd className="text-gray-900">{activeSession.runbook_title}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Status</dt>
                  <dd>
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(
                        activeSession.status
                      )}`}
                    >
                      {activeSession.status}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Current Step</dt>
                  <dd className="text-gray-900">
                    {activeSession.current_step ?? '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Sandbox Profile</dt>
                  <dd className="text-gray-900">
                    {activeSession.sandbox_profile ?? 'default'}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Started</dt>
                  <dd className="text-gray-900">
                    {formatDate(activeSession.started_at)}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Completed</dt>
                  <dd className="text-gray-900">
                    {formatDate(activeSession.completed_at ?? undefined)}
                  </dd>
                </div>
              </dl>
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  onClick={() => handleControlAction('pause')}
                  disabled={
                    controlBusy !== null ||
                    normalizedStatus === 'paused' ||
                    normalizedStatus === 'rollback_requested'
                  }
                  className={`inline-flex items-center gap-1 rounded-lg px-3 py-1 text-xs font-medium ${
                    controlBusy === 'pause'
                      ? 'bg-amber-300 text-amber-900'
                      : 'bg-amber-100 text-amber-700 hover:bg-amber-200'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {controlBusy === 'pause' ? 'Pausing…' : 'Pause'}
                </button>
                <button
                  onClick={() => handleControlAction('resume')}
                  disabled={
                    controlBusy !== null || normalizedStatus !== 'paused'
                  }
                  className={`inline-flex items-center gap-1 rounded-lg px-3 py-1 text-xs font-medium ${
                    controlBusy === 'resume'
                      ? 'bg-green-400 text-white'
                      : 'bg-green-100 text-green-700 hover:bg-green-200'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {controlBusy === 'resume' ? 'Resuming…' : 'Resume'}
                </button>
                <button
                  onClick={() => handleControlAction('rollback')}
                  disabled={
                    controlBusy !== null ||
                    normalizedStatus === 'rollback_requested'
                  }
                  className={`inline-flex items-center gap-1 rounded-lg px-3 py-1 text-xs font-medium ${
                    controlBusy === 'rollback'
                      ? 'bg-red-400 text-white'
                      : 'bg-red-100 text-red-700 hover:bg-red-200'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {controlBusy === 'rollback' ? 'Requesting…' : 'Trigger Rollback'}
                </button>
              </div>
              {controlError && (
                <p className="mt-2 text-xs text-red-600">{controlError}</p>
              )}
            </div>

            <div className="border border-gray-200 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-800 mb-2">
                Connection Telemetry
              </h3>
              <dl className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-gray-500">Target Host</dt>
                  <dd className="text-gray-900">
                    {connectionInfo.host ?? '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Connector</dt>
                  <dd className="text-gray-900">
                    {connectionInfo.connector ?? '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Environment</dt>
                  <dd className="text-gray-900">
                    {connectionInfo.environment ?? '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Service</dt>
                  <dd className="text-gray-900">
                    {connectionInfo.service ?? '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Cluster</dt>
                  <dd className="text-gray-900">
                    {connectionInfo.clusterId ?? '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Device</dt>
                  <dd className="text-gray-900">
                    {connectionInfo.deviceId ?? '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Sandbox</dt>
                  <dd className="text-gray-900">
                    {connectionInfo.sandboxProfile ?? 'default'}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Credential Source</dt>
                  <dd className="text-gray-900">
                    {connectionInfo.credentialSource ?? '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Assigned Worker</dt>
                  <dd className="text-gray-900">
                    {connectionInfo.workerId ?? '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Connection Latency</dt>
                  <dd className="text-gray-900">
                    {connectionInfo.connectionLatencyMs !== undefined
                      ? formatShortDuration(connectionInfo.connectionLatencyMs) ?? '—'
                      : '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Last Command</dt>
                  <dd className="text-gray-900">
                    {connectionInfo.lastCommandDurationMs !== undefined
                      ? `${formatShortDuration(connectionInfo.lastCommandDurationMs) ?? '—'} · ${
                          connectionInfo.lastCommandStatus === 'error'
                            ? 'failed'
                            : 'success'
                        }${
                          connectionInfo.lastCommandRetries
                            ? ` · retries ${connectionInfo.lastCommandRetries}`
                            : ''
                        }`
                      : '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Approval Mode</dt>
                  <dd className="text-gray-900">
                    {connectionInfo.approvalMode
                      ? connectionInfo.approvalMode.replace('_', ' ')
                      : '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">SLA Remaining</dt>
                  <dd className="text-gray-900">
                    {formatDuration(connectionInfo.slaRemainingMs)}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">SLA Deadline</dt>
                  <dd className="text-gray-900">
                    {connectionInfo.slaDeadline
                      ? formatDate(connectionInfo.slaDeadline.toISOString())
                      : '—'}
                  </dd>
                </div>
              </dl>
            </div>

            <div className="border border-gray-200 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-800 mb-2">
                Steps
              </h3>
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {activeSession.steps.map((step) => {
                  const approvalStatus = step.requires_approval
                    ? step.approved === true
                      ? 'approved'
                      : step.approved === false
                      ? 'rejected'
                      : 'pending'
                    : 'n/a';
                  const approvalBadge =
                    approvalStatus === 'approved'
                      ? 'bg-green-100 text-green-700'
                      : approvalStatus === 'rejected'
                      ? 'bg-red-100 text-red-700'
                      : 'bg-amber-100 text-amber-700';
                  return (
                    <div
                      key={`${step.step_number}-${step.step_type}`}
                      className="border border-gray-200 rounded-lg px-3 py-2 text-sm space-y-2"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-semibold text-gray-800">
                            #{step.step_number}{' '}
                            <span className="text-gray-500">
                              {step.step_type || 'step'}
                            </span>
                          </div>
                          <div className="text-xs text-gray-500 line-clamp-2">
                            {step.command}
                          </div>
                        </div>
                        <div className="text-xs text-gray-500 text-right">
                          {step.completed ? (
                            <span className="text-green-600 font-semibold">
                              Done
                            </span>
                          ) : (
                            <span>
                              {step.requires_approval && step.approved === null
                                ? 'Awaiting approval'
                                : 'Pending'}
                            </span>
                          )}
                        </div>
                      </div>
                      {step.requires_approval && (
                        step.approved === null ? (
                          <div className="flex flex-wrap justify-end gap-2">
                            <button
                              onClick={() => handleStepApproval(step, true)}
                              disabled={stepActionBusy === step.step_number}
                              className={`inline-flex items-center gap-1 rounded-lg px-3 py-1 text-xs font-medium text-white ${
                                stepActionBusy === step.step_number
                                  ? 'bg-green-400'
                                  : 'bg-green-600 hover:bg-green-700'
                              }`}
                            >
                              {stepActionBusy === step.step_number
                                ? 'Saving...'
                                : 'Approve'}
                            </button>
                            <button
                              onClick={() => handleStepApproval(step, false)}
                              disabled={stepActionBusy === step.step_number}
                              className={`inline-flex items-center gap-1 rounded-lg px-3 py-1 text-xs font-medium text-white ${
                                stepActionBusy === step.step_number
                                  ? 'bg-red-400'
                                  : 'bg-red-600 hover:bg-red-700'
                              }`}
                            >
                              {stepActionBusy === step.step_number
                                ? 'Saving...'
                                : 'Request changes'}
                            </button>
                          </div>
                        ) : (
                          <div className="flex justify-end">
                            <span
                              className={`px-2 py-0.5 rounded-full text-xs font-medium ${approvalBadge}`}
                            >
                              {approvalStatus === 'approved'
                                ? 'Approved'
                                : approvalStatus === 'rejected'
                                ? 'Changes requested'
                                : 'Pending'}
                            </span>
                          </div>
                        )
                      )}
                    </div>
                  );
                })}
              </div>
              {stepActionError && (
                <div className="mt-3 text-xs text-red-600">
                  {stepActionError}
                </div>
              )}
            </div>

          <div className="border border-gray-200 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-gray-800 mb-2">
              Live Console
            </h3>
            <div
              ref={consoleRef}
              className="mt-2 h-48 overflow-y-auto rounded-lg bg-gray-950 px-3 py-2 font-mono text-sm text-gray-100 shadow-inner"
            >
              {consoleLines.length === 0 ? (
                <div className="text-gray-500 text-sm">
                  Waiting for activity…
                </div>
              ) : (
                consoleLines.map((line) => (
                  <div
                    key={line.key}
                    className="flex items-start gap-2 py-0.5"
                  >
                    <span className="w-20 shrink-0 text-right text-[11px] text-gray-500">
                      {line.timestamp ? `[${line.timestamp}]` : ''}
                    </span>
                    <div className="flex-1">
                      <span
                        className={`block leading-snug ${
                          consoleToneStyles[line.tone] ?? consoleToneStyles.info
                        }`}
                      >
                        {line.text}
                      </span>
                      {line.meta && (
                        <span className="block text-[11px] text-gray-400">
                          {line.meta}
                        </span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

            <div className="border border-gray-200 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-800 mb-2">
                Event Stream
              </h3>
              <div className="max-h-64 overflow-y-auto pr-2 text-sm space-y-3">
                {eventHistory.length === 0 ? (
                  <div className="text-gray-500 text-sm">
                    Waiting for events…
                  </div>
                ) : (
                  eventHistory.map((evt) => (
                    (() => {
                      const entry = buildTranscriptEntry(evt);
                      const style = transcriptStyles[entry.variant] || transcriptStyles.neutral;
                      const Icon = entry.icon;
                      return (
                        <div
                          key={createEventKey(evt)}
                          className={`rounded-xl border px-3 py-3 ${style.container}`}
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div className="flex items-center gap-2">
                              <Icon className={`h-4 w-4 ${style.icon}`} />
                              <span
                                className={`text-sm font-semibold ${style.title}`}
                              >
                                {entry.title}
                              </span>
                            </div>
                            <span className="text-[11px] text-gray-500">
                              {entry.timestamp ? formatDate(entry.timestamp) : ''}
                            </span>
                          </div>
                          {entry.summary && (
                            <p className="mt-1 text-sm text-gray-700">
                              {entry.summary}
                            </p>
                          )}
                          {entry.meta && (
                            <dl className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-500">
                              {entry.meta.map((item, idx) => (
                                <div
                                  key={`${createEventKey(evt)}-meta-${idx}`}
                                  className="flex items-center justify-between gap-2"
                                >
                                  <dt className="text-gray-500">{item.label}</dt>
                                  <dd className="text-gray-700 font-medium">
                                    {item.value}
                                  </dd>
                                </div>
                              ))}
                            </dl>
                          )}
                          {entry.detail && (
                            <pre className="mt-2 text-xs text-gray-800 bg-white border border-gray-200 rounded-lg p-3 whitespace-pre-wrap">
                              {entry.detail}
                            </pre>
                          )}
                          {entry.raw && (
                            <details className="mt-2 text-xs text-gray-500">
                              <summary className="cursor-pointer text-gray-600 hover:text-gray-800">
                                View raw event payload
                              </summary>
                              <pre className="mt-2 bg-gray-100 border border-gray-200 rounded-lg p-3 whitespace-pre-wrap text-gray-700">
                                {entry.raw}
                              </pre>
                            </details>
                          )}
                        </div>
                      );
                    })()
                  ))
                )}
              </div>
            </div>
            <div className="border border-gray-200 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-800 mb-2">
                {commandConsoleLabel}
              </h3>
              <p className="text-xs text-gray-500 mb-3">
                {(() => {
                  const connectorVariant = connectionInfo.connector?.toLowerCase();
                  if (connectorVariant === 'winrm') {
                    return 'Send inline PowerShell to the connected Windows host. Use ⌘/Ctrl + Enter to send.';
                  }
                  if (connectorVariant === 'ssh') {
                    return 'Send shell commands over SSH. Use ⌘/Ctrl + Enter to send.';
                  }
                  if (connectorVariant === 'aws_ssm') {
                    return 'Broadcast commands via AWS Systems Manager Session Manager. Use ⌘/Ctrl + Enter to send.';
                  }
                  if (connectorVariant === 'network_cluster') {
                    return 'Send controller commands to the selected network cluster. Use ⌘/Ctrl + Enter to dispatch.';
                  }
                  if (connectorVariant === 'network_device') {
                    return 'Queue CLI commands for the connected network device. Use ⌘/Ctrl + Enter to dispatch.';
                  }
                  if (connectorVariant === 'azure_bastion') {
                    return 'Run shell commands via Azure Bastion tunnel. Use ⌘/Ctrl + Enter to send.';
                  }
                  if (connectorVariant === 'gcp_iap') {
                    return 'Run shell commands over GCP Identity-Aware Proxy. Use ⌘/Ctrl + Enter to send.';
                  }
                  return 'Queue ad-hoc commands for the assigned worker. Use ⌘/Ctrl + Enter to send.';
                })()}
              </p>
              <form
                onSubmit={(event: FormEvent<HTMLFormElement>) => {
                  event.preventDefault();
                  void handleManualCommandSubmit();
                }}
                className="space-y-3"
              >
                <div>
                  <label
                    htmlFor="workspace-command"
                    className="block text-xs font-medium text-gray-600 mb-1 uppercase tracking-wide"
                  >
                    Command
                  </label>
                  <textarea
                    id="workspace-command"
                    value={commandInput}
                    onChange={(event) => setCommandInput(event.target.value)}
                    disabled={commandSubmitting || !activeSessionId}
                    rows={3}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm text-gray-800 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-400"
                    placeholder={commandPlaceholder}
                    onKeyDown={(event) => {
                      if (
                        (event.metaKey || event.ctrlKey) &&
                        event.key === 'Enter'
                      ) {
                        event.preventDefault();
                        void handleManualCommandSubmit();
                      }
                    }}
                  />
                </div>
                <div className="flex flex-col sm:flex-row gap-2">
                  <input
                    type="text"
                    placeholder="Reason (optional)"
                    value={commandReason}
                    onChange={(event) => setCommandReason(event.target.value)}
                    disabled={commandSubmitting}
                    className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-400"
                  />
                  <button
                    type="submit"
                    disabled={
                      commandSubmitting ||
                      !commandInput.trim() ||
                      !activeSessionId
                    }
                    className={`inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium text-white ${
                      commandSubmitting
                        ? 'bg-blue-400'
                        : 'bg-blue-600 hover:bg-blue-700'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    {commandSubmitting ? 'Queueing…' : 'Queue Command'}
                  </button>
                </div>
              </form>
              {commandError && (
                <p className="mt-2 text-xs text-red-600">{commandError}</p>
              )}
            </div>
          </div>
        )}
      </section>
      </div>
    </>
  );
}


