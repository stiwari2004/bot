import { NextRequest, NextResponse } from 'next/server';

// Use backend service name in Docker, localhost when running locally
// In Docker, use service name; in local dev, use localhost
const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 
  process.env.NEXT_INTERNAL_API_BASE_URL || 
  (process.env.NODE_ENV === 'production' ? 'http://backend:8000' : 'http://localhost:8000');

export async function POST(request: NextRequest) {
  try {
    // Get query parameters from the request URL
    const searchParams = request.nextUrl.searchParams;
    
    // Forward the request to the backend
    const backendUrl = `${BACKEND_URL}/api/v1/runbooks/demo/generate-agent?${searchParams.toString()}`;
    
    // Use a longer timeout for LLM requests (5 minutes)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5 * 60 * 1000); // 5 minutes
    
    try {
      const response = await fetch(backendUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        // Forward the request body if present
        body: request.body ? await request.text() : undefined,
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);

      // Get the response body as text first
      const responseText = await response.text();
      
      // Return the response with the same status and content type
      return new NextResponse(responseText, {
        status: response.status,
        headers: {
          'Content-Type': response.headers.get('content-type') || 'application/json',
        },
      });
    } finally {
      clearTimeout(timeoutId);
    }
  } catch (error) {
    console.error('Error proxying request to backend:', error);
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { detail: 'Request timeout: The runbook generation is taking too long. Please try again.' },
        { status: 504 }
      );
    }
    return NextResponse.json(
      { detail: `Proxy error: ${error instanceof Error ? error.message : 'Unknown error'}` },
      { status: 500 }
    );
  }
}

