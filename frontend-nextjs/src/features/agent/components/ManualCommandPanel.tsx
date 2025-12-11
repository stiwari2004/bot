'use client';

import { FormEvent } from 'react';
import type { ConnectionInfo } from '../types';
import { formatShortDuration } from '../services/utils';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface ManualCommandPanelProps {
  connectionInfo: ConnectionInfo;
  commandInput: string;
  setCommandInput: (cmd: string) => void;
  commandReason: string;
  setCommandReason: (reason: string) => void;
  commandSubmitting: boolean;
  commandError: string | null;
  onSubmit: () => void;
  disabled?: boolean;
}

export function ManualCommandPanel({
  connectionInfo,
  commandInput,
  setCommandInput,
  commandReason,
  setCommandReason,
  commandSubmitting,
  commandError,
  onSubmit,
  disabled = false,
}: ManualCommandPanelProps) {
  const connectorVariant = connectionInfo.connector?.toLowerCase();
  
  const commandConsoleLabel = connectionInfo.host
    ? `Manual Command: ${connectionInfo.host}`
    : 'Manual Command';

  const commandPlaceholder =
    connectorVariant === 'winrm'
      ? 'Get-Process | Where-Object { $_.CPU -gt 100 }'
      : connectorVariant === 'ssh' || connectorVariant === 'aws_ssm'
      ? 'ps aux | head -20'
      : connectorVariant === 'network_cluster'
      ? 'show version'
      : connectorVariant === 'network_device'
      ? 'show interfaces status'
      : connectorVariant === 'azure_bastion' || connectorVariant === 'gcp_iap'
      ? 'uptime'
      : 'command...';

  const helpText = (() => {
    if (connectorVariant === 'winrm') {
      return 'Send inline PowerShell to the connected Windows host. Use ⌘/Ctrl + Enter to send.';
    }
    if (connectorVariant === 'ssh') {
      return 'Send shell commands over SSH. Use ⌘/Ctrl + Enter to send.';
    }
    if (connectorVariant === 'aws_ssm') {
      return 'Broadcast commands via AWS Systems Manager Session Manager. Use ⌘/Ctrl + Enter to send.';
    }
    if (connectorVariant === 'network_cluster') {
      return 'Send controller commands to the selected network cluster. Use ⌘/Ctrl + Enter to dispatch.';
    }
    if (connectorVariant === 'network_device') {
      return 'Queue CLI commands for the connected network device. Use ⌘/Ctrl + Enter to dispatch.';
    }
    if (connectorVariant === 'azure_bastion') {
      return 'Run shell commands via Azure Bastion tunnel. Use ⌘/Ctrl + Enter to send.';
    }
    if (connectorVariant === 'gcp_iap') {
      return 'Run shell commands over GCP Identity-Aware Proxy. Use ⌘/Ctrl + Enter to send.';
    }
    return 'Queue ad-hoc commands for the assigned worker. Use ⌘/Ctrl + Enter to send.';
  })();

  return (
    <Card variant="outlined">
      <CardContent padding="md">
        <h3 className="text-sm font-semibold text-neutral-800 mb-2">
          {commandConsoleLabel}
        </h3>
        <p className="text-xs text-neutral-600 mb-4">
          {helpText}
        </p>
        <form
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            void onSubmit();
          }}
          className="space-y-3"
        >
          <div>
            <label
              htmlFor="workspace-command"
              className="block text-xs font-semibold text-neutral-700 mb-2 uppercase tracking-wide"
            >
              Command
            </label>
            <textarea
              id="workspace-command"
              value={commandInput}
              onChange={(event) => setCommandInput(event.target.value)}
              disabled={commandSubmitting || disabled}
              rows={3}
              className="w-full rounded-lg border border-neutral-300 px-3 py-2 font-mono text-sm text-neutral-900 shadow-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500 disabled:bg-neutral-100 disabled:text-neutral-400 transition-all"
              placeholder={commandPlaceholder}
              onKeyDown={(event) => {
                if (
                  (event.metaKey || event.ctrlKey) &&
                  event.key === 'Enter'
                ) {
                  event.preventDefault();
                  void onSubmit();
                }
              }}
            />
          </div>
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              type="text"
              placeholder="Reason (optional)"
              value={commandReason}
              onChange={(event) => setCommandReason(event.target.value)}
              disabled={commandSubmitting}
              className="flex-1 rounded-lg border border-neutral-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500 disabled:bg-neutral-100 disabled:text-neutral-400 text-neutral-900 transition-all"
            />
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={commandSubmitting || !commandInput.trim() || disabled}
              isLoading={commandSubmitting}
            >
              {commandSubmitting ? 'Queueing…' : 'Queue Command'}
            </Button>
          </div>
        </form>
        {commandError && (
          <p className="mt-3 text-xs text-error-600 font-medium">{commandError}</p>
        )}
      </CardContent>
    </Card>
  );
}



