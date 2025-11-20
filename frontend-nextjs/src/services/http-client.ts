/**
 * Centralized HTTP client for API requests
 * Provides consistent error handling and response parsing
 */

export interface ApiError {
  detail?: string;
  message?: string;
  error?: string;
}

export class HttpClient {
  private baseUrl: string;

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl;
  }

  async request<T>(
    url: string,
    options: RequestInit = {}
  ): Promise<T> {
    const fullUrl = url.startsWith('http') ? url : `${this.baseUrl}${url}`;
    
    try {
      const response = await fetch(fullUrl, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      if (!response.ok) {
        await this.handleErrorResponse(response);
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      
      return (await response.text()) as unknown as T;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('Unknown error occurred');
    }
  }

  private async handleErrorResponse(response: Response): Promise<never> {
    let errorMessage = `Request failed: ${response.status}`;
    
    try {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const errorData: ApiError = await response.json();
        errorMessage = errorData.detail || errorData.message || errorData.error || errorMessage;
      } else {
        const errorText = await response.text();
        console.error('Non-JSON error response:', errorText.substring(0, 200));
      }
    } catch (parseErr) {
      console.error('Error parsing error response:', parseErr);
    }
    
    throw new Error(errorMessage);
  }

  async get<T>(url: string, options?: RequestInit): Promise<T> {
    return this.request<T>(url, { ...options, method: 'GET' });
  }

  async post<T>(url: string, data?: unknown, options?: RequestInit): Promise<T> {
    return this.request<T>(url, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(url: string, data?: unknown, options?: RequestInit): Promise<T> {
    return this.request<T>(url, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(url: string, options?: RequestInit): Promise<T> {
    return this.request<T>(url, { ...options, method: 'DELETE' });
  }
}

// Default instance using apiConfig
import { apiConfig } from '@/lib/api-config';
export const httpClient = new HttpClient(apiConfig.baseUrl);
