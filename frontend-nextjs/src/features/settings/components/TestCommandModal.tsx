'use client';

import { useState, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import type { InfrastructureConnection } from '../types';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface TestCommandModalProps {
  connection: InfrastructureConnection;
  discoveredVMs: any[];
  onClose: () => void;
}

export function TestCommandModal({ connection, discoveredVMs, onClose }: TestCommandModalProps) {
  const [selectedVM, setSelectedVM] = useState<string>('');
  const [command, setCommand] = useState<string>('');
  const [shell, setShell] = useState<string>('powershell');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  const handleExecute = async () => {
    if (!selectedVM || !command.trim()) {
      setError('Please select a VM and enter a command');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const vm = discoveredVMs.find(v => v.resource_id === selectedVM);
      if (!vm) {
        throw new Error('Selected VM not found');
      }

      const url = apiConfig.endpoints.connectors.infrastructureConnectionTestCommand(connection.id);
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vm_resource_id: selectedVM,
          command: command.trim(),
          shell: shell || undefined
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute command');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-4xl max-h-[90vh] overflow-y-auto"
      >
        <Card variant="elevated">
          <CardHeader>
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold text-neutral-900">Test Command Execution</h2>
              <Button variant="ghost" size="sm" onClick={onClose}>
                <XMarkIcon className="h-6 w-6" />
              </Button>
            </div>
          </CardHeader>
          <CardContent padding="md">
            {discoveredVMs.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-neutral-600 mb-4 font-medium">No VMs discovered. Please click "Discover" first.</p>
                <Button variant="secondary" onClick={onClose}>
                  Close
                </Button>
              </div>
            ) : (
              <>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-semibold text-neutral-700 mb-2">
                      Select VM
                    </label>
                    <select
                      value={selectedVM}
                      onChange={(e) => setSelectedVM(e.target.value)}
                      className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    >
                      <option value="">-- Select a VM --</option>
                      {discoveredVMs.map((vm) => (
                        <option key={vm.resource_id} value={vm.resource_id}>
                          {vm.name} ({vm.resource_group}) - {vm.os_type || 'Unknown OS'}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-neutral-700 mb-2">
                      Shell Type
                    </label>
                    <select
                      value={shell}
                      onChange={(e) => setShell(e.target.value)}
                      className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    >
                      <option value="powershell">PowerShell (Windows)</option>
                      <option value="bash">Bash (Linux)</option>
                    </select>
                    <p className="text-xs text-neutral-500 mt-1">
                      Auto-detected from VM OS if not specified
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-neutral-700 mb-2">
                      Command
                    </label>
                    <textarea
                      value={command}
                      onChange={(e) => setCommand(e.target.value)}
                      placeholder={shell === 'powershell' ? 'Write-Host "Hello from Azure VM"' : 'echo "Hello from Azure VM"'}
                      className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 font-mono text-sm text-neutral-900 transition-all"
                      rows={4}
                    />
                    <p className="text-xs text-neutral-500 mt-1">
                      Example commands: {shell === 'powershell' 
                        ? 'Write-Host "Test", Get-ComputerInfo, Get-Service | Select-Object -First 5'
                        : 'echo "Test", hostname, df -h'}
                    </p>
                  </div>

                  {error && (
                    <Card variant="outlined" className="border-error-200 bg-error-50">
                      <CardContent padding="sm">
                        <p className="text-sm text-error-800 font-medium">{error}</p>
                      </CardContent>
                    </Card>
                  )}

                  {result && (
                    <Card variant="default">
                      <CardContent padding="md">
                        <div className="flex items-center justify-between mb-3">
                          <h3 className="font-semibold text-neutral-900">Execution Result</h3>
                          <Badge variant={result.success ? 'success' : 'error'} size="sm">
                            {result.success ? 'Success' : 'Failed'}
                          </Badge>
                        </div>
                        <div className="space-y-2 text-sm">
                          <div>
                            <span className="font-semibold text-neutral-700">VM:</span> <span className="text-neutral-900">{result.vm_name} ({result.resource_group})</span>
                          </div>
                          <div>
                            <span className="font-semibold text-neutral-700">Shell:</span> <span className="text-neutral-900">{result.shell}</span>
                          </div>
                          <div>
                            <span className="font-semibold text-neutral-700">Exit Code:</span> <span className="text-neutral-900">{result.exit_code}</span>
                          </div>
                          {result.output && (
                            <div>
                              <span className="font-semibold text-neutral-700">Output:</span>
                              <pre className="mt-2 p-3 bg-neutral-50 border-2 border-neutral-200 rounded-lg text-xs overflow-x-auto text-neutral-900">
                                {result.output}
                              </pre>
                            </div>
                          )}
                          {result.error && (
                            <div>
                              <span className="font-semibold text-error-700">Error:</span>
                              <pre className="mt-2 p-3 bg-error-50 border-2 border-error-200 rounded-lg text-xs overflow-x-auto text-error-800">
                                {result.error}
                              </pre>
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  <div className="flex gap-2 justify-end">
                    <Button
                      variant="outline"
                      onClick={onClose}
                    >
                      Close
                    </Button>
                    <Button
                      variant="primary"
                      onClick={handleExecute}
                      disabled={loading || !selectedVM || !command.trim()}
                      isLoading={loading}
                    >
                      {loading ? 'Executing...' : 'Execute Command'}
                    </Button>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}



