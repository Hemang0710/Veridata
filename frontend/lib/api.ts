// Typed client for the Veridata backend (spec 004 task 2).
// Thin wrapper over /upload and /ask — no business logic, just transport +
// error normalization. The UI renders whatever these return.

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, init);
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
