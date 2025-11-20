import {
  BoltIcon,
  CheckCircleIcon,
  CommandLineIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  PlayIcon,
  ServerIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import type { ExecutionEventRecord } from '../hooks/useExecutionEvents';
import type {
  TranscriptEntry,
  TranscriptVariant,
  ConnectorType,
  ConsoleLine,
} from '../types';

export const statusColor = (status: string) => {
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

export const formatDate = (value?: string) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

export const formatDuration = (value?: number) => {
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

export const formatConsoleTimestamp = (value?: string) => {
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

export const formatShortDuration = (value?: number) => {
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

export const createEventKey = (event: ExecutionEventRecord) => {
  if (event.stream_id) return event.stream_id;
  const stamp = event.created_at ?? '';
  return `${event.event}-${event.step_number ?? 'x'}-${stamp}`;
};

export const mergeConnectionDefaults = (
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

export const deriveSandboxProfile = (env?: string, risk?: string): string => {
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

export const defaultAliasForConnector = (connector: ConnectorType): string | undefined => {
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

export const normalizeConnectorType = (
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

export const normalizeCredentialAlias = (
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

export const deriveHostFromSpec = (spec: any): string | undefined => {
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

export const parseMetadataObject = (value: any): Record<string, any> | null => {
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

export const transcriptStyles: Record<
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

export const buildTranscriptEntry = (evt: ExecutionEventRecord): TranscriptEntry => {
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
    ]);
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
    ]);
  } else {
    entry.summary = payload.message || undefined;
    entry.raw = JSON.stringify(payload, null, 2);
  }

  if (!entry.meta || entry.meta.length === 0) {
    entry.meta = undefined;
  }

  return entry;
};
