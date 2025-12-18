'use client';

import { useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

/**
 * Dynamic route for customer-specific paths (direct slug)
 * Example: /customer-name redirects to main app
 * The tenant is identified by the slug in the URL
 */
export default function DirectTenantPathPage() {
  const router = useRouter();
  const params = useParams();
  const { isAuthenticated, loading: authLoading } = useAuth();
  const slug = params?.slug as string;

  // List of reserved paths that should not be treated as tenant slugs
  const reservedPaths = [
    'admin',
    'super-admin',
    'tenant-admin',
    'api',
    'c', // The /c/[slug] route
    '_next', // Next.js internal paths
    'favicon.ico',
    'globals.css',
    'page.tsx',
    // Add any other top-level paths that are not tenant slugs
  ];

  useEffect(() => {
    if (authLoading) return;
    if (!slug) return;

    // Check if the slug is a reserved path
    if (reservedPaths.includes(slug.toLowerCase())) {
      // If it's a reserved path, do not treat it as a tenant slug
      // Let Next.js handle it normally (e.g., 404 or other route)
      console.warn(`Attempted to access reserved path as tenant slug: /${slug}`);
      return;
    }

    // If not authenticated, redirect to login with slug context
    if (!isAuthenticated) {
      // Store the slug in sessionStorage so login can redirect back
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('customer_slug', slug);
        router.push(`/?customer_slug=${slug}`);
      }
      return;
    }

    // If authenticated, redirect to main app
    // The tenant context is already set via the user's tenant_id
    router.replace('/');
  }, [slug, isAuthenticated, authLoading, router]);

  // Show loading while redirecting
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-neutral-50 via-white to-neutral-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
        <p className="text-neutral-600">Loading customer portal...</p>
      </div>
    </div>
  );
}
