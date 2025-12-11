/**
 * Controller: Utility functions for recommendation display
 */
import React from 'react';
import type { AnalysisResponse } from '../types';
import { 
  CheckCircleIcon, 
  WrenchScrewdriverIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

export function getRecommendationIcon(analysis: AnalysisResponse | null): React.ReactElement | null {
  if (!analysis) return null;
  
  switch (analysis.recommendation) {
    case 'existing_runbook':
      return React.createElement(CheckCircleIcon, { className: "h-8 w-8 text-green-500" });
    case 'generate_new':
      return React.createElement(WrenchScrewdriverIcon, { className: "h-8 w-8 text-blue-500" });
    case 'escalate':
      return React.createElement(ExclamationTriangleIcon, { className: "h-8 w-8 text-yellow-500" });
    default:
      return null;
  }
}

export function getRecommendationColor(analysis: AnalysisResponse | null): string {
  if (!analysis) return '';
  
  switch (analysis.recommendation) {
    case 'existing_runbook':
      return 'bg-success-50 border-success-200 text-success-900';
    case 'generate_new':
      return 'bg-primary-50 border-primary-200 text-primary-900';
    case 'escalate':
      return 'bg-warning-50 border-warning-200 text-warning-900';
    default:
      return '';
  }
}

export function getRecommendationTitle(analysis: AnalysisResponse | null): string {
  if (!analysis) return '';
  
  switch (analysis.recommendation) {
    case 'existing_runbook':
      return 'Use Existing Runbook';
    case 'generate_new':
      return 'Generate New Runbook';
    case 'escalate':
      return 'Escalate to Human';
    default:
      return '';
  }
}

