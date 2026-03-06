'use client';

import { useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { LoginPage } from '@/components/LoginPage';
import { PasswordChangeModal } from '@/components/PasswordChangeModal';
import { MainDashboard } from '@/components/MainDashboard';

export default function TicketsPage() {
  const { isAuthenticated, loading: authLoading, user, mustChangePassword } = useAuth();

  // Mirror the root page behaviour: if user must change password, block access to main app.
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-neutral-50 via-white to-neutral-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-neutral-600 font-medium">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  if (isAuthenticated && user && mustChangePassword) {
    return (
      <PasswordChangeModal
        onPasswordChanged={() => {
          window.location.reload();
        }}
      />
    );
  }

  // Authenticated and no forced password change: render the same dashboard, defaulting to Tickets tab.
  return <MainDashboard initialTab="tickets" />;
}

