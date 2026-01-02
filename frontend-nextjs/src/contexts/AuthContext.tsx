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
    try {
      // Add timeout to prevent hanging
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000); // 3 second timeout

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
        setUser(userData);
        setToken(authToken); // Ensure token is set
      } else {
        // Token invalid, clear it
        localStorage.removeItem('auth_token');
        setToken(null);
        setUser(null);
      }
    } catch (error) {
      // On error or timeout, clear token and treat as not authenticated
      if (error instanceof Error && error.name !== 'AbortError') {
        console.error('Failed to fetch user info:', error);
      }
      localStorage.removeItem('auth_token');
      setToken(null);
      setUser(null);
    } finally {
      // Always set loading to false, even on error
      setLoading(false);
    }
  }, []);

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

  const logout = () => {
    localStorage.removeItem('auth_token');
    setToken(null);
    setUser(null);
    setMustChangePassword(false);
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

