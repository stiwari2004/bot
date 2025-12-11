/**
 * Controller: Business logic for Ticket Analysis
 */
import { useState } from 'react';
import { AnalysisResponse, AnalysisRequest } from '../types';
import { TicketAnalysisService } from '../services/ticketAnalysisService';

export function useTicketAnalysis() {
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [firstRequest, setFirstRequest] = useState(true);

  const analyzeTicket = async (request: AnalysisRequest) => {
    if (!request.issue_description.trim()) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await TicketAnalysisService.analyzeTicket(request);
      setAnalysis(data);
      setFirstRequest(false);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Analysis failed';
      setError(errorMessage);
      
      // Provide helpful error message for timeouts
      if (errorMessage.includes('500') || errorMessage.includes('timeout')) {
        setError('Request timed out. The first analysis may take 1-2 minutes to load the AI model. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const clearError = () => {
    setError(null);
  };

  const reset = () => {
    setAnalysis(null);
    setError(null);
    setFirstRequest(true);
  };

  return {
    analysis,
    loading,
    error,
    firstRequest,
    analyzeTicket,
    clearError,
    reset,
  };
}





