"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Column = { name: string; type: string };
type UploadResult = { table: string; columns: Column[]; row_count: number };
type Answer = { columns: string[]; rows: unknown[][] };
type AskResult = { answer: Answer; sql: string; trace_id: string };

export default function Home() {
  const [upload, setUpload] = useState<UploadResult | null>(null);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [traceId, setTraceId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setResult(null);
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const resp = await fetch(`${API}/upload`, { method: "POST", body: form });
      if (!resp.ok) throw new Error(`Upload failed (${resp.status})`);
      setUpload((await resp.json()) as UploadResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onAsk() {
    if (!question.trim()) return;
    setError(null);
    setResult(null);
    setTraceId(null);
    setBusy(true);
    try {
      const resp = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const body = await resp.json();
      if (!resp.ok) {
        // guard rejection / no-upload: FastAPI nests the payload under `detail`
        const detail = body.detail;
        if (detail && typeof detail === "object") {
          setError(detail.error as string);
          setTraceId(detail.trace_id as string);
        } else {
          setError(String(detail ?? "Request failed"));
        }
        return;
      }
      const data = body as AskResult;
      setResult(data);
      setTraceId(data.trace_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ maxWidth: 820, margin: "0 auto", display: "grid", gap: 24 }}>
      <h1>Veridata</h1>

      <section>
        <h2>1. Upload a CSV</h2>
        <input type="file" accept=".csv" onChange={onUpload} disabled={busy} />
        {upload && (
          <p>
            Loaded <strong>{upload.row_count}</strong> rows into{" "}
            <code>{upload.table}</code>. Columns:{" "}
            {upload.columns.map((c) => `${c.name} (${c.type})`).join(", ")}
          </p>
        )}
      </section>

      <section>
        <h2>2. Ask a question</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            style={{ flex: 1, padding: 8 }}
            value={question}
            placeholder="How many rows are there?"
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onAsk()}
            disabled={!upload || busy}
          />
          <button onClick={onAsk} disabled={!upload || busy}>
            Ask
          </button>
        </div>
        {!upload && <p style={{ color: "#888" }}>Upload a CSV first.</p>}
      </section>

      {error && <p style={{ color: "crimson" }}>Error: {error}</p>}

      {result && (
        <section>
          <h2>Answer</h2>
          <ResultTable answer={result.answer} />
          <h3>SQL</h3>
          <pre style={{ background: "#f4f4f4", padding: 12, overflowX: "auto" }}>{result.sql}</pre>
        </section>
      )}

      {traceId && (
        <p style={{ color: "#888" }}>
          Trace ID: <code>{traceId}</code>
        </p>
      )}
    </main>
  );
}

function ResultTable({ answer }: { answer: Answer }) {
  return (
    <table style={{ borderCollapse: "collapse" }}>
      <thead>
        <tr>
          {answer.columns.map((c) => (
            <th key={c} style={{ border: "1px solid #ccc", padding: "4px 8px", textAlign: "left" }}>
              {c}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {answer.rows.map((row, i) => (
          <tr key={i}>
            {row.map((cell, j) => (
              <td key={j} style={{ border: "1px solid #ccc", padding: "4px 8px" }}>
                {String(cell)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
