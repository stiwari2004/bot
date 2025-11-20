export interface RunbookStep {
  id?: number;
  step_number: number;
  type: 'precheck' | 'main' | 'postcheck';
  command: string;
  description?: string;
  completed: boolean;
  success: boolean | null;
  output?: string | null;
  notes?: string | null;
  requires_approval?: boolean;
  approved?: boolean | null;
  severity?: string;
  rollback_command?: string | null;
}

export interface ExecutionSession {
  id: number;
  runbook_id: number;
  runbook_title: string;
  issue_description: string;
  status: string;
  started_at: string;
  completed_at?: string;
  total_duration_minutes?: number;
  current_step?: number | null;
  waiting_for_approval?: boolean;
  steps: RunbookStep[];
}

export type StepUpdatePayload = {
  completed?: boolean;
  success?: boolean | null;
  output?: string;
  notes?: string;
  approved?: boolean | null;
};

