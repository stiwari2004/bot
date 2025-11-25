'use client';

import { useState, useEffect, type FormEvent, type ChangeEvent } from 'react';
import { BookOpenIcon, WrenchScrewdriverIcon, CheckCircleIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';

interface RunbookResponse {
  id: number;
  title: string;
  body_md: string;
  confidence: number;
  status?: string;
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
  // CI Type: server, database, web, storage, network
  const [ciType, setCiType] = useState('auto');
  // OS Type: Windows, Linux (only for servers)
  const [osType, setOsType] = useState<string>('auto');
  const [envType, setEnvType] = useState('prod');
  const [riskLevel, setRiskLevel] = useState('low');
  const [runbook, setRunbook] = useState<RunbookResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [detectingOS, setDetectingOS] = useState(false);

  // Auto-detect OS from server name in issue description (for servers only)
  useEffect(() => {
    const detectOS = async () => {
      // Only detect OS if CI type is server (or auto which might be server)
      if (ciType !== 'auto' && ciType !== 'server') {
        return;
      }
      
      // Don't override if OS type is already set manually
      if (osType !== 'auto') {
        return;
      }

      // Extract server name from issue description
      const serverPatterns = [
        /\b([A-Za-z0-9-]+(?:VM|vm|Server|server))\b/g,
        /\b([A-Za-z0-9-]+\.(?:local|com|net|org))\b/g,
        /\b(InfraBotTestVM\d+)\b/gi,
      ];

      let serverName: string | null = null;
      for (const pattern of serverPatterns) {
        const matches = issueDescription.match(pattern);
        if (matches && matches.length > 0) {
          serverName = matches[0];
          break;
        }
      }

      // Also check for common server name patterns
      if (!serverName) {
        const words = issueDescription.split(/\s+/);
        for (const word of words) {
          if (/^[A-Za-z0-9-]{3,}$/.test(word) && !['server', 'database', 'service', 'application'].includes(word.toLowerCase())) {
            serverName = word;
            break;
          }
        }
      }

      if (serverName) {
        setDetectingOS(true);
        try {
          const response = await fetch(apiConfig.endpoints.runbooks.detectOS(serverName));
          if (response.ok) {
            const data = await response.json();
            if (data.detected && data.os_type) {
              setOsType(data.os_type);
            }
          }
        } catch (err) {
          console.error('Failed to detect OS:', err);
        } finally {
          setDetectingOS(false);
        }
      }
    };

    // Debounce the detection
    const timeoutId = setTimeout(detectOS, 1000);
    return () => clearTimeout(timeoutId);
  }, [issueDescription, ciType, osType]);

  const handleGenerate = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!issueDescription.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const url = apiConfig.endpoints.runbooks.generateAgent();
      
      // Determine service parameter: if CI type is server and OS type is set, use OS type for backward compatibility
      // Otherwise use CI type
      let serviceParam = ciType;
      if (ciType === 'server' && osType !== 'auto' && osType !== '') {
        serviceParam = osType; // Backward compatibility: Windows/Linux treated as server
      } else if (ciType === 'auto') {
        serviceParam = 'auto';
      }
      
      const params = new URLSearchParams({
        issue_description: issueDescription,
        service: serviceParam,
        env: envType,
        risk: riskLevel
      });

      const response = await fetch(`${url}?${params.toString()}`, {
        method: 'POST',
      });

      if (!response.ok) {
        try {
          const err = await response.json();
          const detail = err?.detail;
          const msg = typeof detail === 'string'
            ? detail
            : (detail?.message || detail?.error || JSON.stringify(detail));
          throw new Error(`(${response.status}) ${msg || 'Runbook generation failed'}`);
        } catch (_) {
          throw new Error(`(${response.status}) Runbook generation failed`);
        }
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

  const handleApprove = async () => {
    if (!runbook || runbook.status !== 'draft') return;

    setApproving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await fetch(`/api/v1/runbooks/demo/${runbook.id}/approve`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to approve runbook');
      }

      const data = await response.json();
      setRunbook(data);
      setSuccessMessage('Runbook approved and published! It is now searchable and will be used for similar issues.');
      onRunbookGenerated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve runbook');
    } finally {
      setApproving(false);
    }
  };

  const formatMarkdown = (markdown: string) => {
    // First, extract code blocks to preserve them
    const codeBlocks: string[] = [];
    const placeholders: string[] = [];
    let processedMarkdown = markdown.replace(/```[\s\S]*?```/g, (match) => {
      const placeholder = `__CODE_BLOCK_${codeBlocks.length}__`;
      codeBlocks.push(match);
      return placeholder;
    });

    // Process markdown without code blocks
    processedMarkdown = processedMarkdown
      .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold text-gray-900 mb-4">$1</h1>')
      .replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold text-gray-800 mb-3 mt-6">$1</h2>')
      .replace(/^### (.*$)/gim, '<h3 class="text-lg font-medium text-gray-700 mb-2 mt-4">$1</h3>')
      .replace(/^\- (.*$)/gim, '<li class="ml-4 text-gray-700">$1</li>')
      .replace(/\n\n/gim, '</p><p class="mb-4 text-gray-700">')
      .replace(/^(?!<[h|l|p|d])/gim, '<p class="mb-4 text-gray-700">')
      .replace(/(?<!>)$/gim, '</p>');

    // Restore code blocks with proper formatting
    codeBlocks.forEach((block, index) => {
      const placeholder = `__CODE_BLOCK_${index}__`;
      // Format code blocks
      const formattedBlock = block
        .replace(/```yaml\n?([\s\S]*?)\n?```/g, '<pre class="bg-gray-100 border border-gray-300 p-4 rounded-lg overflow-x-auto my-4"><code class="text-sm">$1</code></pre>')
        .replace(/```bash\n?([\s\S]*?)\n?```/g, '<pre class="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto my-4"><code class="text-sm">$1</code></pre>')
        .replace(/```([\s\S]*?)\n?```/g, '<pre class="bg-gray-100 border border-gray-300 p-4 rounded-lg overflow-x-auto my-4"><code class="text-sm">$1</code></pre>');
      processedMarkdown = processedMarkdown.replace(placeholder, formattedBlock);
    });

    return processedMarkdown;
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
              onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setIssueDescription(e.target.value)}
              rows={4}
              placeholder="Describe the IT issue you need a runbook for... (e.g., 'Server is running slow and users are complaining about timeouts')"
              className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          {/* Agent-ready only */}

          {
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="ci-type" className="block text-sm font-medium text-gray-700 mb-2">
                    CI Type *
                  </label>
                  <select
                    id="ci-type"
                    value={ciType}
                    onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                      setCiType(e.target.value);
                      // Reset OS type if CI type is not server
                      if (e.target.value !== 'server' && e.target.value !== 'auto') {
                        setOsType('auto');
                      }
                    }}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="auto">Auto-detect</option>
                    <option value="server">Server</option>
                    <option value="database">Database</option>
                    <option value="web">Web Application</option>
                    <option value="storage">Storage</option>
                    <option value="network">Network</option>
                  </select>
                  <p className="mt-1 text-xs text-gray-500">CI Type: server, router, switch, storage, database, web, etc.</p>
                </div>
                
                <div>
                  <label htmlFor="os-type" className="block text-sm font-medium text-gray-700 mb-2">
                    OS Type {ciType === 'server' || ciType === 'auto' ? '*' : '(N/A)'}
                  </label>
                  <select
                    id="os-type"
                    value={osType}
                    onChange={(e: ChangeEvent<HTMLSelectElement>) => setOsType(e.target.value)}
                    disabled={ciType !== 'server' && ciType !== 'auto'}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                  >
                    <option value="auto">Auto-detect {detectingOS && '(detecting...)'}</option>
                    <option value="Windows">Windows</option>
                    <option value="Linux">Linux</option>
                  </select>
                  <p className="mt-1 text-xs text-gray-500">
                    {ciType === 'server' || ciType === 'auto' 
                      ? 'OS Type: Windows or Linux (only for servers)'
                      : 'OS Type not applicable for this CI type'}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="env-type" className="block text-sm font-medium text-gray-700 mb-2">
                    Environment
                  </label>
                  <select
                    id="env-type"
                    value={envType}
                    onChange={(e: ChangeEvent<HTMLSelectElement>) => setEnvType(e.target.value)}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="prod">Production</option>
                    <option value="staging">Staging</option>
                    <option value="dev">Development</option>
                    <option value="testing">Testing</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="risk-level" className="block text-sm font-medium text-gray-700 mb-2">
                    Risk Level
                  </label>
                  <select
                    id="risk-level"
                    value={riskLevel}
                    onChange={(e: ChangeEvent<HTMLSelectElement>) => setRiskLevel(e.target.value)}
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
            <WrenchScrewdriverIcon className="h-5 w-5 mr-2" />
            {loading ? 'Generating...' : 'Generate Runbook'}
          </button>
        </div>
      </form>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {successMessage && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-green-800">{successMessage}</p>
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
              {runbook.status && (
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                  runbook.status === 'draft' ? 'bg-yellow-100 text-yellow-800' :
                  runbook.status === 'approved' ? 'bg-green-100 text-green-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {runbook.status.charAt(0).toUpperCase() + runbook.status.slice(1)}
                </span>
              )}
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                Confidence: {(runbook.confidence * 100).toFixed(0)}%
              </span>
              {runbook.meta_data.sources_used && (
                <span className="text-sm text-gray-500">
                  Sources: {runbook.meta_data.sources_used}
                </span>
              )}
              {runbook.meta_data.service && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
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
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-500">
                <p>Generated on: {new Date(runbook.created_at).toLocaleString()}</p>
                {runbook.meta_data.search_query && (
                  <p>Query: "{runbook.meta_data.search_query}"</p>
                )}
              </div>
              {runbook.status === 'draft' && (
                <button
                  onClick={handleApprove}
                  disabled={approving}
                  className="inline-flex items-center px-4 py-2 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <CheckCircleIcon className="h-5 w-5 mr-2" />
                  {approving ? 'Approving...' : 'Approve & Publish'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
