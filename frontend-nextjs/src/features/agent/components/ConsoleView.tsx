'use client';

import { useRef, useEffect } from 'react';
import type { ConsoleLine } from '../types';

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
    <div className="border border-gray-200 rounded-xl p-4">
      <h3 className="text-sm font-semibold text-gray-800 mb-2">
        Live Console
      </h3>
      <div
        ref={consoleRef}
        className="mt-2 h-48 overflow-y-auto rounded-lg bg-gray-950 px-3 py-2 font-mono text-sm text-gray-100 shadow-inner"
      >
        {lines.length === 0 ? (
          <div className="text-gray-500 text-sm">
            Waiting for activity…
          </div>
        ) : (
          lines.map((line) => (
            <div
              key={line.key}
              className="flex items-start gap-2 py-0.5"
            >
              <span className="w-20 shrink-0 text-right text-[11px] text-gray-500">
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
                  <span className="block text-[11px] text-gray-400">
                    {line.meta}
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}



