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

const nextConfig = {
  ...(basePath ? { basePath } : {}),
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
