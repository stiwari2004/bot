/** @type {import('next').NextConfig} */
// When running in Docker production, use backend service name; otherwise use localhost
const isDocker = process.env.NODE_ENV === 'production';
const apiBase = isDocker ? 'http://backend:8000' : 'http://localhost:8000';

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
