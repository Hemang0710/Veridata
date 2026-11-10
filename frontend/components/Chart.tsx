// Renders a backend-decided ChartSpec beneath a verified answer (spec 005 task 3).
// Thin client: draws exactly what the spec says and nothing when there's no spec
// (not chartable, or a low/abstained answer the system doesn't trust).
"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ChartSpec } from "@/lib/api";

const ACCENT = "#2563eb";
const GRID = "#e5e5e5";

export default function Chart({ spec }: { spec?: ChartSpec | null }) {
  if (!spec) return null; // no chart: layout unchanged

  const data = spec.labels.map((label, i) => ({ label, value: spec.values[i] }));
  const axisLabel = (text: string, axis: "x" | "y") =>
    axis === "x"
      ? { value: text, position: "insideBottom" as const, offset: -4, fill: "#666", fontSize: 12 }
      : { value: text, angle: -90, position: "insideLeft" as const, fill: "#666", fontSize: 12 };

  return (
    <ResponsiveContainer width="100%" height={280}>
      {spec.type === "bar" ? (
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 20, left: 8 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} label={axisLabel(spec.x_title, "x")} />
          <YAxis tick={{ fontSize: 12 }} label={axisLabel(spec.y_title, "y")} />
          <Tooltip />
          <Bar dataKey="value" name={spec.y_title} fill={ACCENT} radius={[2, 2, 0, 0]} />
        </BarChart>
      ) : (
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 20, left: 8 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} label={axisLabel(spec.x_title, "x")} />
          <YAxis tick={{ fontSize: 12 }} label={axisLabel(spec.y_title, "y")} />
          <Tooltip />
          <Line dataKey="value" name={spec.y_title} stroke={ACCENT} dot={{ r: 3 }} />
        </LineChart>
      )}
    </ResponsiveContainer>
  );
}
