// Verified chat UI (spec 004). Holds the page state — whether a CSV is loaded
// and the latest answer — and composes the panels. All transport and types come
// from lib/api.ts; this file renders what the API returns.
"use client";

import { useState } from "react";

import AnswerCard from "@/components/AnswerCard";
import QuestionBox from "@/components/QuestionBox";
import UploadPanel from "@/components/UploadPanel";
import type { AskResponse } from "@/lib/api";

export default function Home() {
  const [ready, setReady] = useState(false);
  const [answer, setAnswer] = useState<AskResponse | null>(null);

  return (
    <main style={{ maxWidth: 820, margin: "0 auto", display: "grid", gap: 24 }}>
      <h1 style={{ margin: 0 }}>Veridata</h1>
      <UploadPanel onLoaded={() => setReady(true)} />
      <QuestionBox disabled={!ready} onAnswer={setAnswer} />
      {answer && <AnswerCard res={answer} />}
    </main>
  );
}
