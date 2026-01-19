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
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/066c9cec-c573-4288-a2b8-64e315bfdeda',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SuperAdminAuthContext.tsx:83',message:'Login attempt started',data:{email,hasPassword:!!password,hostname:typeof window!=='undefined'?window.location.hostname:'server'},timestamp:Date.now(),sessionId:'debug-session',runId:'pre-fix',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const loginUrl = apiConfig.endpoints.superAdmin.auth.login();
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/066c9cec-c573-4288-a2b8-64e315bfdeda',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SuperAdminAuthContext.tsx:88',message:'Login URL determined',data:{loginUrl,apiBaseUrl:apiConfig.baseUrl,formDataKeys:['username','password']},timestamp:Date.now(),sessionId:'debug-session',runId:'pre-fix',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    
    try {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/066c9cec-c573-4288-a2b8-64e315bfdeda',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SuperAdminAuthContext.tsx:91',message:'Fetch request initiated',data:{method:'POST',url:loginUrl,hasBody:!!formData.toString()},timestamp:Date.now(),sessionId:'debug-session',runId:'pre-fix',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      const response = await fetch(loginUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString(),
      });

      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/066c9cec-c573-4288-a2b8-64e315bfdeda',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SuperAdminAuthContext.tsx:99',message:'Response received',data:{status:response.status,statusText:response.statusText,ok:response.ok,url:response.url},timestamp:Date.now(),sessionId:'debug-session',runId:'pre-fix',hypothesisId:'C'})}).catch(()=>{});
      // #endregion

      if (!response.ok) {
        let errorMessage = 'Login failed';
        let errorBody = null;
        try {
          errorBody = await response.json();
          errorMessage = errorBody.detail || errorBody.message || `Login failed (${response.status})`;
        } catch (e) {
          errorMessage = `Login failed: ${response.status} ${response.statusText}`;
        }
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/066c9cec-c573-4288-a2b8-64e315bfdeda',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SuperAdminAuthContext.tsx:107',message:'Login failed - error response',data:{status:response.status,errorMessage,errorBody},timestamp:Date.now(),sessionId:'debug-session',runId:'pre-fix',hypothesisId:'C'})}).catch(()=>{});
        // #endregion
        throw new Error(errorMessage);
      }

      const data = await response.json();
      const authToken = data.access_token;

      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/066c9cec-c573-4288-a2b8-64e315bfdeda',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SuperAdminAuthContext.tsx:115',message:'Login success - token received',data:{hasToken:!!authToken,tokenLength:authToken?.length},timestamp:Date.now(),sessionId:'debug-session',runId:'pre-fix',hypothesisId:'C'})}).catch(()=>{});
      // #endregion

      if (!authToken) {
        throw new Error('No access token received from server');
      }

      localStorage.setItem('super_admin_token', authToken);
      setToken(authToken);
      await fetchAdminInfo(authToken);
    } catch (error) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/066c9cec-c573-4288-a2b8-64e315bfdeda',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SuperAdminAuthContext.tsx:125',message:'Login exception caught',data:{errorType:error?.constructor?.name,errorMessage:error instanceof Error?error.message:String(error),isFetchError:error instanceof TypeError&&error.message.includes('fetch')},timestamp:Date.now(),sessionId:'debug-session',runId:'pre-fix',hypothesisId:'D'})}).catch(()=>{});
      // #endregion
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







