/**
 * Model: Type definitions for Ticket Analyzer
 */

export interface RunbookMatch {
  id: number;
  title: string;
  similarity_score: number;
  confidence_score: number;
  success_rate: number | null;
  times_used: number;
  last_used: string | null;
  reasoning: string;
}

export interface AnalysisResponse {
  recommendation: 'existing_runbook' | 'generate_new' | 'escalate';
  confidence: number;
  reasoning: string;
  matched_runbooks: RunbookMatch[];
  suggested_actions: string[];
  threshold_used: number;
}

export interface AnalysisRequest {
  issue_description: string;
  severity: string;
  service_type?: string;
  environment?: string;
}





