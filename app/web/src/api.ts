// One request to the FastAPI backend. Signed out: back to the sign-in page. Errors carry the server's own message.
export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, { credentials: 'same-origin', ...options });
  if (response.status === 401) {
    window.location.replace('/login');
    throw new Error('Signed out');
  }
  const data: unknown = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data && typeof data === 'object' && 'detail' in data ? (data as { detail: unknown }).detail : undefined;
    throw new Error(typeof detail === 'string' ? detail : `Request failed: ${response.status}`);
  }
  return data as T;
}

export const postJSON = <T>(path: string, body: unknown): Promise<T> =>
  api<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export const errorText = (error: unknown): string => (error instanceof Error ? error.message : String(error));
