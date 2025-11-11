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

const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${internalApiBase}/api/:path*`,
      },
    ];
  },
  env: {
    NEXT_PUBLIC_API_BASE_URL: publicApiBase,
    NEXT_INTERNAL_API_BASE_URL: internalApiBase,
  },
};

module.exports = nextConfig;
