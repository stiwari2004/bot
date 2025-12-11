/**
 * Model: Service layer for Ticket Analysis API calls
 */
import { AnalysisRequest, AnalysisResponse } from '../types';

const API_BASE = '/api/v1/tickets/demo';

export class TicketAnalysisService {
  /**
   * Analyze a ticket and get recommendations
   */
  static async analyzeTicket(request: AnalysisRequest): Promise<AnalysisResponse> {
    const response = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        issue_description: request.issue_description,
        severity: request.severity,
        service_type: request.service_type || undefined,
        environment: request.environment || 'prod',
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Analysis failed: ${response.status} ${errorText}`);
    }

    return await response.json();
  }
}





