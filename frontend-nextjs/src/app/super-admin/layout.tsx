'use client';

import { SuperAdminAuthProvider } from '@/contexts/SuperAdminAuthContext';
import { useSuperAdminAuth } from '@/contexts/SuperAdminAuthContext';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect } from 'react';

function SuperAdminLayoutContent({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useSuperAdminAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && typeof window !== 'undefined') {
      // If not on login page and not authenticated, redirect to login
      if (pathname !== '/super-admin/login' && !isAuthenticated) {
        router.push('/super-admin/login');
      }
      // If on login page and authenticated, redirect to dashboard
      if (pathname === '/super-admin/login' && isAuthenticated) {
        router.push('/super-admin');
      }
    }
  }, [isAuthenticated, loading, pathname, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-neutral-50 via-white to-neutral-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-neutral-600 font-medium">Loading...</p>
        </div>
      </div>
    );
  }

  // Allow login page to render without auth check
  if (pathname === '/super-admin/login') {
    return <>{children}</>;
  }

  // For other pages, require authentication
  if (!isAuthenticated) {
    return null; // Will redirect in useEffect
  }

  return <>{children}</>;
}

export default function SuperAdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <SuperAdminAuthProvider>
      <SuperAdminLayoutContent>{children}</SuperAdminLayoutContent>
    </SuperAdminAuthProvider>
  );
}

