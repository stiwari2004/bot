'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { LockClosedIcon, EnvelopeIcon } from '@heroicons/react/24/outline';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface LoginPageProps {
  onSkipLogin?: () => void;
}

export function LoginPage({ onSkipLogin }: LoginPageProps) {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login, user, isAuthenticated } = useAuth();
  const [isDemoHost, setIsDemoHost] = useState(false);

  // Detect if we're on the public demo host (demo.resolvify.tech)
  // Redirect dev.resolvify.tech and admin.resolvify.tech to super admin login
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const hostname = window.location.hostname;
    setIsDemoHost(hostname === 'demo.resolvify.tech');
    
    // Redirect to super admin login for admin and dev domains
    if (hostname === 'admin.resolvify.tech' || hostname === 'dev.resolvify.tech') {
      router.push('/super-admin/login');
      return;
    }
  }, [router]);

  // Redirect admins after login
  useEffect(() => {
    if (typeof window === 'undefined') return;
    // Wait for user data to be fully loaded (including tenant info)
    if (isAuthenticated && user && user.tenant !== undefined) {
      const currentPath = window.location.pathname;
      
      // MSP Admin: redirect to /tenant-admin
      // Allow both 'msp_admin' role and legacy 'admin' role with MSP tenant
      const isMspAdmin = (
        user.role === 'msp_admin' || 
        (user.role === 'admin' && user.tenant?.is_msp === true)
      );
      if (isMspAdmin && !currentPath.startsWith('/tenant-admin')) {
        window.location.href = '/tenant-admin';
        return;
      }
      
      // Tenant Admin (non-MSP): redirect to /admin
      // Allow both 'tenant_admin' role and legacy 'admin' role with non-MSP tenant
      const isTenantAdmin = (
        user.role === 'tenant_admin' || 
        (user.role === 'admin' && user.tenant?.is_msp === false)
      );
      if (isTenantAdmin && !currentPath.startsWith('/admin') && !currentPath.startsWith('/tenant-admin')) {
        window.location.href = '/admin';
        return;
      }
    }
  }, [isAuthenticated, user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(email, password);
      // Login successful - AuthContext will update, triggering re-render
      // The useEffect above will handle redirect for MSP admins
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-secondary-50 px-4 py-12">
      <Card variant="elevated" className="max-w-md w-full">
        <CardContent padding="lg">
          <div className="text-center mb-8">
            <div className="mx-auto h-16 w-16 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-2xl flex items-center justify-center mb-4 shadow-lg">
              <LockClosedIcon className="h-8 w-8 text-white" />
            </div>
            <h2 className="text-3xl font-bold text-neutral-900 mb-2">Welcome Back</h2>
            <p className="text-sm text-neutral-600">
              Sign in to access the Troubleshooting AI Platform
            </p>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <Card variant="outlined" className="border-error-200 bg-error-50">
                <CardContent padding="sm">
                  <p className="text-error-800 text-sm">{error}</p>
                </CardContent>
              </Card>
            )}

            <div className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-semibold text-neutral-700 mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <EnvelopeIcon className="h-5 w-5 text-neutral-400" />
                  </div>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="appearance-none block w-full pl-10 pr-3 py-2.5 border border-neutral-300 rounded-lg placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 bg-white transition-all"
                    placeholder={isDemoHost ? 'demo@example.com' : 'you@example.com'}
                  />
                </div>
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-semibold text-neutral-700 mb-2">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <LockClosedIcon className="h-5 w-5 text-neutral-400" />
                  </div>
                  <input
                    id="password"
                    name="password"
                    type="password"
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="appearance-none block w-full pl-10 pr-3 py-2.5 border border-neutral-300 rounded-lg placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 bg-white transition-all"
                    placeholder="Enter your password"
                  />
                </div>
              </div>
            </div>

            {isDemoHost && (
              <Card variant="default" className="bg-primary-50 border-primary-200">
                <CardContent padding="sm">
                  <p className="font-semibold text-primary-800 mb-2 text-sm">Sandbox Demo Credentials:</p>
                  <div className="space-y-1 text-xs text-primary-700">
                    <p>
                      Email:{' '}
                      <code className="bg-primary-100 px-1.5 py-0.5 rounded font-mono">
                        demo@example.com
                      </code>
                    </p>
                    <p>
                      Password:{' '}
                      <code className="bg-primary-100 px-1.5 py-0.5 rounded font-mono">
                        demo123
                      </code>
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            <div>
              <Button
                type="submit"
                variant="primary"
                size="lg"
                isLoading={loading}
                className="w-full"
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </Button>
            </div>

            <div className="text-center space-y-2">
              {onSkipLogin && isDemoHost && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={onSkipLogin}
                  className="w-full"
                >
                  Continue in Demo Mode (No Login Required)
                </Button>
              )}
              {isDemoHost && (
                <p className="text-xs text-neutral-500">
                  Demo mode uses public endpoints and doesn't require authentication
                </p>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

