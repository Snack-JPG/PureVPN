/** @type {import('next').NextConfig} */
const nextConfig = {
  // Remove rewrites for Vercel deployment - we'll use NEXT_PUBLIC_API_URL instead
  // For local development, the API utility will fall back to localhost:8000
  
  // Optimize for Vercel deployment
  typescript: {
    // Don't fail build on TypeScript errors in development
    ignoreBuildErrors: false,
  },
  
  // Environment variables validation
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },
  
  // Headers for better security and performance
  async headers() {
    return [
      {
        source: '/(.*)',
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
        ],
      },
    ]
  },
}

module.exports = nextConfig 