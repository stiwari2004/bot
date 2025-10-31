'use client';

import { useState } from 'react';
import { BookOpenIcon, SparklesIcon } from '@heroicons/react/24/outline';
import { API_BASE_URL } from '@/lib/config';

interface RunbookResponse {
  id: number;
  title: string;
  body_md: string;
  confidence: number;
  meta_data: {
    issue_description: string;
    sources_used?: number;
    search_query?: string;
    generated_by: string;
    service?: string;
    env?: string;
    risk?: string;
    runbook_spec?: any;
  };
  created_at: string;
}

interface RunbookGeneratorProps {
  onRunbookGenerated?: () => void;
}

export function RunbookGenerator({ onRunbookGenerated }: RunbookGeneratorProps) {
  const [issueDescription, setIssueDescription] = useState('');
  // Always generate Agent-Ready runbooks
  const [serviceType, setServiceType] = useState('auto');
  const [envType, setEnvType] = useState('prod');
  const [riskLevel, setRiskLevel] = useState('low');
  const [runbook, setRunbook] = useState<RunbookResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!issueDescription.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const url = `${API_BASE_URL}/api/v1/runbooks/demo/generate-agent`;
      const params = new URLSearchParams({
        issue_description: issueDescription,
        service: serviceType,
        env: envType,
        risk: riskLevel
      });

      const response = await fetch(`${url}?${params}`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Runbook generation failed');
      }

      const data = await response.json();
      setRunbook(data);
      onRunbookGenerated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Runbook generation failed');
    } finally {
      setLoading(false);
    }
  };

  const formatMarkdown = (markdown: string) => {
    return markdown
      .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold text-gray-900 mb-4">$1</h1>')
      .replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold text-gray-800 mb-3 mt-6">$1</h2>')
      .replace(/^### (.*$)/gim, '<h3 class="text-lg font-medium text-gray-700 mb-2 mt-4">$1</h3>')
      .replace(/^\- (.*$)/gim, '<li class="ml-4 text-gray-700">$1</li>')
      .replace(/```bash\n([\s\S]*?)\n```/gim, '<pre class="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto my-4"><code>$1</code></pre>')
      .replace(/```([\s\S]*?)```/gim, '<pre class="bg-gray-100 p-4 rounded-lg overflow-x-auto my-4"><code>$1</code></pre>')
      .replace(/\n\n/gim, '</p><p class="mb-4 text-gray-700">')
      .replace(/^(?!<[h|l|p|d])/gim, '<p class="mb-4 text-gray-700">')
      .replace(/(?<!>)$/gim, '</p>');
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Generate Runbook</h2>
        <p className="text-gray-600">Describe an IT issue and let AI generate a comprehensive troubleshooting guide</p>
      </div>

      <form onSubmit={handleGenerate} className="mb-6">
        <div className="space-y-4">
          <div>
            <label htmlFor="issue-description" className="block text-sm font-medium text-gray-700 mb-2">
              Issue Description
            </label>
            <textarea
              id="issue-description"
              value={issueDescription}
              onChange={(e) => setIssueDescription(e.target.value)}
              rows={4}
              placeholder="Describe the IT issue you need a runbook for... (e.g., 'Server is running slow and users are complaining about timeouts')"
              className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          {/* Agent-ready only */}

          {
            <>
              <div>
                <label htmlFor="service-type" className="block text-sm font-medium text-gray-700 mb-2">
                  Service Type
                </label>
                <select
                  id="service-type"
                  value={serviceType}
                  onChange={(e) => setServiceType(e.target.value)}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="auto">Auto-detect (Recommended)</option>
                  <option value="server">Server</option>
                  <option value="network">Network</option>
                  <option value="database">Database</option>
                  <option value="web">Web Application</option>
                  <option value="storage">Storage</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="env-type" className="block text-sm font-medium text-gray-700 mb-2">
                    Environment
                  </label>
                  <select
                    id="env-type"
                    value={envType}
                    onChange={(e) => setEnvType(e.target.value)}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="prod">Production</option>
                    <option value="staging">Staging</option>
                    <option value="dev">Development</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="risk-level" className="block text-sm font-medium text-gray-700 mb-2">
                    Risk Level
                  </label>
                  <select
                    id="risk-level"
                    value={riskLevel}
                    onChange={(e) => setRiskLevel(e.target.value)}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>
            </>
          }

          {/* Traditional path removed */}
        </div>

        <div className="mt-6">
          <button
            type="submit"
            disabled={loading || !issueDescription.trim()}
            className="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <SparklesIcon className="h-5 w-5 mr-2" />
            {loading ? 'Generating...' : 'Generate Runbook'}
          </button>
        </div>
      </form>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {runbook && (
        <div className="border border-gray-200 rounded-lg p-6">
          <div className="mb-6 flex items-center justify-between">
            <div className="flex items-center">
              <BookOpenIcon className="h-6 w-6 text-blue-600 mr-2" />
              <h3 className="text-xl font-semibold text-gray-900">{runbook.title}</h3>
            </div>
            <div className="flex items-center space-x-4">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                Confidence: {(runbook.confidence * 100).toFixed(0)}%
              </span>
              {runbook.meta_data.sources_used && (
                <span className="text-sm text-gray-500">
                  Sources: {runbook.meta_data.sources_used}
                </span>
              )}
              {runbook.meta_data.service && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {runbook.meta_data.service.toUpperCase()}
                </span>
              )}
            </div>
          </div>

          <div className="prose max-w-none">
            <div 
              dangerouslySetInnerHTML={{ 
                __html: formatMarkdown(runbook.body_md) 
              }}
            />
          </div>

          <div className="mt-6 pt-4 border-t border-gray-200">
            <div className="text-sm text-gray-500">
              <p>Generated on: {new Date(runbook.created_at).toLocaleString()}</p>
              <p>Query: "{runbook.meta_data.search_query}"</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
