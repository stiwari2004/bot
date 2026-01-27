'use client';

import { HumanInLoopWorkspace } from '@/components/workspace/HumanInLoopWorkspace';

export default function WorkspacePage() {
  return (
    <div className="container mx-auto py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-900">Human-in-the-Loop Workspace</h1>
        <p className="text-sm text-neutral-600 mt-1">
          Manage pending approvals, tune parameters, and review audit trails
        </p>
      </div>
      <HumanInLoopWorkspace />
    </div>
  );
}
