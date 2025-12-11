export interface Alert {
  id: number;
  external_id: string | null;
  source: string;
  title: string;
  description: string | null;
  severity: string;
  environment: string;
  service: string | null;
  status: string; // firing, resolved, acknowledged
  received_at: string;
  starts_at: string | null;
  ends_at: string | null;
  resolved_at: string | null;
  matched_ticket_id: number | null;
  matched_at: string | null;
  meta_data: any;
}

export interface AlertDetail extends Alert {
  raw_payload: any;
}









