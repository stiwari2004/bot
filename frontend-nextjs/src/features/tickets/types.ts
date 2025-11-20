export interface Ticket {
  id: number;
  source: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  classification: string | null;
  classification_confidence: string | null;
  environment: string;
  service: string | null;
  created_at: string;
  analyzed_at: string | null;
  resolved_at: string | null;
}

export interface MatchedRunbook {
  id: number;
  title: string;
  confidence_score: number;
  reasoning: string;
}

export interface ExecutionSession {
  id: number;
  status: string;
  created_at: string;
}

export interface TicketDetail extends Ticket {
  meta_data: any;
  matched_runbooks: MatchedRunbook[];
  execution_sessions: ExecutionSession[];
}

