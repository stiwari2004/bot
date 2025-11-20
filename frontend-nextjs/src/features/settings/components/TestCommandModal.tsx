'use client';

import { useState, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import type { InfrastructureConnection } from '../types';

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
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Test Command Execution</h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {discoveredVMs.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-600 mb-4">No VMs discovered. Please click "Discover" first.</p>
              <button
                onClick={onClose}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300"
              >
                Close
              </button>
            </div>
          ) : (
            <>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Select VM
                  </label>
                  <select
                    value={selectedVM}
                    onChange={(e) => setSelectedVM(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Shell Type
                  </label>
                  <select
                    value={shell}
                    onChange={(e) => setShell(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="powershell">PowerShell (Windows)</option>
                    <option value="bash">Bash (Linux)</option>
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    Auto-detected from VM OS if not specified
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Command
                  </label>
                  <textarea
                    value={command}
                    onChange={(e) => setCommand(e.target.value)}
                    placeholder={shell === 'powershell' ? 'Write-Host "Hello from Azure VM"' : 'echo "Hello from Azure VM"'}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                    rows={4}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Example commands: {shell === 'powershell' 
                      ? 'Write-Host "Test", Get-ComputerInfo, Get-Service | Select-Object -First 5'
                      : 'echo "Test", hostname, df -h'}
                  </p>
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                    {error}
                  </div>
                )}

                {result && (
                  <div className="border border-gray-300 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold">Execution Result</h3>
                      <span className={`px-2 py-1 rounded text-sm ${
                        result.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {result.success ? 'Success' : 'Failed'}
                      </span>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div>
                        <span className="font-medium">VM:</span> {result.vm_name} ({result.resource_group})
                      </div>
                      <div>
                        <span className="font-medium">Shell:</span> {result.shell}
                      </div>
                      <div>
                        <span className="font-medium">Exit Code:</span> {result.exit_code}
                      </div>
                      {result.output && (
                        <div>
                          <span className="font-medium">Output:</span>
                          <pre className="mt-1 p-2 bg-gray-50 border border-gray-200 rounded text-xs overflow-x-auto">
                            {result.output}
                          </pre>
                        </div>
                      )}
                      {result.error && (
                        <div>
                          <span className="font-medium">Error:</span>
                          <pre className="mt-1 p-2 bg-red-50 border border-red-200 rounded text-xs overflow-x-auto text-red-700">
                            {result.error}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <div className="flex gap-2 justify-end">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300"
                  >
                    Close
                  </button>
                  <button
                    onClick={handleExecute}
                    disabled={loading || !selectedVM || !command.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Executing...' : 'Execute Command'}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

