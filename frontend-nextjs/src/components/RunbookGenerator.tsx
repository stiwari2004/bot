'use client';

import { useState, useEffect, type FormEvent, type ChangeEvent } from 'react';
import { BookOpenIcon, WrenchScrewdriverIcon, CheckCircleIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';

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
      .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold text-neutral-900 mb-4">$1</h1>')
      .replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold text-neutral-800 mb-3 mt-6">$1</h2>')
      .replace(/^### (.*$)/gim, '<h3 class="text-lg font-medium text-neutral-700 mb-2 mt-4">$1</h3>')
      .replace(/^\- (.*$)/gim, '<li class="ml-4 text-neutral-700">$1</li>')
      .replace(/\n\n/gim, '</p><p class="mb-4 text-neutral-700">')
      .replace(/^(?!<[h|l|p|d])/gim, '<p class="mb-4 text-neutral-700">')
      .replace(/(?<!>)$/gim, '</p>');

    // Restore code blocks with proper formatting
    codeBlocks.forEach((block, index) => {
      const placeholder = `__CODE_BLOCK_${index}__`;
      // Format code blocks
      const formattedBlock = block
        .replace(/```yaml\n?([\s\S]*?)\n?```/g, '<pre class="bg-neutral-100 border-2 border-neutral-300 p-4 rounded-lg overflow-x-auto my-4"><code class="text-sm text-neutral-900">$1</code></pre>')
        .replace(/```bash\n?([\s\S]*?)\n?```/g, '<pre class="bg-neutral-900 text-success-400 p-4 rounded-lg overflow-x-auto my-4"><code class="text-sm">$1</code></pre>')
        .replace(/```([\s\S]*?)\n?```/g, '<pre class="bg-neutral-100 border-2 border-neutral-300 p-4 rounded-lg overflow-x-auto my-4"><code class="text-sm text-neutral-900">$1</code></pre>');
      processedMarkdown = processedMarkdown.replace(placeholder, formattedBlock);
    });

    return processedMarkdown;
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-neutral-900 mb-2">Generate Runbook</h2>
        <p className="text-neutral-600">Describe an IT issue and let AI generate a comprehensive troubleshooting guide</p>
      </div>

      <Card variant="elevated" className="mb-6">
        <CardContent padding="md">
          <form onSubmit={handleGenerate}>
            <div className="space-y-4">
              <div>
                <label htmlFor="issue-description" className="block text-sm font-semibold text-neutral-700 mb-2">
                  Issue Description
                </label>
                <Textarea
                  id="issue-description"
                  value={issueDescription}
                  onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setIssueDescription(e.target.value)}
                  rows={4}
                  placeholder="Describe the IT issue you need a runbook for... (e.g., 'Server is running slow and users are complaining about timeouts')"
                />
              </div>
          
          {/* Agent-ready only */}

          {
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="ci-type" className="block text-sm font-semibold text-neutral-700 mb-2">
                    CI Type *
                  </label>
                  <Select
                    value={ciType}
                    onValueChange={(value) => {
                      setCiType(value);
                      if (value !== 'server' && value !== 'auto') {
                        setOsType('auto');
                      }
                    }}
                  >
                    <SelectTrigger id="ci-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auto">Auto-detect</SelectItem>
                      <SelectItem value="server">Server</SelectItem>
                      <SelectItem value="database">Database</SelectItem>
                      <SelectItem value="web">Web Application</SelectItem>
                      <SelectItem value="storage">Storage</SelectItem>
                      <SelectItem value="network">Network</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="mt-1 text-xs text-neutral-500">CI Type: server, router, switch, storage, database, web, etc.</p>
                </div>
                
                <div>
                  <label htmlFor="os-type" className="block text-sm font-semibold text-neutral-700 mb-2">
                    OS Type {ciType === 'server' || ciType === 'auto' ? '*' : '(N/A)'}
                  </label>
                  <Select
                    value={osType}
                    onValueChange={setOsType}
                    disabled={ciType !== 'server' && ciType !== 'auto'}
                  >
                    <SelectTrigger id="os-type">
                      <SelectValue placeholder={detectingOS ? 'Detecting...' : 'Select OS'} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auto">Auto-detect {detectingOS && '(detecting...)'}</SelectItem>
                      <SelectItem value="Windows">Windows</SelectItem>
                      <SelectItem value="Linux">Linux</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="mt-1 text-xs text-neutral-500">
                    {ciType === 'server' || ciType === 'auto' 
                      ? 'OS Type: Windows or Linux (only for servers)'
                      : 'OS Type not applicable for this CI type'}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="env-type" className="block text-sm font-semibold text-neutral-700 mb-2">
                    Environment
                  </label>
                  <Select value={envType} onValueChange={setEnvType}>
                    <SelectTrigger id="env-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="prod">Production</SelectItem>
                      <SelectItem value="staging">Staging</SelectItem>
                      <SelectItem value="dev">Development</SelectItem>
                      <SelectItem value="testing">Testing</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label htmlFor="risk-level" className="block text-sm font-semibold text-neutral-700 mb-2">
                    Risk Level
                  </label>
                  <Select value={riskLevel} onValueChange={setRiskLevel}>
                    <SelectTrigger id="risk-level">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </>
          }

          {/* Traditional path removed */}
        </div>

              <div className="mt-6">
                <Button
                  type="submit"
                  variant="primary"
                  disabled={loading || !issueDescription.trim()}
                  isLoading={loading}
                  leftIcon={<WrenchScrewdriverIcon className="h-5 w-5" />}
                >
                  {loading ? 'Generating...' : 'Generate Runbook'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {error && (
          <Card variant="outlined" className="mb-6 border-error-200 bg-error-50">
            <CardContent padding="sm">
              <p className="text-error-800 font-medium">{error}</p>
            </CardContent>
          </Card>
        )}

        {successMessage && (
          <Card variant="outlined" className="mb-6 border-success-200 bg-success-50">
            <CardContent padding="sm">
              <p className="text-success-800 font-medium">{successMessage}</p>
            </CardContent>
          </Card>
        )}

      {runbook && (
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-primary-100">
                  <BookOpenIcon className="h-6 w-6 text-primary-600" />
                </div>
                <h3 className="text-xl font-semibold text-neutral-900">{runbook.title}</h3>
              </div>
              <div className="flex items-center gap-3 flex-wrap">
                {runbook.status && (
                  <Badge variant="status" status={runbook.status === 'draft' ? 'waiting_approval' : runbook.status === 'approved' ? 'completed' : 'pending'} size="sm">
                    {runbook.status.charAt(0).toUpperCase() + runbook.status.slice(1)}
                  </Badge>
                )}
                <Badge variant="primary" size="sm">
                  Confidence: {(runbook.confidence * 100).toFixed(0)}%
                </Badge>
                {runbook.meta_data.sources_used && (
                  <span className="text-sm text-neutral-600 font-medium">
                    Sources: {runbook.meta_data.sources_used}
                  </span>
                )}
                {runbook.meta_data.service && (
                  <Badge variant="secondary" size="sm">
                    {runbook.meta_data.service.toUpperCase()}
                  </Badge>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent padding="md">

            <div className="prose max-w-none">
              <div 
                dangerouslySetInnerHTML={{ 
                  __html: formatMarkdown(runbook.body_md) 
                }}
              />
            </div>

            <div className="mt-6 pt-4 border-t border-neutral-200">
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div className="text-sm text-neutral-600">
                  <p className="font-medium">Generated on: {new Date(runbook.created_at).toLocaleString()}</p>
                  {runbook.meta_data.search_query && (
                    <p className="text-neutral-500">Query: "{runbook.meta_data.search_query}"</p>
                  )}
                </div>
                {runbook.status === 'draft' && (
                  <Button
                    variant="success"
                    onClick={handleApprove}
                    disabled={approving}
                    isLoading={approving}
                    leftIcon={<CheckCircleIcon className="h-5 w-5" />}
                  >
                    {approving ? 'Approving...' : 'Approve & Publish'}
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
