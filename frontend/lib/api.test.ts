// Run: node --test --experimental-strip-types lib/api.test.ts
// No test runner is wired into the scaffold yet (task 1 debt); this uses Node's
// built-in runner so the error-parsing logic stays covered with zero deps.

import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError, ask, messageFromDetail, setTokenProvider } from "./api.ts";

const originalFetch = global.fetch;
function stubFetch(fn: typeof fetch): void {
  global.fetch = fn;
}
function restoreFetch(): void {
  global.fetch = originalFetch;
}

test("ask parses a success body", async () => {
  stubFetch(async () =>
    new Response(
      JSON.stringify({
        answer: { columns: ["n"], rows: [[42]] },
        sql: "SELECT count(*) AS n",
        confidence: "high",
        abstained: false,
        reason: "",
        checks: [{ name: "row_count", passed: true, detail: "1 row" }],
        trace_id: "ok-trace",
      }),
      { status: 200, headers: { "X-Trace-Id": "ok-trace" } },
    ),
  );
  try {
    const res = await ask("how many rows?");
    assert.equal(res.confidence, "high");
    assert.deepEqual(res.answer.rows, [[42]]);
    assert.equal(res.trace_id, "ok-trace");
  } finally {
    restoreFetch();
  }
});

test("guard rejection surfaces the error message and trace id", async () => {
  stubFetch(async () =>
    new Response(
      JSON.stringify({
        detail: { error: "SQL rejected by guard: writes blocked", sql: "DROP t", trace_id: "trace-123" },
      }),
      { status: 400, headers: { "X-Trace-Id": "trace-123" } },
    ),
  );
  try {
    await assert.rejects(ask("drop it"), (err: unknown) => {
      assert.ok(err instanceof ApiError);
      assert.equal(err.status, 400);
      assert.match(err.message, /rejected by guard/);
      assert.equal(err.traceId, "trace-123");
      return true;
    });
  } finally {
    restoreFetch();
  }
});

test("network failure becomes an ApiError with status 0", async () => {
  stubFetch(async () => {
    throw new TypeError("connection refused");
  });
  try {
    await assert.rejects(ask("x"), (err: unknown) => err instanceof ApiError && err.status === 0);
  } finally {
    restoreFetch();
  }
});

test("attaches the Supabase access token as a Bearer header", async () => {
  let seen: Headers | undefined;
  stubFetch(async (_url, init) => {
    seen = new Headers(init?.headers);
    return new Response(
      JSON.stringify({
        answer: { columns: [], rows: [] },
        sql: "",
        confidence: "high",
        abstained: false,
        reason: "",
        checks: [],
        trace_id: "t",
      }),
      { status: 200 },
    );
  });
  setTokenProvider(async () => "jwt-abc");
  try {
    await ask("anything");
    assert.equal(seen?.get("Authorization"), "Bearer jwt-abc");
    // The JSON content-type the caller set must survive the header merge.
    assert.equal(seen?.get("Content-Type"), "application/json");
  } finally {
    setTokenProvider(async () => null);
    restoreFetch();
  }
});

test("sends no Authorization header when there is no token", async () => {
  let seen: Headers | undefined;
  stubFetch(async (_url, init) => {
    seen = new Headers(init?.headers);
    return new Response(
      JSON.stringify({
        answer: { columns: [], rows: [] },
        sql: "",
        confidence: "high",
        abstained: false,
        reason: "",
        checks: [],
        trace_id: "t",
      }),
      { status: 200 },
    );
  });
  try {
    await ask("anything");
    assert.equal(seen?.has("Authorization"), false);
  } finally {
    restoreFetch();
  }
});

test("messageFromDetail handles the string shape", () => {
  assert.deepEqual(messageFromDetail("Upload a CSV first.", "fallback"), {
    message: "Upload a CSV first.",
  });
});
