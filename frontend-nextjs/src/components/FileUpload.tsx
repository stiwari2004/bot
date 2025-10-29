'use client';

import { useState } from 'react';
import { CloudArrowUpIcon, DocumentTextIcon } from '@heroicons/react/24/outline';

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
    { value: 'ticket', label: 'Ticket' },
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

      const response = await fetch('http://localhost:8000/api/v1/demo/upload-demo', {
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
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Upload Knowledge Files</h2>
        <p className="text-gray-600">Upload documents, logs, tickets, and other files to build your knowledge base</p>
      </div>

      <form onSubmit={handleUpload} className="space-y-6">
        <div>
          <label htmlFor="file" className="block text-sm font-medium text-gray-700 mb-2">
            Select File
          </label>
          <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-lg hover:border-gray-400 transition-colors">
            <div className="space-y-1 text-center">
              <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
              <div className="flex text-sm text-gray-600">
                <label
                  htmlFor="file"
                  className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-blue-500"
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
              <p className="text-xs text-gray-500">TXT, MD, CSV, JSON, LOG up to 10MB</p>
            </div>
          </div>
          {file && (
            <div className="mt-2 flex items-center text-sm text-gray-600">
              <DocumentTextIcon className="h-4 w-4 mr-2" />
              {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="source-type" className="block text-sm font-medium text-gray-700 mb-2">
              Source Type
            </label>
            <select
              id="source-type"
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value)}
              className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              {sourceTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
              Title (Optional)
            </label>
            <input
              type="text"
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Custom title for this file"
              className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        <div>
          <button
            type="submit"
            disabled={!file || uploading}
            className="w-full flex justify-center items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <CloudArrowUpIcon className="h-5 w-5 mr-2" />
            {uploading ? 'Uploading...' : 'Upload & Process'}
          </button>
        </div>
      </form>

      {error && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {result && (
        <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <h3 className="text-lg font-medium text-green-800 mb-2">Upload Successful!</h3>
          <div className="text-sm text-green-700">
            <p>Document ID: {result.document_id}</p>
            <p>Chunks Created: {result.chunks_created}</p>
            <p>Status: {result.message}</p>
          </div>
        </div>
      )}
    </div>
  );
}
