import { describe, it, expect, vi, beforeEach } from 'vitest';
import { request, ApiError } from '../api/client';

describe('Centralized API Client Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('parses successful JSON responses correctly', async () => {
    const mockData = { service: 'carspective-api', status: 'UP' };
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockData,
    } as Response);

    const result = await request<typeof mockData>('/api/test');
    expect(result).toEqual(mockData);
  });

  it('parses RFC 7807 structured errors and throws typed ApiError', async () => {
    const errorBody = {
      type: 'about:blank',
      title: 'Validation Error',
      status: 422,
      detail: 'Missing mandatory brand name',
    };

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      json: async () => errorBody,
    } as Response);

    await expect(request('/api/test')).rejects.toThrow(ApiError);
    try {
      await request('/api/test');
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(422);
      expect(err.title).toBe('Validation Error');
      expect(err.detail).toBe('Missing mandatory brand name');
    }
  });

  it('handles 204 No Content responses gracefully', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 204,
    } as Response);

    const result = await request('/api/delete');
    expect(result).toEqual({});
  });

  it('captures request_id from RFC 7807 response or X-Request-ID header on error', async () => {
    const errorBody = {
      type: 'https://carspective.internal/errors/invalid_request',
      title: 'Bad Request',
      status: 400,
      detail: 'Invalid parameters',
      request_id: 'req-audit-trace-12345',
    };

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      headers: new Headers({ 'X-Request-ID': 'req-audit-trace-12345' }),
      json: async () => errorBody,
    } as unknown as Response);

    try {
      await request('/api/test-error');
      expect.unreachable('Should have thrown ApiError');
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.requestId).toBe('req-audit-trace-12345');
      expect(err.detail).toBe('Invalid parameters');
    }
  });
});
