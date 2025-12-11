'use client';

import { MspAdminAuthProvider, useMspAdminAuth } from '@/contexts/MspAdminAuthContext';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect } from 'react';

function MspAdminLayoutContent({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, loading } = useMspAdminAuth();

  useEffect(() => {
    if (loading) return;

    // Redirect to login if not authenticated (except on login page)
    if (pathname !== '/tenant-admin/login' && !isAuthenticated) {
      router.push('/tenant-admin/login');
    }

    // Redirect to dashboard if authenticated and on login page
    if (pathname === '/tenant-admin/login' && isAuthenticated) {
      router.push('/tenant-admin');
    }
  }, [isAuthenticated, loading, pathname, router]);

  // Show loading while checking auth
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-neutral-50 via-white to-neutral-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-neutral-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Show login page if not authenticated
  if (pathname === '/tenant-admin/login') {
    return <>{children}</>;
  }

  // Show content if authenticated
  if (isAuthenticated) {
    return <>{children}</>;
  }

  // Default: show nothing (will redirect)
  return null;
}

export default function MspAdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <MspAdminAuthProvider>
      <MspAdminLayoutContent>{children}</MspAdminLayoutContent>
    </MspAdminAuthProvider>
  );
}

