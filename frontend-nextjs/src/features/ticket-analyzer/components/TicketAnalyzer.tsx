/**
 * Controller: Main component that orchestrates Model, View, and Controller
 * This is the entry point that connects all MVC layers
 */
'use client';

import { useTicketAnalysis } from '../hooks/useTicketAnalysis';
import { TicketAnalysisForm } from './TicketAnalysisForm';
import { AnalysisResultView } from './AnalysisResultView';
import { StatusMessages } from './StatusMessages';

export function TicketAnalyzer() {
  const {
    analysis,
    loading,
    error,
    firstRequest,
    analyzeTicket,
    clearError,
  } = useTicketAnalysis();

  return (
    <div className="space-y-6">
      <TicketAnalysisForm onSubmit={analyzeTicket} loading={loading} />
      
      <StatusMessages
        firstRequest={firstRequest}
        loading={loading}
        error={error}
        onDismissError={clearError}
      />

      {analysis && <AnalysisResultView analysis={analysis} />}
    </div>
  );
}





