'use client';
/**
 * Helper function for super admin authenticated fetch requests
 * Uses super_admin_token from localStorage and handles 401s consistently
 */
export async function superAdminFetch(
  url: string,
  token: string | null,
  options: RequestInit = {}
): Promise<Response> {
  if (!token) {
    throw new Error('No authentication token available');
  }

  const headers = new Headers(options.headers);
  headers.set('Authorization', `Bearer ${token}`);
  
  // Merge with any existing headers
  if (options.headers) {
    Object.entries(options.headers).forEach(([key, value]) => {
      if (typeof value === 'string') {
        headers.set(key, value);
      }
    });
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
  });
  
  // Handle 401 Unauthorized - clear token and redirect to login
  if (response.status === 401 && typeof window !== 'undefined') {
    // Clear invalid token
    localStorage.removeItem('super_admin_token');
    
    // Dispatch a custom event to notify SuperAdminAuthContext
    window.dispatchEvent(new CustomEvent('super-admin:logout', { detail: { reason: 'session_revoked' } }));
    
    // Redirect to login page if not already there
    const currentPath = window.location.pathname;
    if (!currentPath.includes('/super-admin/login') &&
        !currentPath.includes('/forgot-password') &&
        !currentPath.includes('/reset-password')) {
      // Small delay to allow event handlers to process
      setTimeout(() => {
        window.location.href = '/super-admin/login';
      }, 100);
    }
  }
  
  return response;
}
