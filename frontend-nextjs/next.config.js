/** @type {import('next').NextConfig} */
// Default to “same-origin” for the browser, but always proxy to the backend service internally.
const isDocker =
  process.env.IN_DOCKER === '1' ||
  process.env.IN_DOCKER === 'true' ||
  process.env.DOCKER === '1';

const internalApiBase =
  process.env.NEXT_INTERNAL_API_BASE_URL ||
  (isDocker ? 'http://backend:8000' : 'http://localhost:8000');

const publicApiBase =
  process.env.NEXT_PUBLIC_API_BASE_URL && process.env.NEXT_PUBLIC_API_BASE_URL.trim() !== ''
    ? process.env.NEXT_PUBLIC_API_BASE_URL.trim()
    : '';

// When served under resolvify.tech/app (marketing at root, app at /app)
const basePath = process.env.NEXT_PUBLIC_BASE_PATH && process.env.NEXT_PUBLIC_BASE_PATH.trim() !== ''
  ? process.env.NEXT_PUBLIC_BASE_PATH.trim().replace(/\/$/, '')
  : '';

// Security headers (OWASP ZAP recommendations)
// CSP is set by middleware.ts with nonce (no unsafe-inline/unsafe-eval). These apply to all routes.
const securityHeaders = [
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  {
    key: 'Permissions-Policy',
    value: 'camera=(), microphone=(), geolocation=(), interest-cohort=()',
  },
  { key: 'Cross-Origin-Opener-Policy', value: 'same-origin' },
  { key: 'Cross-Origin-Resource-Policy', value: 'same-origin' },
  { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' },
];

// Combined image: static export so FastAPI can serve frontend from same origin
const combinedBuild = process.env.COMBINED_BUILD === '1' || process.env.COMBINED_BUILD === 'true';

const nextConfig = {
  ...(basePath ? { basePath } : {}),
  ...(combinedBuild ? { output: 'export' } : {}),
  poweredByHeader: false,
  async headers() {
    return [{ source: '/:path*', headers: securityHeaders }];
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${internalApiBase}/api/:path*`,
      },
      {
        source: '/health',
        destination: `${internalApiBase}/health`,
      },
    ];
  },
  env: {
    NEXT_PUBLIC_API_BASE_URL: publicApiBase,
    NEXT_INTERNAL_API_BASE_URL: internalApiBase,
  },
};

module.exports = nextConfig;
