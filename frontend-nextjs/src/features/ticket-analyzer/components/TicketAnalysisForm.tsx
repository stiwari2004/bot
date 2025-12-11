/**
 * View: Form component for ticket analysis input
 */
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { MagnifyingGlassIcon, BoltIcon } from '@heroicons/react/24/outline';
import { AnalysisRequest } from '../types';

interface TicketAnalysisFormProps {
  onSubmit: (request: AnalysisRequest) => void;
  loading: boolean;
}

export function TicketAnalysisForm({ onSubmit, loading }: TicketAnalysisFormProps) {
  const [issueDescription, setIssueDescription] = useState('');
  const [severity, setSeverity] = useState('medium');
  const [serviceType, setServiceType] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      issue_description: issueDescription,
      severity,
      service_type: serviceType,
      environment: 'prod',
    });
  };

  return (
    <>
      <Card variant="elevated">
        <CardHeader>
          <div className="flex items-center mb-2">
            <div className="p-1.5 rounded-lg bg-primary-100 mr-3">
              <BoltIcon className="h-7 w-7 text-primary-600" />
            </div>
            <h2 className="text-2xl font-semibold text-neutral-900">Intelligent Ticket Analysis</h2>
          </div>
          <p className="text-sm text-neutral-600">
            Enter an issue description to get AI-powered recommendations with existing solutions or generate a new runbook
          </p>
        </CardHeader>
      </Card>

      <Card variant="elevated">
        <CardContent padding="md">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="issue-description" className="block text-sm font-semibold text-neutral-700 mb-2">
                Issue Description *
              </label>
              <textarea
                id="issue-description"
                value={issueDescription}
                onChange={(e) => setIssueDescription(e.target.value)}
                placeholder="e.g., Production database connections timing out, causing intermittent failures..."
                rows={4}
                className="block w-full px-3 py-2 border-2 border-neutral-300 rounded-lg text-neutral-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all"
                required
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="severity" className="block text-sm font-semibold text-neutral-700 mb-2">
                  Severity
                </label>
                <select
                  id="severity"
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value)}
                  className="block w-full px-4 py-2 border-2 border-neutral-300 rounded-lg text-sm font-medium text-neutral-900 bg-white hover:border-primary-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>

              <div>
                <label htmlFor="service-type" className="block text-sm font-semibold text-neutral-700 mb-2">
                  Service Type (Optional)
                </label>
                <input
                  id="service-type"
                  type="text"
                  value={serviceType}
                  onChange={(e) => setServiceType(e.target.value)}
                  placeholder="e.g., server, network, database"
                  className="block w-full px-4 py-2 border-2 border-neutral-300 rounded-lg text-neutral-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all"
                />
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              disabled={loading || !issueDescription.trim()}
              isLoading={loading}
              leftIcon={<MagnifyingGlassIcon className="h-5 w-5" />}
              className="w-full"
            >
              Analyze Ticket
            </Button>
          </form>
        </CardContent>
      </Card>
    </>
  );
}





