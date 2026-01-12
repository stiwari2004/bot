'use client';

import { useState, useEffect } from 'react';

interface ProvisioningProject {
  id: number;
  name: string;
  description?: string;
  provider: string;
  state: string;
  created_at: string;
  updated_at?: string;
}

export function ProvisioningDashboard() {
  const [projects, setProjects] = useState<ProvisioningProject[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/v1/provisioning/projects', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch projects');
      }
      const data = await response.json();
      setProjects(data.projects || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const stateColors = {
    pending: 'bg-gray-100 text-gray-800',
    provisioning: 'bg-blue-100 text-blue-800',
    active: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    destroyed: 'bg-gray-100 text-gray-600',
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Infrastructure Provisioning</h2>
        <button
          onClick={() => {/* TODO: Open provisioning wizard */}}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Provision Infrastructure
        </button>
      </div>

      {loading && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading projects...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-800">Error: {error}</p>
        </div>
      )}

      {!loading && !error && projects.length === 0 && (
        <div className="text-center py-8 bg-gray-50 rounded-lg">
          <p className="text-gray-600">No provisioning projects found</p>
        </div>
      )}

      {!loading && !error && projects.length > 0 && (
        <div className="grid gap-4">
          {projects.map(project => (
            <div
              key={project.id}
              className="border rounded-lg p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-lg">{project.name}</h3>
                  {project.description && (
                    <p className="text-sm text-gray-600 mt-1">{project.description}</p>
                  )}
                  <p className="text-sm mt-2">
                    Provider: <span className="font-medium">{project.provider}</span>
                  </p>
                  <p className="text-sm text-gray-500 mt-2">
                    Created: {new Date(project.created_at).toLocaleString()}
                  </p>
                </div>
                <div className="text-right">
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold capitalize ${
                    stateColors[project.state as keyof typeof stateColors] || 'bg-gray-200'
                  }`}>
                    {project.state}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

