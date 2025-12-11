'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Redirect admin.resolvify.tech root to super admin login
 */
export default function AdminRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to super admin login
    router.replace('/super-admin/login');
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-neutral-50 via-white to-neutral-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
        <p className="text-neutral-600">Redirecting to super admin login...</p>
      </div>
    </div>
  );
}
