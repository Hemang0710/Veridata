// Renders an /ask result, trust signals first (spec 004 task 4/5). The
// confidence badge is the most prominent element; SQL, rows, and checks live in
// a collapsible "show your work" panel. Thin client: shows what the API returns,
// never recomputes confidence or checks.

import type { AskResponse, Check, Confidence } from "@/lib/api";

const BADGE: Record<Confidence | "abstained", { bg: string; fg: string; label: string }> = {
  high: { bg: "#dcfce7", fg: "#166534", label: "HIGH CONFIDENCE" },
  medium: { bg: "#fef3c7", fg: "#92400e", label: "MEDIUM CONFIDENCE" },
  low: { bg: "#fee2e2", fg: "#991b1b", label: "LOW CONFIDENCE" },
  abstained: { bg: "#fee2e2", fg: "#991b1b", label: "ABSTAINED" },
};

function ConfidenceBadge({ confidence, abstained }: { confidence: Confidence; abstained: boolean }) {
  // Abstain always reads red regardless of the raw level.
  const b = BADGE[abstained ? "abstained" : confidence];
  return (
    <span
      style={{
        display: "inline-block",
        background: b.bg,
        color: b.fg,
        fontSize: 20,
        fontWeight: 700,
        letterSpacing: 0.5,
        padding: "8px 16px",
        borderRadius: 999,
      }}
    >
      {b.label}
    </span>
  );
}

function ResultTable({ columns, rows }: { columns: string[]; rows: unknown[][] }) {
  if (rows.length === 0) return <p style={{ color: "#888", margin: 0 }}>No rows.</p>;
  return (
    <table style={{ borderCollapse: "collapse", fontSize: 14 }}>
      <thead>
        <tr>
          {columns.map((c) => (
            <th key={c} style={{ ...cell, textAlign: "left", fontWeight: 600 }}>
              {c}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i}>
            {row.map((v, j) => (
              <td key={j} style={cell}>
                {String(v)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

const cell: React.CSSProperties = { border: "1px solid #e5e5e5", padding: "4px 10px" };

function CheckRow({ check }: { check: Check }) {
  return (
    <li style={{ margin: "4px 0" }}>
      <span style={{ color: check.passed ? "#166534" : "#991b1b", fontWeight: 600 }}>
        {check.passed ? "✓" : "✗"} {check.name}
      </span>
      {check.detail && <span style={{ color: "#555" }}> — {check.detail}</span>}
    </li>
  );
}

function ShowYourWork({ res }: { res: AskResponse }) {
  return (
    <details style={{ marginTop: 16 }}>
      <summary style={{ cursor: "pointer", fontWeight: 600 }}>Show your work</summary>
      <div style={{ display: "grid", gap: 16, marginTop: 12 }}>
        <section>
          <h4 style={heading}>SQL</h4>
          <pre
            style={{
              margin: 0,
              background: "#f6f8fa",
              padding: 12,
              borderRadius: 6,
              overflowX: "auto",
              fontSize: 13,
            }}
          >
            {res.sql}
          </pre>
        </section>
        <section>
          <h4 style={heading}>Result</h4>
          <ResultTable columns={res.answer.columns} rows={res.answer.rows} />
        </section>
        <section>
          <h4 style={heading}>Checks</h4>
          <ul style={{ margin: 0, paddingLeft: 18, listStyle: "none" }}>
            {res.checks.map((c) => (
              <CheckRow key={c.name} check={c} />
            ))}
          </ul>
        </section>
        <p style={{ color: "#aaa", fontSize: 12, margin: 0 }}>trace id: {res.trace_id}</p>
      </div>
    </details>
  );
}

const heading: React.CSSProperties = { margin: "0 0 6px", fontSize: 13, color: "#666" };

/** Concise answer: a single cell is shown big; otherwise a shape summary. */
function AnswerValue({ columns, rows }: { columns: string[]; rows: unknown[][] }) {
  if (rows.length === 0) return null;
  if (rows.length === 1 && columns.length === 1) {
    return <div style={{ fontSize: 28, fontWeight: 700 }}>{String(rows[0][0])}</div>;
  }
  return (
    <div style={{ fontSize: 16 }}>
      {rows.length} rows × {columns.length} columns
    </div>
  );
}

export default function AnswerCard({ res }: { res: AskResponse }) {
  return (
    <div style={{ border: "1px solid #e5e5e5", borderRadius: 8, padding: 20, display: "grid", gap: 12 }}>
      <ConfidenceBadge confidence={res.confidence} abstained={res.abstained} />
      {res.reason && <p style={{ margin: 0, color: "#333" }}>{res.reason}</p>}
      <AnswerValue columns={res.answer.columns} rows={res.answer.rows} />
      <ShowYourWork res={res} />
    </div>
  );
}
