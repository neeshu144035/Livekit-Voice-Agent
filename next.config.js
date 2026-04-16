/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://13.135.81.172:8000/:path*',
      },
    ]
  },
}

module.exports = nextConfig