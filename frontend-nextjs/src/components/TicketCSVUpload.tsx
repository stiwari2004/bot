/**
 * Ticket CSV Upload Component
 * Allows users to upload tickets from CSV files
 */
'use client';

import { useState } from 'react';
import { CloudArrowUpIcon, DocumentArrowUpIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';

export function TicketCSVUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [autoExecute, setAutoExecute] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setResult(null);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a CSV file');
      return;
    }

    setUploading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('auto_execute', autoExecute.toString());

      const response = await fetch('/api/v1/tickets/upload-csv', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(errorData.detail || 'Failed to upload CSV');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload CSV');
    } finally {
      setUploading(false);
    }
  };

  const downloadTemplate = () => {
    const csvContent = `title,description,severity,environment,service,source
Database connection timeout,Unable to connect to PostgreSQL database,high,prod,database,prometheus
Server CPU high,CPU usage above 90% on web server,high,prod,server,prometheus
Network latency,High latency between data centers,medium,prod,network,datadog`;

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'tickets_template.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Upload Tickets from CSV</h2>
        <p className="text-gray-600">
          Bulk upload tickets from a CSV file. The system will analyze each ticket and optionally auto-execute matching runbooks.
        </p>
      </div>

      {/* CSV Format Guide */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">CSV Format:</h3>
        <p className="text-sm text-blue-800 mb-2">
          Required columns: <code className="bg-blue-100 px-1 rounded">title</code>, <code className="bg-blue-100 px-1 rounded">description</code>, <code className="bg-blue-100 px-1 rounded">severity</code>
        </p>
        <p className="text-sm text-blue-800 mb-2">
          Optional columns: <code className="bg-blue-100 px-1 rounded">environment</code> (default: prod), <code className="bg-blue-100 px-1 rounded">service</code>, <code className="bg-blue-100 px-1 rounded">source</code> (default: csv_upload)
        </p>
        <button
          onClick={downloadTemplate}
          className="text-sm text-blue-600 hover:text-blue-800 underline"
        >
          Download CSV Template
        </button>
      </div>

      {/* Upload Section */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="space-y-4">
          <div>
            <label htmlFor="csv-file" className="block text-sm font-medium text-gray-700 mb-2">
              Select CSV File
            </label>
            <div className="flex items-center gap-4">
              <input
                id="csv-file"
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="block w-full text-sm text-gray-500
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-lg file:border-0
                  file:text-sm file:font-semibold
                  file:bg-blue-50 file:text-blue-700
                  hover:file:bg-blue-100"
              />
              {file && (
                <span className="text-sm text-gray-600">{file.name}</span>
              )}
            </div>
          </div>

          <div className="flex items-center">
            <input
              id="auto-execute"
              type="checkbox"
              checked={autoExecute}
              onChange={(e) => setAutoExecute(e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor="auto-execute" className="ml-2 block text-sm text-gray-700">
              Auto-execute matching runbooks (confidence ≥0.8)
            </label>
          </div>

          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="w-full flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {uploading ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                Uploading...
              </>
            ) : (
              <>
                <CloudArrowUpIcon className="h-5 w-5 mr-2" />
                Upload Tickets
              </>
            )}
          </button>
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircleIcon className="h-6 w-6 text-green-600" />
            <h3 className="text-lg font-semibold text-green-900">
              Upload Complete: {result.tickets_created?.length || 0} tickets processed
            </h3>
          </div>
          
          {result.tickets_created && result.tickets_created.length > 0 && (
            <div className="space-y-2 mb-4">
              <h4 className="text-sm font-semibold text-green-800">Created Tickets:</h4>
              <div className="max-h-60 overflow-y-auto">
                {result.tickets_created.map((ticket: any, idx: number) => (
                  <div key={idx} className="bg-white p-3 rounded border border-green-200 mb-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{ticket.title}</p>
                        <p className="text-xs text-gray-600">Ticket ID: {ticket.ticket_id}</p>
                      </div>
                      <div className="text-right">
                        <span className={`text-xs px-2 py-1 rounded ${
                          ticket.status === 'resolved' ? 'bg-green-100 text-green-800' :
                          ticket.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {ticket.status}
                        </span>
                        {ticket.auto_executed && (
                          <p className="text-xs text-green-600 mt-1">Auto-executed</p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.errors && result.errors.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-red-800">Errors:</h4>
              {result.errors.map((err: any, idx: number) => (
                <div key={idx} className="bg-white p-3 rounded border border-red-200">
                  <p className="text-sm text-red-800">Row {err.row}: {err.error}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <XCircleIcon className="h-5 w-5 text-red-600" />
            <p className="text-red-800 font-medium">Upload Failed</p>
          </div>
          <p className="text-red-700 mt-2 text-sm">{error}</p>
        </div>
      )}
    </div>
  );
}




