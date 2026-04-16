import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { email, password } = body;

    const rawBackendUrl =
      process.env.INTERNAL_API_URL ||
      process.env.BACKEND_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://127.0.0.1:8000';
    const backendUrl = rawBackendUrl.replace(/\/+$/, '');
    const loginUrl = backendUrl.endsWith('/api')
      ? `${backendUrl}/login`
      : `${backendUrl}/api/login`;

    const response = await fetch(loginUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    let data: any = null;
    try {
      data = await response.json();
    } catch {
      data = {
        success: false,
        message: response.ok ? 'Unexpected backend response' : 'Login failed',
      };
    }

    const nextResponse = NextResponse.json(data, {
      status: response.status,
    });

    if (response.ok && data?.session_token) {
      nextResponse.cookies.set('session_token', String(data.session_token), {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        maxAge: 60 * 60 * 24 * 7,
        path: '/',
        sameSite: 'lax',
      });
    }

    return nextResponse;
  } catch (error) {
    return NextResponse.json(
      { success: false, message: 'Connection error' },
      { status: 500 }
    );
  }
}
