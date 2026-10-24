// Pick a CSV, upload it, show the detected columns + row count (spec 004 task 3).
"use client";

import { useState } from "react";

import { ApiError, upload, type UploadResponse } from "@/lib/api";

export default function UploadPanel({ onLoaded }: { onLoaded: () => void }) {
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleFile(file: File) {
    setBusy(true);
    setError(null);
    try {
      const res = await upload(file);
      setResult(res);
      onLoaded();
    } catch (err) {
      setResult(null);
      setError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ border: "1px solid #e5e5e5", borderRadius: 8, padding: 20, display: "grid", gap: 12 }}>
      <label style={{ fontWeight: 600 }}>Upload a CSV</label>
      <input
        type="file"
        accept=".csv,text/csv"
        disabled={busy}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleFile(file);
        }}
      />
      {busy && <p style={{ margin: 0, color: "#888" }}>Uploading…</p>}
      {error && <p style={{ margin: 0, color: "#991b1b" }}>{error}</p>}
      {result && (
        <div style={{ display: "grid", gap: 6 }}>
          <p style={{ margin: 0 }}>
            Loaded <strong>{result.table}</strong> — {result.row_count} rows,{" "}
            {result.columns.length} columns.
          </p>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 14, color: "#555" }}>
            {result.columns.map((c) => (
              <li key={c.name}>
                {c.name}: <span style={{ color: "#888" }}>{c.type}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
