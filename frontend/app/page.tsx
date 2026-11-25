// Verified chat UI (spec 004; auth added in spec 007 task 3). Holds the page
// state — whether a CSV is loaded and the latest answer — and composes the
// panels. The middleware already gates this route behind a session; here we
// surface the logged-in user and a log-out control.
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import AnswerCard from "@/components/AnswerCard";
import QuestionBox from "@/components/QuestionBox";
import UploadPanel from "@/components/UploadPanel";
import type { AskResponse } from "@/lib/api";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

export default function Home() {
  const supabase = getSupabaseBrowserClient();
  const router = useRouter();

  const [email, setEmail] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [answer, setAnswer] = useState<AskResponse | null>(null);

  useEffect(() => {
    void supabase.auth.getUser().then(({ data }) => setEmail(data.user?.email ?? null));
  }, [supabase]);

  async function logout() {
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <main style={{ maxWidth: 820, margin: "0 auto", display: "grid", gap: 24 }}>
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <h1 style={{ margin: 0 }}>Veridata</h1>
        <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 14 }}>
          {email && <span style={{ color: "#555" }}>{email}</span>}
          <button
            type="button"
            onClick={() => void logout()}
            style={{ padding: "6px 12px", fontSize: 14, borderRadius: 6, cursor: "pointer" }}
          >
            Log out
          </button>
        </div>
      </header>
      <UploadPanel onLoaded={() => setReady(true)} />
      <QuestionBox disabled={!ready} onAnswer={setAnswer} />
      {answer && <AnswerCard res={answer} />}
    </main>
  );
}
