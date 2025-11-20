export interface ExecutionStep {
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

export interface ExecutionSessionSummary {
  id: number;
  runbook_id: number;
  runbook_title?: string;
  status: string;
  started_at?: string;
  completed_at?: string | null;
}

export interface ExecutionSessionDetail extends ExecutionSessionSummary {
  issue_description?: string;
  current_step?: number | null;
  waiting_for_approval?: boolean;
  sandbox_profile?: string | null;
  steps: ExecutionStep[];
  connection?: Record<string, any> | null;
}

export interface RunbookOption {
  id: number;
  title: string;
  description?: string | null;
  metadata?: Record<string, any> | null;
}

export type TranscriptVariant = 'info' | 'success' | 'warning' | 'error' | 'neutral';

export interface TranscriptEntry {
  title: string;
  summary?: string;
  detail?: string;
  meta?: Array<{ label: string; value: string }>;
  variant: TranscriptVariant;
  icon: any;
  timestamp?: string;
  raw?: string;
}

export type ConsoleLineTone = 'prompt' | 'success' | 'error' | 'info' | 'warning' | 'output';

export interface ConsoleLine {
  key: string;
  text: string;
  tone: ConsoleLineTone;
  timestamp?: string;
  meta?: string;
}

export type ControlAction = 'pause' | 'resume' | 'rollback';

export type ConnectorType =
  | 'winrm'
  | 'ssh'
  | 'aws_ssm'
  | 'network_cluster'
  | 'network_device'
  | 'azure_bastion'
  | 'gcp_iap';

export interface NetworkClusterOption {
  id: string;
  name: string;
  description?: string;
  vendor?: string;
  management_host?: string;
  transport?: string;
  default_prompt?: string;
}

export interface NetworkDeviceOption {
  id: string;
  name: string;
  vendor?: string;
  model?: string;
  role?: string;
  mgmt_ip?: string;
}

export interface ConnectionInfo {
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
}
