'use client';
/**
 * Helper function to make authenticated fetch requests
 * Automatically includes Authorization header with token from localStorage
 */
export async function authFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  
  const headers = new Headers(options.headers);
  
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  
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
    localStorage.removeItem('auth_token');
    
    // Dispatch a custom event to notify AuthContext and other components
    window.dispatchEvent(new CustomEvent('auth:logout', { detail: { reason: 'session_revoked' } }));
    
    // Redirect to login page if not already there
    const currentPath = window.location.pathname;
    if (!currentPath.includes('/login') && 
        !currentPath.includes('/super-admin/login') && 
        !currentPath.includes('/tenant-admin/login') &&
        !currentPath.includes('/forgot-password') &&
        !currentPath.includes('/reset-password')) {
      // Small delay to allow event handlers to process
      setTimeout(() => {
        window.location.href = '/';
      }, 100);
    }
  }
  
  return response;
}

