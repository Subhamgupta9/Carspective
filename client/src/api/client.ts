/**
 * CARspective — Centralized API Client
 * Provides typed fetch wrapper, timeout handling, and RFC 7807 structured error parsing.
 */

export interface ApiErrorDetail {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
}

export class ApiError extends Error {
  public status: number;
  public title: string;
  public detail: string;
  public errors?: ApiErrorDetail[];
  public requestId?: string;

  constructor(status: number, title: string, detail: string, errors?: ApiErrorDetail[], requestId?: string) {
    super(detail || title || `HTTP Error ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.title = title;
    this.detail = detail;
    this.errors = errors;
    this.requestId = requestId;
  }
}

const API_BASE_URL = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');
const DEFAULT_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS) || 75000;

export async function request<T>(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<T> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);

  const resolvedUrl = (url.startsWith('http://') || url.startsWith('https://'))
    ? url
    : `${API_BASE_URL}${url.startsWith('/') ? url : `/${url}`}`;

  const config: RequestInit = {
    ...options,
    signal: controller.signal,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options.headers,
    },
  };

  try {
    const response = await fetch(resolvedUrl, config);
    clearTimeout(id);

    if (!response.ok) {
      let errorBody: any = null;
      try {
        errorBody = await response.json();
      } catch {
        // Non-JSON response body
      }

      const title = errorBody?.title || errorBody?.message || response.statusText || 'API Request Failed';
      const detail = errorBody?.detail || errorBody?.error || `Request failed with status code ${response.status}`;
      const errors = errorBody?.errors;
      const requestId = errorBody?.request_id || response.headers?.get?.('X-Request-ID') || undefined;

      throw new ApiError(response.status, title, detail, errors, requestId);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return (await response.json()) as T;
  } catch (err: any) {
    clearTimeout(id);
    if (err.name === 'AbortError') {
      throw new ApiError(
        408,
        'Request Timeout',
        `Request timed out after ${timeoutMs / 1000} seconds. If the server was sleeping (cold start), please wait a moment and retry.`
      );
    }
    if (err instanceof ApiError) {
      throw err;
    }
    // Network error or unexpected exception
    throw new ApiError(0, 'Network Connection Error', err.message || 'Could not communicate with the CARspective server.');
  }
}
