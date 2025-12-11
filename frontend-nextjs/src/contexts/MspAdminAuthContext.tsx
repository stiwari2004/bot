'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { apiConfig } from '@/lib/api-config';

interface MspAdmin {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  tenant_id: number;
  tenant: {
    id: number;
    name: string;
    is_msp: boolean;
  } | null;
}

interface MspAdminAuthContextType {
  token: string | null;
  admin: MspAdmin | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  loading: boolean;
}

const MspAdminAuthContext = createContext<MspAdminAuthContextType | undefined>(undefined);

export function MspAdminAuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [admin, setAdmin] = useState<MspAdmin | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchAdminInfo = useCallback(async (authToken: string) => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);

      // Use regular auth/me endpoint but validate it's an MSP admin
      const url: string = apiConfig.endpoints.auth.me();
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const userData = await response.json();
        
        // Validate user is MSP admin
        // Check for both new 'msp_admin' role and legacy 'admin' role with MSP tenant
        const isMspAdmin = (
          userData.role === 'msp_admin' || 
          (userData.role === 'admin' && userData.tenant?.is_msp === true)
        );
        
        if (isMspAdmin) {
          setAdmin({
            id: userData.id,
            email: userData.email,
            full_name: userData.full_name,
            role: userData.role,
            tenant_id: userData.tenant_id,
            tenant: userData.tenant,
          });
          setToken(authToken);
        } else {
          // Not an MSP admin, clear token
          localStorage.removeItem('auth_token');
          setToken(null);
          setAdmin(null);
        }
      } else {
        localStorage.removeItem('auth_token');
        setToken(null);
        setAdmin(null);
      }
    } catch (error) {
      if (error instanceof Error && error.name !== 'AbortError') {
        console.error('Failed to fetch MSP admin info:', error);
      }
      localStorage.removeItem('auth_token');
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

    const storedToken = localStorage.getItem('auth_token');
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

      localStorage.setItem('auth_token', authToken);
      setToken(authToken);
      await fetchAdminInfo(authToken);
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(`Cannot connect to backend at ${loginUrl}. Make sure the backend is running on port 8000.`);
      }
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setToken(null);
    setAdmin(null);
  };

  return (
    <MspAdminAuthContext.Provider
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
    </MspAdminAuthContext.Provider>
  );
}

export function useMspAdminAuth() {
  const context = useContext(MspAdminAuthContext);
  if (context === undefined) {
    throw new Error('useMspAdminAuth must be used within a MspAdminAuthProvider');
  }
  return context;
}

