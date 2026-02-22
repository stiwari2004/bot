import DirectTenantPathPage from './page-client';

/** Required for static export (output: 'export'): no slugs known at build time; SPA fallback serves index.html. */
export function generateStaticParams() {
  return [];
}

export default function Page() {
  return <DirectTenantPathPage />;
}
