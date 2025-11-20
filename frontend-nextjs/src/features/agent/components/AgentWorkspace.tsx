'use client';

import { FormEvent } from 'react';
import { BoltIcon, ServerIcon, SignalIcon, WifiIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { useAgentWorkspace } from '../hooks/useAgentWorkspace';
import { SessionSidebar } from './SessionSidebar';
import { SessionDetailView } from './SessionDetailView';
import { ConsoleView } from './ConsoleView';
import { EventStreamView } from './EventStreamView';
import { ManualCommandPanel } from './ManualCommandPanel';
import type { ConnectorType } from '../types';

interface AgentWorkspaceProps {
  initialSessionId?: number | null;
}

export function AgentWorkspace({ initialSessionId = null }: AgentWorkspaceProps) {
  const workspaceEnabled = process.env.NEXT_PUBLIC_AGENT_WORKSPACE_ENABLED !== 'false';

  const {
    sessions,
    loadingSessions,
    sessionError,
    activeSessionId,
    setActiveSessionId,
    fetchSessions,
    activeSession,
    loadingDetail,
    detailError,
    connectionInfo,
    controlBusy,
    controlError,
    handleControlAction,
    stepActionBusy,
    stepActionError,
    handleStepApproval,
    consoleLines,
    eventHistory,
    commandInput,
    setCommandInput,
    commandReason,
    setCommandReason,
    commandSubmitting,
    commandError,
    handleManualCommandSubmit,
    connectModalOpen,
    setConnectModalOpen,
    connectConnectorType,
    setConnectConnectorType,
    connectHost,
    setConnectHost,
    connectPort,
    setConnectPort,
    connectUsername,
    setConnectUsername,
    connectPassword,
    setConnectPassword,
    connectCredentialAlias,
    setConnectCredentialAlias,
    connectSubmitting,
    connectError,
    handleConnectSubmit,
  } = useAgentWorkspace({ initialSessionId });

  if (!workspaceEnabled) {
    return (
      <div className="p-6 text-center">
        <BoltIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Agent Workspace Disabled</h3>
        <p className="text-gray-600">
          The Agent Workspace feature is currently disabled. Enable it by setting{' '}
          <code className="bg-gray-100 px-2 py-1 rounded">NEXT_PUBLIC_AGENT_WORKSPACE_ENABLED=true</code>
        </p>
      </div>
    );
  }

  const supportsPort = connectConnectorType === 'ssh' || connectConnectorType === 'winrm';
  const supportsUsername = connectConnectorType === 'ssh' || connectConnectorType === 'winrm';
  const supportsPassword = connectConnectorType === 'ssh' || connectConnectorType === 'winrm';
  const isWinRM = connectConnectorType === 'winrm';
  const usernamePlaceholder = isWinRM ? 'Administrator' : 'root';

  return (
    <>
      {connectModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-semibold text-gray-900">Connect to Infrastructure</h3>
                <button
                  onClick={() => setConnectModalOpen(false)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>

              {connectError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
                  {connectError}
                </div>
              )}

              <form
                onSubmit={(e: FormEvent) => {
                  e.preventDefault();
                  handleConnectSubmit();
                }}
                className="space-y-4"
              >
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Connection Type *
                  </label>
                  <select
                    value={connectConnectorType}
                    onChange={(e) => setConnectConnectorType(e.target.value as ConnectorType)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  >
                    <option value="ssh">SSH</option>
                    <option value="winrm">WinRM</option>
                    <option value="azure_bastion">Azure Bastion</option>
                    <option value="gcp_iap">GCP IAP</option>
                    <option value="aws_ssm">AWS SSM</option>
                    <option value="network_cluster">Network Cluster</option>
                    <option value="network_device">Network Device</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Host *
                  </label>
                  <input
                    type="text"
                    value={connectHost}
                    onChange={(e) => setConnectHost(e.target.value)}
                    disabled={connectSubmitting}
                    placeholder="Hostname or IP address"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    required
                  />
                </div>

                {supportsPort && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Port
                    </label>
                    <input
                      type="text"
                      value={connectPort}
                      onChange={(e) => setConnectPort(e.target.value)}
                      disabled={connectSubmitting}
                      placeholder={isWinRM ? '5985' : '22'}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    />
                  </div>
                )}

                {supportsUsername && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Username
                    </label>
                    <input
                      type="text"
                      value={connectUsername}
                      onChange={(e) => setConnectUsername(e.target.value)}
                      disabled={connectSubmitting}
                      placeholder={usernamePlaceholder}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    />
                  </div>
                )}

                {supportsPassword && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Password
                    </label>
                    <input
                      type="password"
                      value={connectPassword}
                      onChange={(e) => setConnectPassword(e.target.value)}
                      disabled={connectSubmitting}
                      placeholder="Password"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    />
                  </div>
                )}

                <div className="flex items-center justify-end gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setConnectModalOpen(false)}
                    className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={connectSubmitting}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {connectSubmitting ? 'Connecting...' : 'Connect'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      <div className="grid lg:grid-cols-[320px,1fr] gap-4">
        <SessionSidebar
          sessions={sessions}
          loading={loadingSessions}
          error={sessionError}
          activeSessionId={activeSessionId}
          onSelectSession={setActiveSessionId}
          onRefresh={fetchSessions}
        />

        <section className="bg-white border border-gray-200 rounded-2xl shadow-sm p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Live Execution Feed</h2>
              <p className="text-sm text-gray-600 mt-1">
                Monitor and interact with active execution sessions
              </p>
            </div>
            <button
              onClick={() => setConnectModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <ServerIcon className="h-5 w-5" />
              Connect to CI
            </button>
          </div>

          {loadingDetail || detailError || !activeSession ? (
            <div className="text-center py-12">
              {loadingDetail ? (
                <div className="flex flex-col items-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
                  <p className="text-gray-600">Loading session details...</p>
                </div>
              ) : detailError ? (
                <div className="text-red-600">
                  <p className="font-medium">Error loading session</p>
                  <p className="text-sm mt-2">{detailError}</p>
                </div>
              ) : (
                <div className="text-gray-500">
                  <BoltIcon className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                  <p>Select a session from the sidebar to view details</p>
                </div>
              )}
            </div>
          ) : (
            <SessionDetailView
              session={activeSession}
              connectionInfo={connectionInfo}
              controlBusy={controlBusy}
              controlError={controlError}
              stepActionBusy={stepActionBusy}
              stepActionError={stepActionError}
              onControlAction={handleControlAction}
              onStepApproval={handleStepApproval}
            />
          )}

          <ConsoleView
            lines={consoleLines}
          />

          <EventStreamView
            events={eventHistory}
          />

          <ManualCommandPanel
            connectionInfo={connectionInfo}
            commandInput={commandInput}
            setCommandInput={setCommandInput}
            commandReason={commandReason}
            setCommandReason={setCommandReason}
            commandSubmitting={commandSubmitting}
            commandError={commandError}
            onSubmit={handleManualCommandSubmit}
            disabled={!activeSessionId}
          />
        </section>
      </div>
    </>
  );
}

