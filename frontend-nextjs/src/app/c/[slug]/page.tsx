'use client';

import { useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

/**
 * Dynamic route for customer-specific paths
 * Example: /c/customer-name redirects to main app
 * The tenant is identified by the slug in the URL
 */
export default function CustomerPathPage() {
  const router = useRouter();
  const params = useParams();
  const { isAuthenticated, loading: authLoading } = useAuth();
  const slug = params?.slug as string;

  useEffect(() => {
    if (authLoading) return;

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

