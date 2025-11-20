export interface Runbook {
  id: number;
  title: string;
  body_md: string;
  confidence: number;
  status?: string;
  meta_data: {
    issue_description: string;
    sources_used: number;
    search_query: string;
    generated_by: string;
  };
  created_at: string;
}

