/**
 * View: Status message components (loading, error, first request notice)
 */
'use client';

import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface StatusMessagesProps {
  firstRequest: boolean;
  loading: boolean;
  error: string | null;
  onDismissError: () => void;
}

export function StatusMessages({ firstRequest, loading, error, onDismissError }: StatusMessagesProps) {
  return (
    <>
      {firstRequest && !loading && (
        <Card variant="elevated" className="bg-warning-50 border-warning-200">
          <CardContent padding="md">
            <div className="flex items-start">
              <ExclamationTriangleIcon className="h-5 w-5 text-warning-600 mr-2 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-warning-800 font-semibold">First Request Notice</p>
                <p className="text-warning-700 text-sm mt-1">
                  The first analysis may take 1-2 minutes to load the AI model. Subsequent requests will be much faster.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {loading && (
        <Card variant="elevated" className="bg-primary-50 border-primary-200">
          <CardContent padding="md">
            <div className="flex items-center">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600 mr-3"></div>
              <div>
                <p className="text-primary-800 font-semibold">Analyzing ticket...</p>
                <p className="text-primary-700 text-sm mt-1">
                  Searching runbooks and computing recommendations
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {error && (
        <Card variant="elevated" className="bg-error-50 border-error-200">
          <CardContent padding="md">
            <div className="flex items-start">
              <ExclamationTriangleIcon className="h-5 w-5 text-error-600 mr-2 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-error-800 font-semibold mb-1">Analysis Failed</p>
                <p className="text-error-700 text-sm">{error}</p>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onDismissError}
                  className="mt-2"
                >
                  Dismiss
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </>
  );
}





