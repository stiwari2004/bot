'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { apiConfig } from '@/lib/api-config';

interface Tenant {
  id: number;
  name: string;
  is_msp: boolean;
}

interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  tenant_id: number;
  tenant?: Tenant;
  must_change_password?: boolean;
}

interface AuthContextType {
  token: string | null;
  user: User | null;
  mustChangePassword: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [mustChangePassword, setMustChangePassword] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchUserInfo = useCallback(async (authToken: string) => {
    let timeoutId: ReturnType<typeof setTimeout> | undefined;
    try {
      const { authFetch } = await import('@/lib/auth-fetch');
      const url: string = apiConfig.endpoints.auth.me();
      const controller = new AbortController();
      timeoutId = setTimeout(() => controller.abort(), 15000);
      const response = await authFetch(url, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${authToken}` },
        signal: controller.signal,
      });
      if (timeoutId) clearTimeout(timeoutId);

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        // Update mustChangePassword from user data if present
        if (userData.must_change_password !== undefined) {
          setMustChangePassword(userData.must_change_password === true);
        }
        setToken(authToken); // Ensure token is set
      } else if (response.status === 401) {
        // 401 handled by authFetch (token cleared, logout event dispatched)
        setToken(null);
        setUser(null);
      } else {
        // Other error - clear token
        localStorage.removeItem('auth_token');
        setToken(null);
        setUser(null);
      }
    } catch (error) {
      if (error instanceof Error && error.name !== 'AbortError') {
        console.error('Failed to fetch user info:', error);
      }
      localStorage.removeItem('auth_token');
      setToken(null);
      setUser(null);
    } finally {
      if (timeoutId) clearTimeout(timeoutId);
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token');
    setToken(null);
    setUser(null);
    setMustChangePassword(false);
  }, []);

  // Listen for logout events (e.g., from authFetch when 401 is received)
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const handleLogout = () => {
      logout();
      // Force page reload to clear all state
      window.location.href = '/';
    };
    
    window.addEventListener('auth:logout', handleLogout);
    return () => window.removeEventListener('auth:logout', handleLogout);
  }, [logout]);

  // Periodically check session status (every 30 seconds)
  useEffect(() => {
    if (typeof window === 'undefined' || !token) return;
    
    const checkSession = async () => {
      try {
        const { authFetch } = await import('@/lib/auth-fetch');
        const response = await authFetch(apiConfig.endpoints.auth.me());
        
        if (!response.ok && response.status === 401) {
          // Session invalid - logout event will be dispatched by authFetch
          return;
        }
      } catch (error) {
        // Ignore errors - session check is best effort
        console.debug('Session check failed:', error);
      }
    };
    
    // Check immediately, then every 30 seconds
    checkSession();
    const interval = setInterval(checkSession, 30000);
    
    return () => clearInterval(interval);
  }, [token]);

  // Load token from localStorage on mount (client-side only)
  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') {
      setLoading(false);
      return;
    }

    const storedToken = localStorage.getItem('auth_token');
    if (storedToken) {
      setToken(storedToken);
      // Fetch user info
      fetchUserInfo(storedToken);
    } else {
      setLoading(false);
    }
  }, [fetchUserInfo]);

  const login = async (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const loginUrl = apiConfig.endpoints.auth.login();
    
    try {
      const response = await fetch(loginUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString(),
      });

      if (!response.ok) {
        let errorMessage = 'Login failed';
        try {
          const error = await response.json();
          errorMessage = error.detail || error.message || `Login failed (${response.status})`;
        } catch (e) {
          errorMessage = `Login failed: ${response.status} ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      const authToken = data.access_token;

      if (!authToken) {
        throw new Error('No access token received from server');
      }

      // Check if password change is required
      const requiresPasswordChange = data.must_change_password === true;
      setMustChangePassword(requiresPasswordChange);

      localStorage.setItem('auth_token', authToken);
      setToken(authToken);
      await fetchUserInfo(authToken);
    } catch (error) {
      // Re-throw with more context if it's a network error
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(`Cannot connect to backend at ${loginUrl}. Make sure the backend is running on port 8000.`);
      }
      throw error;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        mustChangePassword,
        login,
        logout,
        isAuthenticated: !!token,
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

