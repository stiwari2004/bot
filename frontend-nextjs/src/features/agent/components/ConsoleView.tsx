'use client';

import { useRef, useEffect } from 'react';
import type { ConsoleLine } from '../types';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';

interface ConsoleViewProps {
  lines: ConsoleLine[];
}

const consoleToneStyles: Record<string, string> = {
  prompt: 'text-sky-300',
  success: 'text-emerald-300',
  error: 'text-red-300',
  warning: 'text-amber-300',
  info: 'text-cyan-300',
  output: 'text-gray-100',
};

export function ConsoleView({ lines }: ConsoleViewProps) {
  const consoleRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [lines]);

  return (
    <Card variant="elevated">
      <CardHeader>
        <h3 className="text-sm font-semibold text-neutral-800">
          Live Console
        </h3>
      </CardHeader>
      <CardContent padding="none">
        <div
          ref={consoleRef}
          className="h-48 overflow-y-auto rounded-lg bg-neutral-950 px-4 py-3 font-mono text-sm text-neutral-100 shadow-inner"
        >
          {lines.length === 0 ? (
            <div className="text-neutral-400 text-sm text-center py-8">
              Waiting for activity…
            </div>
          ) : (
            lines.map((line) => (
              <div
                key={line.key}
                className="flex items-start gap-2 py-0.5"
              >
                <span className="w-20 shrink-0 text-right text-[11px] text-neutral-400">
                  {line.timestamp ? `[${line.timestamp}]` : ''}
                </span>
                <div className="flex-1">
                  <span
                    className={`block leading-snug ${
                      consoleToneStyles[line.tone] ?? consoleToneStyles.info
                    }`}
                  >
                    {line.text}
                  </span>
                  {line.meta && (
                    <span className="block text-[11px] text-neutral-400">
                      {line.meta}
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}



