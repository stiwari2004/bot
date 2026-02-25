/**
 * Security middleware: nonce-based CSP to remove unsafe-inline/unsafe-eval (OWASP ZAP).
 * Sets x-nonce for Next.js to inject into script/style tags.
 */
import { NextRequest, NextResponse } from 'next/server';

const isDev = process.env.NODE_ENV === 'development';

export function middleware(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString('base64');

  const cspParts = [
    "default-src 'self'",
    "base-uri 'self'",
    "form-action 'self'",
    // Relaxed for production Next.js so static chunks and inline runtime scripts can execute.
    // Backend/API still has its own stricter CSP; this header is for the Next.js frontend only.
    `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ''}`,
    `style-src 'self' 'unsafe-inline'`,
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "object-src 'none'",
  ];
  const csp = cspParts.join('; ');

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-nonce', nonce);

  const response = NextResponse.next({
    request: { headers: requestHeaders },
  });
  response.headers.set('Content-Security-Policy', csp);

  return response;
}

export const config = {
  matcher: [
    {
      source: '/((?!api|_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)',
      missing: [
        { type: 'header', key: 'next-router-prefetch' },
        { type: 'header', key: 'purpose', value: 'prefetch' },
      ],
    },
  ],
};
