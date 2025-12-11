'use client';

// Simplified layout - all /admin routes redirect to main page
// This layout is kept for backward compatibility but pages handle their own redirects
export default function ClientAdminLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

