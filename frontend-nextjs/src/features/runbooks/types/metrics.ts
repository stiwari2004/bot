export interface OverallStats {
  total_executions: number;
  successful: number;
  failed: number;
  success_rate: number;
  avg_execution_time_minutes: number;
  min_execution_time_minutes: number;
  max_execution_time_minutes: number;
  avg_rating: number;
  resolution_rate: number;
}

export interface DailyTrend {
  date: string;
  total_executions: number;
  success_rate: number;
  avg_execution_time_minutes: number;
  avg_rating: number;
}

export interface StepMetric {
  step_type: string;
  step_number: number;
  total_attempts: number;
  completion_rate: number;
  success_rate: number;
  successful: number;
  failed: number;
}

export interface RecentExecution {
  id: number;
  issue_description: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  duration_minutes: number | null;
  was_successful: boolean | null;
  rating: number | null;
  issue_resolved: boolean | null;
}

export interface RunbookMetricsData {
  runbook_id: number;
  title: string;
  period_days: number;
  overall_stats: OverallStats;
  rating_distribution: Record<number, number>;
  daily_trends: DailyTrend[];
  step_metrics: StepMetric[];
  recent_executions: RecentExecution[];
  message?: string;
}



