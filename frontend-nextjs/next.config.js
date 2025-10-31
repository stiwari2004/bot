/** @type {import('next').NextConfig} */
// When running in Docker, use backend service name; otherwise use localhost
const apiBase = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === 'production' ? 'http://backend:8000' : 'http://localhost:8000');
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
