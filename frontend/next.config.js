/** @type {import('next').NextConfig} */
const nextConfig = {
  // Security: Only allow localhost
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'Content-Security-Policy',
            value: "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' http://127.0.0.1:8000;",
          },
        ],
      },
    ];
  },
  
  // Security: Disable image optimization external domains
  images: {
    domains: [],
  },
  
  // Output standalone for deployment
  output: 'standalone',
  
  // Disable powered by header
  poweredByHeader: false,
};

module.exports = nextConfig;