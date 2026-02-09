'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeftIcon,
  KeyIcon,
  CircleStackIcon,
  ServerStackIcon,
  CheckCircleIcon,
  ClipboardDocumentIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';

interface TokenStatus {
  configured: boolean;
}

interface DiscoveryCurrent {
  current_run_id: number | null;
  assets_count: number;
}

interface DiscoveryRun {
  id: number;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  run_config: string | null;
}

interface DiscoveryAsset {
  id: number;
  source: string;
  source_native_id: string;
  name: string | null;
  primary_ip: string | null;
  tags: string | null;
}

interface DiscoveryViewProps {
  token: string | null;
  /** When true, show back button and full-page header (e.g. on /tenant-admin/discovery). When false, show only content (e.g. in-app System tab). */
  standalone?: boolean;
  backHref?: string;
}

export function DiscoveryView({ token, standalone = false, backHref = '/tenant-admin' }: DiscoveryViewProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Link to Settings tab preserving current query (e.g. customer_slug)
  const settingsUrl = (() => {
    if (typeof window === 'undefined') return '/?tab=settings';
    const params = new URLSearchParams(searchParams?.toString() ?? window.location.search);
    params.set('tab', 'settings');
    return `${window.location.pathname || '/'}?${params.toString()}`;
  })();
  const [tokenStatus, setTokenStatus] = useState<TokenStatus | null>(null);
  const [newToken, setNewToken] = useState<string | null>(null);
  const [runs, setRuns] = useState<DiscoveryRun[]>([]);
  const [current, setCurrent] = useState<DiscoveryCurrent | null>(null);
  const [assets, setAssets] = useState<DiscoveryAsset[]>([]);
  const [selectedAssetIds, setSelectedAssetIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const baseUrl = typeof window !== 'undefined' ? window.location.origin : '';
  const ingestUrl = `${baseUrl}/api/v1/tenant-admin/discovery/ingest`;
  const runScriptUrl = `${baseUrl}/api/v1/tenant-admin/discovery/run`;
  const oneCommandUnix = `curl -sSL "${runScriptUrl}" -o run.py && python3 run.py "${ingestUrl}" "YOUR_TOKEN"`;
  const oneCommandWindows = `powershell -Command "Invoke-WebRequest -Uri '${runScriptUrl}' -OutFile run.py; python run.py '${ingestUrl}' 'YOUR_TOKEN'"`;

  const fetchTokenStatus = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(apiConfig.endpoints.tenantAdmin.discovery.tokenStatus(), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setTokenStatus(data);
      }
    } catch (e) {
      console.error('Token status:', e);
    }
  }, [token]);

  const fetchRuns = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(apiConfig.endpoints.tenantAdmin.discovery.runs(), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setRuns(data);
      }
    } catch (e) {
      console.error('Runs:', e);
    }
  }, [token]);

  const fetchCurrent = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(apiConfig.endpoints.tenantAdmin.discovery.current(), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCurrent(data);
      }
    } catch (e) {
      console.error('Current:', e);
    }
  }, [token]);

  const fetchAssets = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(apiConfig.endpoints.tenantAdmin.discovery.assets(), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAssets(data);
      }
    } catch (e) {
      console.error('Assets:', e);
    }
  }, [token]);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    Promise.all([fetchTokenStatus(), fetchRuns(), fetchCurrent(), fetchAssets()]).finally(() =>
      setLoading(false)
    );
  }, [token, fetchTokenStatus, fetchRuns, fetchCurrent, fetchAssets]);

  const handleGenerateToken = async () => {
    if (!token) return;
    setActionLoading('generate');
    setError(null);
    setNewToken(null);
    try {
      const res = await fetch(apiConfig.endpoints.tenantAdmin.discovery.token(), {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      });
      const text = await res.text();
      const data = text ? (() => { try { return JSON.parse(text); } catch { return {}; } })() : {};
      if (!res.ok) {
        const msg = Array.isArray(data.detail) ? data.detail.map((x: { msg?: string }) => x.msg).join(', ') : (data.detail || `Failed to generate token (${res.status})`);
        throw new Error(msg);
      }
      if (!data.token) throw new Error('No token in response');
      setNewToken(data.token);
      setTokenStatus({ configured: true });
      setMessage('Token created. Copy it now; it will not be shown again.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate token');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRotateToken = async () => {
    if (!token) return;
    setActionLoading('rotate');
    setError(null);
    setNewToken(null);
    try {
      const res = await fetch(apiConfig.endpoints.tenantAdmin.discovery.tokenRotate(), {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to rotate token');
      setNewToken(data.token);
      setMessage('New token generated. Update the agent config. Old token is invalid.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to rotate token');
    } finally {
      setActionLoading(null);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setMessage('Copied to clipboard');
    setTimeout(() => setMessage(null), 2000);
  };

  const toggleAsset = (id: number) => {
    setSelectedAssetIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllAssets = () => {
    if (selectedAssetIds.size === assets.length) setSelectedAssetIds(new Set());
    else setSelectedAssetIds(new Set(assets.map((a) => a.id)));
  };

  const handleCreateAssets = async () => {
    if (!token || selectedAssetIds.size === 0) {
      setError('Select at least one asset.');
      return;
    }
    setActionLoading('adopt');
    setError(null);
    try {
      const adoptUrl = apiConfig.endpoints.tenantAdmin.discovery.adoptBulk();
      const body = {
        assets: Array.from(selectedAssetIds).map((asset_id) => ({
          asset_id,
          credential_id: null,
          connection_type: 'ssh',
          environment: 'prod',
        })),
      };
      const res = await fetch(adoptUrl, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to create assets');
      const okCount = (data.results || []).filter((r: { ok: boolean }) => r.ok).length;
      setMessage(`Created ${okCount} node(s). Add credentials in Settings & Connections to connect and run runbooks.`);
      setSelectedAssetIds(new Set());
      fetchCurrent();
      fetchAssets();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create assets');
    } finally {
      setActionLoading(null);
    }
  };

  if (!token) {
    return (
      <div className="p-6 text-center text-neutral-600">
        Sign in to manage discovery. Use the same login as the rest of the app.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
      </div>
    );
  }

  const content = (
    <div className={standalone ? 'min-h-screen bg-gradient-to-br from-neutral-50 via-white to-neutral-50' : ''}>
      {standalone && (
        <header className="bg-white border-b border-neutral-200">
          <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.push(backHref)}
                className="p-2 rounded-lg hover:bg-neutral-100"
              >
                <ArrowLeftIcon className="h-5 w-5 text-neutral-600" />
              </button>
              <div className="flex items-center space-x-3">
                <CircleStackIcon className="h-8 w-8 text-primary-600" />
                <div>
                  <h1 className="text-xl font-bold text-neutral-900">Discovery</h1>
                  <p className="text-sm text-neutral-600">Agent token, staged assets, create nodes</p>
                </div>
              </div>
            </div>
          </div>
        </header>
      )}

      <main className={standalone ? 'max-w-7xl mx-auto px-6 py-8 space-y-8' : 'space-y-6'}>
        {error && (
          <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
            <ExclamationTriangleIcon className="h-5 w-5 shrink-0" />
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-auto text-sm underline">Dismiss</button>
          </div>
        )}
        {message && (
          <div className="flex items-center gap-2 p-4 bg-green-50 border border-green-200 rounded-lg text-green-800">
            <CheckCircleIcon className="h-5 w-5 shrink-0" />
            <span>{message}</span>
          </div>
        )}

        <section className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4 flex items-center gap-2">
            <KeyIcon className="h-5 w-5" />
            Agent connection
          </h2>
          <p className="text-sm text-neutral-600 mb-4">
            Generate a token below, then run <strong>one command</strong> on any server (Windows, Linux, or macOS). It installs what it needs and runs full discovery (this host + network + storage). Replace <code>YOUR_TOKEN</code> with the token you copy after generating.
          </p>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">One command (Linux / macOS)</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  readOnly
                  value={oneCommandUnix}
                  className="flex-1 px-3 py-2 border border-neutral-300 rounded-lg bg-neutral-50 text-sm font-mono"
                />
                <button
                  type="button"
                  onClick={() => copyToClipboard(oneCommandUnix)}
                  className="px-3 py-2 border border-neutral-300 rounded-lg hover:bg-neutral-50 flex items-center gap-1 shrink-0"
                >
                  <ClipboardDocumentIcon className="h-4 w-4" /> Copy
                </button>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">One command (Windows PowerShell)</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  readOnly
                  value={oneCommandWindows}
                  className="flex-1 px-3 py-2 border border-neutral-300 rounded-lg bg-neutral-50 text-sm font-mono"
                />
                <button
                  type="button"
                  onClick={() => copyToClipboard(oneCommandWindows)}
                  className="px-3 py-2 border border-neutral-300 rounded-lg hover:bg-neutral-50 flex items-center gap-1 shrink-0"
                >
                  <ClipboardDocumentIcon className="h-4 w-4" /> Copy
                </button>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Ingest URL (for reference)</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  readOnly
                  value={ingestUrl}
                  className="flex-1 px-3 py-2 border border-neutral-300 rounded-lg bg-neutral-50 text-sm"
                />
                <button
                  type="button"
                  onClick={() => copyToClipboard(ingestUrl)}
                  className="px-3 py-2 border border-neutral-300 rounded-lg hover:bg-neutral-50 flex items-center gap-1"
                >
                  <ClipboardDocumentIcon className="h-4 w-4" /> Copy
                </button>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-100 text-neutral-800">
                Token: {tokenStatus?.configured ? 'Configured' : 'Not set'}
              </span>
              {!tokenStatus?.configured ? (
                <button
                  onClick={handleGenerateToken}
                  disabled={!!actionLoading}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {actionLoading === 'generate' ? <ArrowPathIcon className="h-4 w-4 animate-spin" /> : null}
                  Generate token
                </button>
              ) : (
                <button
                  onClick={handleRotateToken}
                  disabled={!!actionLoading}
                  className="px-4 py-2 border border-amber-500 text-amber-700 rounded-lg hover:bg-amber-50 disabled:opacity-50 flex items-center gap-2"
                >
                  {actionLoading === 'rotate' ? <ArrowPathIcon className="h-4 w-4 animate-spin" /> : null}
                  Rotate token
                </button>
              )}
            </div>
            {newToken && (
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-sm font-medium text-amber-900 mb-2">Your token (copy now; it will not be shown again):</p>
                <div className="flex gap-2">
                  <code className="flex-1 break-all text-sm bg-white px-2 py-1 border rounded">{newToken}</code>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(newToken)}
                    className="px-3 py-1 border border-amber-300 rounded hover:bg-amber-100 flex items-center gap-1"
                  >
                    <ClipboardDocumentIcon className="h-4 w-4" /> Copy
                  </button>
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="bg-white rounded-xl border border-neutral-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4 flex items-center gap-2">
            <ServerStackIcon className="h-5 w-5" />
            Runs and staged assets
          </h2>
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
            <strong className="text-blue-900">How discovery works:</strong>{' '}
            Discovery finds and registers machines as nodes. After creating nodes here, add credentials (SSH, cloud, database, etc.) in{' '}
            <Link href={settingsUrl} className="underline font-medium">Settings &amp; Connections</Link>{' '}
            and attach them to nodes to enable runbooks and connectivity.
          </div>
          <div className="mb-4 flex items-center gap-4">
            <p className="text-sm text-neutral-600">
              Current run: {current?.current_run_id ?? 'None'} — {current?.assets_count ?? 0} assets
            </p>
            <button
              onClick={() => Promise.all([fetchRuns(), fetchCurrent(), fetchAssets()])}
              className="text-sm text-primary-600 hover:underline flex items-center gap-1"
            >
              <ArrowPathIcon className="h-4 w-4" /> Refresh
            </button>
          </div>
          {runs.length > 0 && (
            <div className="overflow-x-auto mb-6">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-200">
                    <th className="text-left py-2">ID</th>
                    <th className="text-left py-2">Status</th>
                    <th className="text-left py-2">Started</th>
                    <th className="text-left py-2">Completed</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.slice(0, 10).map((r) => (
                    <tr key={r.id} className="border-b border-neutral-100">
                      <td className="py-2">{r.id}</td>
                      <td className="py-2">{r.status}</td>
                      <td className="py-2">{r.started_at ?? '-'}</td>
                      <td className="py-2">{r.completed_at ?? '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h3 className="text-md font-medium text-neutral-800 mb-2">Staged assets (current run)</h3>
          {assets.length === 0 ? (
            <p className="text-sm text-neutral-500">No staged assets. Run discovery from a VM manager or have the agent send data.</p>
          ) : (
            <>
              <div className="mb-4 flex flex-wrap items-center gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selectedAssetIds.size === assets.length}
                    onChange={selectAllAssets}
                  />
                  <span className="text-sm">Select all</span>
                </label>
                <div className="flex flex-col gap-1">
                  <button
                    onClick={handleCreateAssets}
                    disabled={selectedAssetIds.size === 0 || !!actionLoading}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    title={selectedAssetIds.size === 0 ? 'Select at least one asset (checkbox)' : ''}
                  >
                    {actionLoading === 'adopt' ? <ArrowPathIcon className="h-4 w-4 animate-spin" /> : null}
                    Create nodes ({selectedAssetIds.size} selected)
                  </button>
                  {selectedAssetIds.size === 0 && (
                    <span className="text-xs text-neutral-500">Select assets using the checkboxes above</span>
                  )}
                  {selectedAssetIds.size > 0 && (
                    <span className="text-xs text-neutral-500">
                      Nodes will be created without credentials. Add credentials in{' '}
                      <Link href={settingsUrl} className="underline">Settings &amp; Connections</Link>{' '}
                      to connect and run runbooks.
                    </span>
                  )}
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-neutral-200">
                      <th className="w-10 text-left py-2">
                        <input
                          type="checkbox"
                          checked={selectedAssetIds.size === assets.length && assets.length > 0}
                          onChange={selectAllAssets}
                        />
                      </th>
                      <th className="text-left py-2">ID</th>
                      <th className="text-left py-2">Name</th>
                      <th className="text-left py-2">Source</th>
                      <th className="text-left py-2">Primary IP</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assets.map((a) => (
                      <tr key={a.id} className="border-b border-neutral-100">
                        <td className="py-2">
                          <input
                            type="checkbox"
                            checked={selectedAssetIds.has(a.id)}
                            onChange={() => toggleAsset(a.id)}
                          />
                        </td>
                        <td className="py-2">{a.id}</td>
                        <td className="py-2">{a.name ?? '-'}</td>
                        <td className="py-2">{a.source}</td>
                        <td className="py-2">{a.primary_ip ?? '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );

  return content;
}
