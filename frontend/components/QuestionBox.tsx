// Ask a question over the uploaded dataset, with a loading state (spec 004 task 4).
"use client";

import { useState } from "react";

import { ApiError, ask, type AskResponse } from "@/lib/api";

export default function QuestionBox({
  disabled,
  onAnswer,
}: {
  disabled: boolean;
  onAnswer: (res: AskResponse) => void;
}) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    const q = question.trim();
    if (!q || loading) return;
    setLoading(true);
    setError(null);
    try {
      onAnswer(await ask(q));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Request failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 8 }}>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          type="text"
          value={question}
          disabled={disabled || loading}
          placeholder={disabled ? "Upload a CSV first" : "Ask a question…"}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void submit();
          }}
          style={{ flex: 1, padding: "8px 12px", fontSize: 15, border: "1px solid #ccc", borderRadius: 6 }}
        />
        <button
          type="button"
          onClick={() => void submit()}
          disabled={disabled || loading || !question.trim()}
          style={{ padding: "8px 16px", fontSize: 15, borderRadius: 6, cursor: "pointer" }}
        >
          {loading ? "Asking…" : "Ask"}
        </button>
      </div>
      {error && <p style={{ margin: 0, color: "#991b1b" }}>{error}</p>}
    </div>
  );
}
