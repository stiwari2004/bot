import CustomerTenantPathPage from './page-client';

/** Required for static export (output: 'export'): provide one placeholder so the route is included; SPA fallback serves index.html for other slugs. */
export function generateStaticParams() {
  return [{ slug: '_' }];
}

export default function Page() {
  return <CustomerTenantPathPage />;
}
