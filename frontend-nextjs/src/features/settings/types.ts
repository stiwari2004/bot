export interface ExecutionMode {
  mode: string;
  description: string;
}

export interface TicketingConnection {
  id: number;
  tool_name: string;
  connection_type: string;
  is_active: boolean;
  webhook_url: string | null;
  api_base_url: string | null;
  last_sync_at: string | null;
  last_sync_status: string | null;
  last_error: string | null;
  sync_interval_minutes?: number;
  api_key?: string | null;
  api_username?: string | null;
  meta_data?: string | any;
  oauth_authorized?: boolean;
}

export interface TicketingTool {
  name: string;
  display_name: string;
  connection_types: string[];
  description: string;
}

export interface InfrastructureConnection {
  id: number;
  name: string;
  type: string;
  target_host: string | null;
  target_port: number | null;
  target_service: string | null;
  environment: string;
  credential_id: number | null;
  created_at: string | null;
}

export interface Credential {
  id: number;
  name: string;
  type: string;
  environment: string;
  host: string | null;
  port: number | null;
  database_name: string | null;
  created_at: string | null;
}



