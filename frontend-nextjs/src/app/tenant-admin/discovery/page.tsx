'use client';

import { useMspAdminAuth } from '@/contexts/MspAdminAuthContext';
import { DiscoveryView } from '@/features/admin/components/DiscoveryView';

export default function TenantAdminDiscoveryPage() {
  const { token } = useMspAdminAuth();
  return <DiscoveryView token={token} standalone backHref="/tenant-admin" />;
}
