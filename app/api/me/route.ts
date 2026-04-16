import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function GET() {
  const cookieStore = await cookies();
  const sessionToken = cookieStore.get('session_token')?.value;
  if (!sessionToken) {
    return NextResponse.json({ success: false, user: null }, { status: 401 });
  }
  const rawBackendUrl =
    process.env.INTERNAL_API_URL ||
    process.env.BACKEND_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://127.0.0.1:8000';
  const backendUrl = rawBackendUrl.replace(/\/+$/, '');
  const meUrl = backendUrl.endsWith('/api') ? `${backendUrl}/me` : `${backendUrl}/api/me`;

  try {
    const response = await fetch(meUrl, {
      headers: {
        Cookie: `session_token=${sessionToken}`,
      },
      cache: 'no-store',
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json(
      { success: false, message: 'Unable to verify session', user: null },
      { status: 500 }
    );
  }
}
