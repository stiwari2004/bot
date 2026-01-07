'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { EnvelopeIcon, CheckCircleIcon } from '@heroicons/react/24/outline';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { apiConfig } from '@/lib/api-config';

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response = await fetch(apiConfig.endpoints.auth.forgotPassword(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (response.ok) {
        setSuccess(true);
      } else {
        setError(data.detail || 'Failed to send password reset email');
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-secondary-50 px-4 py-12">
        <Card variant="elevated" className="max-w-md w-full">
          <CardContent padding="lg">
            <div className="text-center">
              <div className="mx-auto h-16 w-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                <CheckCircleIcon className="h-8 w-8 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold text-neutral-900 mb-2">Check Your Email</h2>
              <p className="text-neutral-600 mb-6">
                If an account with that email exists, we've sent a password reset link to{' '}
                <strong>{email}</strong>
              </p>
              <p className="text-sm text-neutral-500 mb-6">
                The link will expire in 1 hour. If you don't see the email, check your spam folder.
              </p>
              <Button
                variant="primary"
                onClick={() => router.push('/login')}
                className="w-full"
              >
                Back to Login
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-secondary-50 px-4 py-12">
      <Card variant="elevated" className="max-w-md w-full">
        <CardContent padding="lg">
          <div className="text-center mb-8">
            <div className="mx-auto h-16 w-16 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-2xl flex items-center justify-center mb-4 shadow-lg">
              <EnvelopeIcon className="h-8 w-8 text-white" />
            </div>
            <h2 className="text-3xl font-bold text-neutral-900 mb-2">Forgot Password?</h2>
            <p className="text-sm text-neutral-600">
              Enter your email address and we'll send you a link to reset your password
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
                  placeholder="you@example.com"
                />
              </div>
            </div>

            <div>
              <Button
                type="submit"
                variant="primary"
                size="lg"
                isLoading={loading}
                className="w-full"
              >
                {loading ? 'Sending...' : 'Send Reset Link'}
              </Button>
            </div>

            <div className="text-center">
              <a
                href="/login"
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                Back to Login
              </a>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

