'use client';

import { useState } from 'react';
import { CloudArrowUpIcon, DocumentTextIcon } from '@heroicons/react/24/outline';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';

interface FileUploadProps {
  onFileUploaded?: () => void;
}

export function FileUpload({ onFileUploaded }: FileUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [sourceType, setSourceType] = useState('doc');
  const [title, setTitle] = useState('');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const sourceTypes = [
    { value: 'doc', label: 'Documentation' },
    { value: 'log', label: 'Log File' },
    { value: 'slack', label: 'Slack' },
    { value: 'csv', label: 'CSV' },
    { value: 'json', label: 'JSON' },
    { value: 'txt', label: 'Text' },
    { value: 'md', label: 'Markdown' },
  ];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      if (!title) {
        setTitle(selectedFile.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('source_type', sourceType);
      if (title) formData.append('title', title);

      const response = await fetch(`/api/v1/demo/upload-demo`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const data = await response.json();
      setResult(data);
      onFileUploaded?.();
      
      // Reset form
      setFile(null);
      setTitle('');
      setSourceType('doc');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-neutral-900 mb-2 flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-primary-100">
            <CloudArrowUpIcon className="h-7 w-7 text-primary-600" />
          </div>
          Upload Documents
        </h2>
        <p className="text-neutral-600">
          Upload documentation, logs, and other files to build the knowledge base for runbook generation.
          <strong className="text-primary-600 block mt-2">Note: For tickets, use the Tickets tab after configuring ticketing tool connections in Settings & Connections.</strong>
        </p>
      </div>

      <Card variant="elevated">
        <CardContent padding="md">
          <form onSubmit={handleUpload} className="space-y-6">
            <div>
              <label htmlFor="file" className="block text-sm font-semibold text-neutral-700 mb-2">
                Select File
              </label>
              <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-neutral-300 border-dashed rounded-lg hover:border-primary-400 transition-colors bg-neutral-50">
                <div className="space-y-1 text-center">
                  <CloudArrowUpIcon className="mx-auto h-12 w-12 text-neutral-400" />
                  <div className="flex text-sm text-neutral-600">
                    <label
                      htmlFor="file"
                      className="relative cursor-pointer bg-white rounded-md font-medium text-primary-600 hover:text-primary-700 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-primary-500"
                    >
                      <span>Upload a file</span>
                      <input
                        id="file"
                        name="file"
                        type="file"
                        className="sr-only"
                        onChange={handleFileChange}
                        accept=".txt,.md,.csv,.json,.log"
                      />
                    </label>
                    <p className="pl-1">or drag and drop</p>
                  </div>
                  <p className="text-xs text-neutral-500">TXT, MD, CSV, JSON, LOG up to 10MB</p>
                </div>
              </div>
              {file && (
                <div className="mt-3 flex items-center text-sm text-neutral-700 bg-neutral-50 p-2 rounded-lg">
                  <DocumentTextIcon className="h-4 w-4 mr-2 text-primary-600" />
                  <span className="font-medium">{file.name}</span>
                  <span className="ml-2 text-neutral-500">({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="source-type" className="block text-sm font-semibold text-neutral-700 mb-2">
                  Source Type
                </label>
                <Select value={sourceType} onValueChange={setSourceType}>
                  <SelectTrigger id="source-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {sourceTypes.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label htmlFor="title" className="block text-sm font-semibold text-neutral-700 mb-2">
                  Title (Optional)
                </label>
                <Input
                  type="text"
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Custom title for this file"
                />
              </div>
            </div>

            <div>
              <Button
                type="submit"
                variant="primary"
                disabled={!file || uploading}
                isLoading={uploading}
                leftIcon={<CloudArrowUpIcon className="h-5 w-5" />}
                className="w-full"
              >
                {uploading ? 'Uploading...' : 'Upload & Process'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {error && (
        <Card variant="outlined" className="mt-6 border-error-200 bg-error-50">
          <CardContent padding="sm">
            <p className="text-error-800 font-medium">{error}</p>
          </CardContent>
        </Card>
      )}

      {result && (
        <Card variant="outlined" className="mt-6 border-success-200 bg-success-50">
          <CardContent padding="md">
            <h3 className="text-lg font-semibold text-success-800 mb-3">Upload Successful!</h3>
            <div className="text-sm text-success-700 space-y-1">
              <p><span className="font-semibold">Document ID:</span> {result.document_id}</p>
              <p><span className="font-semibold">Chunks Created:</span> {result.chunks_created}</p>
              <p><span className="font-semibold">Status:</span> {result.message}</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
