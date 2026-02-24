'use client';

import { LoginPage } from '@/components/LoginPage';

/**
 * Dedicated /login route for main app (tenant) login.
 * admin.resolvify.tech uses /super-admin/login; tenant/MSP uses /tenant-admin/login.
 */
export default function LoginRoutePage() {
  return <LoginPage />;
}
