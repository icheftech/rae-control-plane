export type Row = Record<string, any> & { id: string; name?: string; title?: string };

export const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:18000';

export async function request<T>(path: string, token: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`${baseUrl.replace(/\/$/, '')}/api/${path.replace(/^\//, '')}`, {
    method,
    credentials: 'include',
    headers: {
      ...(token ? {Authorization: `Bearer ${token}`} : {}),
      'Content-Type': 'application/json',
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: 'no-store',
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      // Keep the HTTP status text when the API returns a non-JSON error.
    }
    throw new Error(`${response.status} ${detail}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}
