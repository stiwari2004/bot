/** @type {import('next').NextConfig} */
// When running in Docker production, use backend service name; otherwise use localhost
const isDocker = process.env.NODE_ENV === 'production';
const apiBase =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (isDocker ? 'http://backend:8000' : 'http://localhost:8000');

const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
  env: {
    NEXT_PUBLIC_API_BASE_URL: apiBase,
  },
};

module.exports = nextConfig;
