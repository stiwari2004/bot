'use client';

import { useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

/**
 * Dynamic route for tenant-specific paths
 * Example: /ritwik redirects to main app with tenant context
 * The tenant is identified by the slug in the URL
 * 
 * This route handles direct tenant access like resolvify.tech/ritwik
 * Reserved paths (admin, super-admin, tenant-admin, api, c) are handled by other routes
 */
export default function TenantSlugPage() {
  const router = useRouter();
  const params = useParams();
  const { isAuthenticated, loading: authLoading } = useAuth();
  const slug = params?.slug as string;

  useEffect(() => {
    if (authLoading) return;

    // Reserved paths should not be handled here (they have their own routes)
    const reservedPaths = ['admin', 'super-admin', 'tenant-admin', 'api', 'c', 'health'];
    if (reservedPaths.includes(slug?.toLowerCase())) {
      return; // Let Next.js handle these with their specific routes
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
        <p className="text-neutral-600">Loading tenant portal...</p>
      </div>
    </div>
  );
}

