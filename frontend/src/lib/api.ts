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

// --- Documents -------------------------------------------------------------

export type DocumentStatus =
  | 'uploaded'
  | 'processing'
  | 'pending_review'
  | 'approved'
  | 'rejected'
  | 'failed';

export interface DocumentSummary {
  id: number;
  public_ref: string;
  doc_type: string;
  original_filename: string;
  status: DocumentStatus;
  uploaded_at: string;
}

export interface Finding {
  id: number;
  agent: string;
  field: string;
  status: 'verified' | 'mismatch' | 'unverifiable';
  severity: 'info' | 'warning' | 'blocking';
  document_value: string | null;
  reference_value: string | null;
  reference_source: string;
  explanation_en: string;
  confidence: number;
  page_number: number | null;
  box_left: number | null;
  box_top: number | null;
  box_width: number | null;
  box_height: number | null;
}

export interface CheckRun {
  agent_name: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
}

export interface DocumentDetail extends DocumentSummary {
  findings: Finding[];
  checks: CheckRun[];
  extracted: Record<string, string>;
  extracted_text: string | null;
  /** How many pages can be rendered. Zero for anything that is not a PDF. */
  page_count: number;
  has_blocking: boolean;
  reviewed_at: string | null;
  decision_reason: string | null;
  override_note: string | null;
}

export function listDocuments() {
  return request<DocumentSummary[]>('/documents');
}

export function getDocument(id: number) {
  return request<DocumentDetail>(`/documents/${id}`);
}

/** The document file's URL. Addressed by ID — never by a path. */
export function documentFileUrl(id: number) {
  return `${BASE_URL}/documents/${id}/file`;
}

/** One page of the document, rendered as an image. */
export function documentPageUrl(id: number, page: number) {
  return `${BASE_URL}/documents/${id}/page/${page}`;
}

export async function uploadDocument(file: File): Promise<ApiResult<DocumentSummary>> {
  const body = new FormData();
  body.append('file', file);
  try {
    // No Content-Type header: the browser must set the multipart boundary
    // itself, and setting it by hand produces a request the server cannot parse.
    const response = await fetch(`${BASE_URL}/documents`, {
      method: 'POST',
      credentials: 'include',
      body
    });
    if (!response.ok) {
      let code = 'unexpected';
      try {
        const payload = await response.json();
        if (typeof payload?.detail === 'string') code = payload.detail;
      } catch {
        /* non-JSON error body */
      }
      return {ok: false, code};
    }
    return {ok: true, data: (await response.json()) as DocumentSummary};
  } catch {
    return {ok: false, code: 'network'};
  }
}

// --- Department (head of department only) ----------------------------------

export interface Department {
  id: number;
  code: string;
  name: string;
}

export interface Officer {
  id: number;
  mobile_number: string;
  full_name: string;
  role: 'officer' | 'dept_head';
  is_active: boolean;
  created_at: string;
  pending: number;
  decided: number;
}

export interface DepartmentStats {
  processed_today: number;
  average_seconds: number | null;
  flags_raised: number;
  pending_now: number;
  officers: number;
}

export interface AuditRow {
  sequence: number;
  action: string;
  actor_user_id: number | null;
  actor_role: string | null;
  document_id: number | null;
  detail_json: string;
  created_at: string;
}

export interface AuditPage {
  rows: AuditRow[];
  total: number;
  chain_intact: boolean;
}

export function getDepartment() {
  return request<Department>('/department');
}

export function getStats() {
  return request<DepartmentStats>('/department/stats');
}

export function listOfficers() {
  return request<Officer[]>('/department/officers');
}

export function createOfficer(body: {
  mobile_number: string;
  full_name: string;
  password: string;
}) {
  return request<Officer>('/department/officers', {
    method: 'POST',
    body: JSON.stringify(body)
  });
}

export function setOfficerActive(id: number, isActive: boolean) {
  return request<Officer>(`/department/officers/${id}/active`, {
    method: 'POST',
    body: JSON.stringify({is_active: isActive})
  });
}

export function getAudit(limit = 50, offset = 0) {
  return request<AuditPage>(`/department/audit?limit=${limit}&offset=${offset}`);
}

export function reassign(documentId: number, assignedTo: number) {
  return request<{code: string}>(`/department/documents/${documentId}/assign`, {
    method: 'POST',
    body: JSON.stringify({assigned_to: assignedTo})
  });
}

export function getProvider() {
  return request<{provider: string}>('/department/provider');
}

export function setProvider(provider: string) {
  return request<{provider: string}>('/department/provider', {
    method: 'POST',
    body: JSON.stringify({provider})
  });
}

export function supersede(
  documentId: number,
  decision: 'approved' | 'rejected',
  reason: string,
  overrideNote?: string
) {
  return request<DocumentDetail>(`/documents/${documentId}/supersede`, {
    method: 'POST',
    body: JSON.stringify({decision, reason, override_note: overrideNote})
  });
}

export function decide(
  id: number,
  decision: 'approved' | 'rejected',
  opts: {reason?: string; override_note?: string} = {}
) {
  return request<DocumentDetail>(`/documents/${id}/decision`, {
    method: 'POST',
    body: JSON.stringify({decision, ...opts})
  });
}
