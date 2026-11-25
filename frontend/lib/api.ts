// Typed client for the Veridata backend (spec 004 task 2).
// Thin wrapper over /upload and /ask — no business logic, just transport +
// error normalization. The UI renders whatever these return.

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// --- Auth token (spec 007 task 3) ---
// The backend verifies a Supabase JWT on /upload and /ask, so every call carries
// the current session's access token as a Bearer header. The provider is injected
// (by lib/supabase/client.ts in the browser) rather than imported, so this module
// stays a pure transport layer with no Supabase dependency — the Node tests can
// exercise it without a browser client.

type TokenProvider = () => Promise<string | null>;

// Default: no token (unauthenticated). Replaced at runtime via setTokenProvider.
let tokenProvider: TokenProvider = async () => null;

/** Register how to obtain the current access token. Called once on the client. */
export function setTokenProvider(provider: TokenProvider): void {
  tokenProvider = provider;
}

// --- Response shapes (mirror backend/app/main.py + pipeline.py) ---

export interface Column {
  name: string;
  type: string;
}

export interface UploadResponse {
  table: string;
  columns: Column[];
  row_count: number;
}

/** The /ask answer is a result set, not a string. */
export interface AnswerTable {
  columns: string[];
  rows: unknown[][];
}

export interface Check {
  name: string;
  passed: boolean;
  detail: string;
}

export type Confidence = "high" | "medium" | "low";

/** A renderable chart the backend decided fits the result (spec 005). Mirrors
 *  backend chart.ChartSpec. Null/absent when not chartable or on a low/abstained answer. */
export interface ChartSpec {
  type: "bar" | "line";
  labels: string[];
  values: number[];
  x_title: string;
  y_title: string;
}

export interface AskResponse {
  answer: AnswerTable;
  sql: string;
  confidence: Confidence;
  abstained: boolean;
  reason: string;
  checks: Check[];
  chart: ChartSpec | null;
  trace_id: string;
}

/** A failed request. `status` is 0 for a network failure (no response). */
export class ApiError extends Error {
  readonly status: number;
  readonly traceId?: string;

  constructor(message: string, status: number, traceId?: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "ApiError";
    this.status = status;
    this.traceId = traceId;
  }
}

/**
 * Turn FastAPI's `detail` into a message + optional trace id. It arrives as a
 * plain string ("Upload a CSV first.") or, for guard rejections, an object
 * {error, sql, trace_id}. Exported so the test can hit both shapes directly.
 */
export function messageFromDetail(
  detail: unknown,
  fallback: string,
): { message: string; traceId?: string } {
  if (typeof detail === "string" && detail) {
    return { message: detail };
  }
  if (detail && typeof detail === "object") {
    const d = detail as Record<string, unknown>;
    const message = typeof d.error === "string" ? d.error : fallback;
    const traceId = typeof d.trace_id === "string" ? d.trace_id : undefined;
    return { message, traceId };
  }
  return { message: fallback };
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  // Attach the Supabase access token. new Headers() preserves whatever the caller
  // set (JSON content-type for /ask) and leaves /upload's multipart boundary alone.
  const headers = new Headers(init.headers);
  const token = await tokenProvider();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  } catch (cause) {
    throw new ApiError(`Could not reach the backend at ${BASE_URL}.`, 0, undefined, { cause });
  }

  const headerTrace = res.headers.get("X-Trace-Id") ?? undefined;

  if (!res.ok) {
    let detail: unknown;
    try {
      detail = ((await res.json()) as { detail?: unknown })?.detail;
    } catch {
      // Non-JSON error body; fall back to the status line below.
    }
    const { message, traceId } = messageFromDetail(
      detail,
      res.statusText || `Request failed (${res.status})`,
    );
    throw new ApiError(message, res.status, traceId ?? headerTrace);
  }

  return (await res.json()) as T;
}

/** Upload a CSV; resolves with the detected columns and row count. */
export function upload(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadResponse>("/upload", { method: "POST", body: form });
}

/** Ask a question over the uploaded dataset. */
export function ask(question: string): Promise<AskResponse> {
  return request<AskResponse>("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}
