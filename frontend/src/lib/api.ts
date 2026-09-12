/**
 * Thin client for the Sutradhar API.
 *
 * Two rules hold everywhere in this file:
 *
 * 1. `credentials: 'include'`, because the session lives in an httpOnly cookie.
 *    No token is ever read or written by JavaScript.
 * 2. Errors are returned as codes, never as sentences. The backend replies with
 *    a code such as `invalid_credentials`; the screen looks it up in its locale
 *    file. No HTTP status, stack trace or raw exception reaches an officer.
 */

/**
 * Relative by design. Next.js rewrites /api/* to the backend (see
 * next.config.ts), so the browser makes a same-origin request and the
 * SameSite=Strict session cookie is actually sent. Pointing this at the backend
 * host directly would make every call cross-site and silently drop the cookie.
 */
const BASE_URL = '/api';

export type ApiResult<T> =
  | {ok: true; data: T}
  | {ok: false; code: string};

export interface CurrentUser {
  id: number;
  full_name: string;
  role: 'officer' | 'dept_head';
}

async function request<T>(
  path: string,
  init: RequestInit = {}
): Promise<ApiResult<T>> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      credentials: 'include',
      headers: {'Content-Type': 'application/json', ...(init.headers ?? {})}
    });
  } catch {
    // Network-level failure: the office connection or the service is down.
    return {ok: false, code: 'network'};
  }

  if (!response.ok) {
    // `detail` is a machine-readable code by convention across the API. Anything
    // unrecognised collapses to `unexpected` rather than surfacing a status code.
    let code = 'unexpected';
    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') code = body.detail;
    } catch {
      /* non-JSON error body — keep `unexpected` */
    }
    return {ok: false, code};
  }

  return {ok: true, data: (await response.json()) as T};
}

export function login(mobileNumber: string, password: string) {
  return request<CurrentUser>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({mobile_number: mobileNumber, password})
  });
}

export function logout() {
  return request<{code: string}>('/auth/logout', {method: 'POST'});
}

export function me() {
  return request<CurrentUser>('/auth/me');
}
