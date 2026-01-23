'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { apiConfig } from '@/lib/api-config';

interface SuperAdmin {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  last_login: string | null;
}

interface SuperAdminAuthContextType {
  token: string | null;
  admin: SuperAdmin | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  loading: boolean;
}

const SuperAdminAuthContext = createContext<SuperAdminAuthContextType | undefined>(undefined);

export function SuperAdminAuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [admin, setAdmin] = useState<SuperAdmin | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchAdminInfo = useCallback(async (authToken: string) => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);

      const url: string = apiConfig.endpoints.superAdmin.auth.me();
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const adminData = await response.json();
        setAdmin(adminData);
        setToken(authToken);
      } else {
        localStorage.removeItem('super_admin_token');
        setToken(null);
        setAdmin(null);
      }
    } catch (error) {
      if (error instanceof Error && error.name !== 'AbortError') {
        console.error('Failed to fetch super admin info:', error);
      }
      localStorage.removeItem('super_admin_token');
      setToken(null);
      setAdmin(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load token from localStorage on mount
  useEffect(() => {
    if (typeof window === 'undefined') {
      setLoading(false);
      return;
    }

    const storedToken = localStorage.getItem('super_admin_token');
    if (storedToken) {
      setToken(storedToken);
      fetchAdminInfo(storedToken);
    } else {
      setLoading(false);
    }
  }, [fetchAdminInfo]);

  const login = async (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const loginUrl = apiConfig.endpoints.superAdmin.auth.login();
    
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
        let errorBody: any = null;
        try {
          const text = await response.text();
          if (text) {
            try {
              errorBody = JSON.parse(text);
              errorMessage = errorBody?.detail || errorBody?.message || `Login failed (${response.status})`;
            } catch (parseError) {
              // Not JSON, use text as error message
              errorMessage = text || `Login failed: ${response.status} ${response.statusText}`;
              errorBody = { raw: text };
            }
          } else {
            errorMessage = `Login failed: ${response.status} ${response.statusText}`;
          }
        } catch (e) {
          errorMessage = `Login failed: ${response.status} ${response.statusText}`;
          errorBody = { error: String(e) };
        }
        console.error('[DEBUG] Login failed - error response', { status: response.status, statusText: response.statusText, errorMessage, errorBody });
        throw new Error(errorMessage);
      }

      const data = await response.json();
      const authToken = data.access_token;

      if (!authToken) {
        throw new Error('No access token received from server');
      }

      localStorage.setItem('super_admin_token', authToken);
      setToken(authToken);
      await fetchAdminInfo(authToken);
    } catch (error) {
      console.error('[DEBUG] Login exception caught', { errorType: error?.constructor?.name, errorMessage: error instanceof Error ? error.message : String(error), isFetchError: error instanceof TypeError && error.message.includes('fetch') });
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(`Cannot connect to backend at ${loginUrl}. Make sure the backend is running on port 8000.`);
      }
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('super_admin_token');
    setToken(null);
    setAdmin(null);
  };

  return (
    <SuperAdminAuthContext.Provider
      value={{
        token,
        admin,
        login,
        logout,
        isAuthenticated: !!token && !!admin,
        loading,
      }}
    >
      {children}
    </SuperAdminAuthContext.Provider>
  );
}

export function useSuperAdminAuth() {
  const context = useContext(SuperAdminAuthContext);
  if (context === undefined) {
    throw new Error('useSuperAdminAuth must be used within a SuperAdminAuthProvider');
  }
  return context;
}







