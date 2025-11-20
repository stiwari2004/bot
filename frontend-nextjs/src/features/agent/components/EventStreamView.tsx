'use client';

import type { ExecutionEventRecord } from '../hooks/useExecutionEvents';
import { buildTranscriptEntry, createEventKey, formatDate, transcriptStyles } from '../services/utils';

interface EventStreamViewProps {
  events: ExecutionEventRecord[];
}

export function EventStreamView({ events }: EventStreamViewProps) {
  return (
    <div className="border border-gray-200 rounded-xl p-4">
      <h3 className="text-sm font-semibold text-gray-800 mb-2">
        Event Stream
      </h3>
      <div className="max-h-64 overflow-y-auto pr-2 text-sm space-y-3">
        {events.length === 0 ? (
          <div className="text-gray-500 text-sm">
            Waiting for events…
          </div>
        ) : (
          events.map((evt) => {
            const entry = buildTranscriptEntry(evt);
            const style = transcriptStyles[entry.variant] || transcriptStyles.neutral;
            const Icon = entry.icon;
            return (
              <div
                key={createEventKey(evt)}
                className={`rounded-xl border px-3 py-3 ${style.container}`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <Icon className={`h-4 w-4 ${style.icon}`} />
                    <span
                      className={`text-sm font-semibold ${style.title}`}
                    >
                      {entry.title}
                    </span>
                  </div>
                  <span className="text-[11px] text-gray-500">
                    {entry.timestamp ? formatDate(entry.timestamp) : ''}
                  </span>
                </div>
                {entry.summary && (
                  <p className="mt-1 text-sm text-gray-700">
                    {entry.summary}
                  </p>
                )}
                {entry.meta && (
                  <dl className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-500">
                    {entry.meta.map((item, idx) => (
                      <div
                        key={`${createEventKey(evt)}-meta-${idx}`}
                        className="flex items-center justify-between gap-2"
                      >
                        <dt className="text-gray-500">{item.label}</dt>
                        <dd className="text-gray-700 font-medium">
                          {item.value}
                        </dd>
                      </div>
                    ))}
                  </dl>
                )}
                {entry.detail && (
                  <pre className="mt-2 text-xs text-gray-800 bg-white border border-gray-200 rounded-lg p-3 whitespace-pre-wrap">
                    {entry.detail}
                  </pre>
                )}
                {entry.raw && (
                  <details className="mt-2 text-xs text-gray-500">
                    <summary className="cursor-pointer text-gray-600 hover:text-gray-800">
                      View raw event payload
                    </summary>
                    <pre className="mt-2 bg-gray-100 border border-gray-200 rounded-lg p-3 whitespace-pre-wrap text-gray-700">
                      {entry.raw}
                    </pre>
                  </details>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}



