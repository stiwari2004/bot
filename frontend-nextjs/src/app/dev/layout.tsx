'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import Link from 'next/link';
import { 
  CodeBracketIcon,
  CheckCircleIcon,
  ClockIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline';

export default function DevLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!user) {
      router.push('/');
    }
  }, [user, router]);

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-neutral-50">
      {/* Header */}
      <header className="bg-white border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="rounded-xl bg-gradient-to-br from-yellow-500 to-orange-500 p-2.5 shadow-lg">
                  <CodeBracketIcon className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-neutral-900">Dev Environment</h1>
                  <p className="text-sm text-neutral-600">Development & Testing</p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-sm font-medium text-neutral-900">{user.email}</p>
                <p className="text-xs text-neutral-600">Developer</p>
              </div>
              <button
                onClick={logout}
                className="flex items-center space-x-2 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-100 rounded-lg transition"
              >
                <ArrowRightOnRectangleIcon className="h-5 w-5" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex space-x-1">
            <Link
              href="/dev/runbooks"
              className="px-4 py-3 text-sm font-medium text-neutral-700 hover:text-neutral-900 hover:bg-neutral-50 border-b-2 border-transparent hover:border-primary-500 transition"
            >
              Runbooks
            </Link>
            <Link
              href="/dev/approvals"
              className="px-4 py-3 text-sm font-medium text-neutral-700 hover:text-neutral-900 hover:bg-neutral-50 border-b-2 border-transparent hover:border-primary-500 transition flex items-center space-x-2"
            >
              <ClockIcon className="h-4 w-4" />
              <span>Approvals</span>
            </Link>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {children}
      </main>
    </div>
  );
}

