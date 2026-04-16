import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public paths that don't require authentication
  const publicPaths = [
    '/login',
    '/api/login',
    '/api/logout',
    '/api/me',
    '/_next',
    '/favicon.ico',
  ];

  // Check if the path is public
  const isPublicPath = publicPaths.some(path => pathname.startsWith(path));
  
  // Check for session token
  const sessionToken = request.cookies.get('session_token');

  // If trying to access a protected route without session
  if (!isPublicPath && !sessionToken && !pathname.startsWith('/api/')) {
    const loginUrl = new URL('/login', request.url);
    return NextResponse.redirect(loginUrl);
  }

  // If already logged in and trying to access login page, redirect to home
  if (pathname === '/login' && sessionToken) {
    return NextResponse.redirect(new URL('/', request.url));
  }

  return NextResponse.next();
}

// Apply middleware to all routes except static files
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
