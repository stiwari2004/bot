'use client';

import type { ExecutionEventRecord } from '../hooks/useExecutionEvents';
import { buildTranscriptEntry, createEventKey, formatDate, transcriptStyles } from '../services/utils';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';

interface EventStreamViewProps {
  events: ExecutionEventRecord[];
}

export function EventStreamView({ events }: EventStreamViewProps) {
  return (
    <Card variant="elevated">
      <CardHeader>
        <h3 className="text-sm font-semibold text-neutral-800">
          Event Stream
        </h3>
      </CardHeader>
      <CardContent padding="md">
        <div className="max-h-64 overflow-y-auto pr-2 text-sm space-y-3">
          {events.length === 0 ? (
            <div className="text-neutral-500 text-sm text-center py-8">
              Waiting for events…
            </div>
          ) : (
            events.map((evt) => {
              const entry = buildTranscriptEntry(evt);
              const style = transcriptStyles[entry.variant] || transcriptStyles.neutral;
              const Icon = entry.icon;
              return (
                <Card
                  key={createEventKey(evt)}
                  variant="outlined"
                  className={`${style.container}`}
                >
                  <CardContent padding="sm">
                    <div className="flex items-center justify-between gap-3 mb-2">
                      <div className="flex items-center gap-2">
                        <Icon className={`h-4 w-4 ${style.icon}`} />
                        <span
                          className={`text-sm font-semibold ${style.title}`}
                        >
                          {entry.title}
                        </span>
                      </div>
                      <span className="text-[11px] text-neutral-500">
                        {entry.timestamp ? formatDate(entry.timestamp) : ''}
                      </span>
                    </div>
                    {entry.summary && (
                      <p className="mt-2 text-sm text-neutral-700">
                        {entry.summary}
                      </p>
                    )}
                    {entry.meta && (
                      <dl className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-xs">
                        {entry.meta.map((item, idx) => (
                          <div
                            key={`${createEventKey(evt)}-meta-${idx}`}
                            className="flex items-center justify-between gap-2"
                          >
                            <dt className="text-neutral-500">{item.label}</dt>
                            <dd className="text-neutral-700 font-semibold">
                              {item.value}
                            </dd>
                          </div>
                        ))}
                      </dl>
                    )}
                    {entry.detail && (
                      <pre className="mt-3 text-xs text-neutral-800 bg-white border-2 border-neutral-200 rounded-lg p-3 whitespace-pre-wrap">
                        {entry.detail}
                      </pre>
                    )}
                    {entry.raw && (
                      <details className="mt-3 text-xs text-neutral-500">
                        <summary className="cursor-pointer text-neutral-600 hover:text-neutral-800 font-semibold">
                          View raw event payload
                        </summary>
                        <pre className="mt-2 bg-neutral-100 border-2 border-neutral-200 rounded-lg p-3 whitespace-pre-wrap text-neutral-700">
                          {entry.raw}
                        </pre>
                      </details>
                    )}
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}



