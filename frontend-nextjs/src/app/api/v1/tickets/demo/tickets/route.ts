import { NextRequest, NextResponse } from 'next/server';

// Use backend service name in Docker, localhost when running locally
// In Docker, use service name; in local dev, use localhost
const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 
  process.env.NEXT_INTERNAL_API_BASE_URL || 
  (process.env.NODE_ENV === 'production' ? 'http://backend:8000' : 'http://localhost:8000');

export async function GET(request: NextRequest) {
  try {
    // Get query parameters from the request URL
    const searchParams = request.nextUrl.searchParams;
    
    // Forward the request to the backend
    const backendUrl = `${BACKEND_URL}/api/v1/tickets/demo/tickets?${searchParams.toString()}`;
    
    // Add timeout and better connection handling
    // Increased timeout to 60 seconds due to backend query performance
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout
    
    try {
      const response = await fetch(backendUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
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
    } catch (fetchError) {
      clearTimeout(timeoutId);
      // Re-throw to be caught by outer catch
      throw fetchError;
    }
  } catch (error) {
    console.error('Error proxying request to backend:', error);
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { detail: 'Request timeout: Backend took too long to respond.' },
        { status: 504 }
      );
    }
    // Check if it's a network error
    if (error instanceof Error && (error.message.includes('fetch failed') || error.message.includes('ECONNREFUSED'))) {
      return NextResponse.json(
        { detail: `Cannot connect to backend at ${BACKEND_URL}. Is the backend running?` },
        { status: 503 }
      );
    }
    return NextResponse.json(
      { detail: `Proxy error: ${error instanceof Error ? error.message : 'Unknown error'}` },
      { status: 500 }
    );
  }
}

