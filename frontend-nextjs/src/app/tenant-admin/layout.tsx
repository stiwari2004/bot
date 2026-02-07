'use client';

import { MspAdminAuthProvider, useMspAdminAuth } from '@/contexts/MspAdminAuthContext';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect } from 'react';
import {
  HomeIcon,
  BuildingOfficeIcon,
  UserGroupIcon,
  KeyIcon,
  CircleStackIcon,
} from '@heroicons/react/24/outline';

const navItems = [
  { href: '/tenant-admin', label: 'Home', icon: HomeIcon },
  { href: '/tenant-admin/customers', label: 'Customers', icon: BuildingOfficeIcon },
  { href: '/tenant-admin/users', label: 'Users', icon: UserGroupIcon },
  { href: '/tenant-admin/subscriptions', label: 'Subscriptions', icon: KeyIcon },
  { href: '/tenant-admin/discovery', label: 'Discovery', icon: CircleStackIcon },
];

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

  // Show content if authenticated, with nav tabs
  if (isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-neutral-50">
        <nav className="sticky top-0 z-40 border-b border-neutral-200 bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            <div className="flex gap-1 overflow-x-auto">
              {navItems.map(({ href, label, icon: Icon }) => {
                const isActive =
                  href === '/tenant-admin'
                    ? pathname === '/tenant-admin'
                    : pathname.startsWith(href);
                return (
                  <button
                    key={href}
                    onClick={() => router.push(href)}
                    className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                      isActive
                        ? 'border-primary-600 text-primary-600'
                        : 'border-transparent text-neutral-600 hover:text-neutral-900 hover:border-neutral-300'
                    }`}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
        </nav>
        {children}
      </div>
    );
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

