const path = require('path');
const fs = require('fs');

// Allow OCR worker origin in CSP if configured
const OCR_URL = process.env.NEXT_PUBLIC_OCR_URL;
let ocrOrigin = null;
if (OCR_URL) {
  try {
    ocrOrigin = new URL(OCR_URL).origin;
  } catch (e) {
    // ignore invalid URL
  }
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  webpack: (config, { isServer }) => {
    if (!isServer) {
      // Copy pdfjs-dist worker file to public folder during build
      const workerSource = path.join(
        process.cwd(),
        'node_modules',
        'pdfjs-dist',
        'build',
        'pdf.worker.min.mjs'
      );
      const workerDest = path.join(process.cwd(), 'public', 'pdf.worker.min.mjs');
      
      if (fs.existsSync(workerSource) && !fs.existsSync(workerDest)) {
        fs.copyFileSync(workerSource, workerDest);
      }
    }
    return config;
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: (() => {
              const connectSrc = ["'self'"];
              if (ocrOrigin) {
                connectSrc.push(ocrOrigin);
              } else {
                // Development fallback: allow local OCR worker
                connectSrc.push('http://localhost:8123');
              }
              
              return [
                "default-src 'self'",
                "script-src 'self' 'unsafe-eval' 'unsafe-inline' blob:",
                "worker-src 'self' blob:",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: blob:",
                "font-src 'self' data:",
                `connect-src ${connectSrc.join(' ')}`,
                "frame-src 'none'",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'none'",
                "upgrade-insecure-requests"
              ].join('; ');
            })()
          }
        ]
      }
    ];
  }
};

module.exports = nextConfig;

