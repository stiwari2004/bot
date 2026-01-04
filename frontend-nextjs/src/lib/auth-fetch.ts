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
  
  // Handle 401 Unauthorized - clear token and potentially redirect
  if (response.status === 401 && typeof window !== 'undefined') {
    // Clear invalid token
    localStorage.removeItem('auth_token');
    
    // Only redirect if we're not already on a login page
    const currentPath = window.location.pathname;
    if (!currentPath.includes('/login') && !currentPath.includes('/super-admin/login')) {
      // Don't auto-redirect, let the component handle it
      // This prevents infinite redirect loops
    }
  }
  
  return response;
}

