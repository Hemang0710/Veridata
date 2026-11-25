// Sign up / log in (spec 007 task 3). Email + password via Supabase. The
// middleware sends logged-out visitors here and bounces them back to the app
// once a session exists.
"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { getSupabaseBrowserClient } from "@/lib/supabase/client";

type Mode = "login" | "signup";

export default function LoginPage() {
  const supabase = getSupabaseBrowserClient();
  const router = useRouter();

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    setNotice(null);

    const { data, error } =
      mode === "login"
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({ email, password });

    setBusy(false);

    if (error) {
      setError(error.message);
      return;
    }
    // Sign up with email confirmation on returns no session until confirmed.
    if (mode === "signup" && !data.session) {
      setNotice("Check your email to confirm your account, then log in.");
      setMode("login");
      return;
    }
    router.push("/");
    router.refresh();
  }

  return (
    <main style={{ maxWidth: 360, margin: "64px auto", display: "grid", gap: 20 }}>
      <h1 style={{ margin: 0 }}>Veridata</h1>
      <p style={{ margin: 0, color: "#555" }}>
        {mode === "login" ? "Log in to your account." : "Create an account."}
      </p>

      <form onSubmit={(e) => void submit(e)} style={{ display: "grid", gap: 12 }}>
        <input
          type="email"
          required
          value={email}
          placeholder="you@example.com"
          autoComplete="email"
          onChange={(e) => setEmail(e.target.value)}
          style={{ padding: "8px 12px", fontSize: 15, border: "1px solid #ccc", borderRadius: 6 }}
        />
        <input
          type="password"
          required
          minLength={6}
          value={password}
          placeholder="Password"
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          onChange={(e) => setPassword(e.target.value)}
          style={{ padding: "8px 12px", fontSize: 15, border: "1px solid #ccc", borderRadius: 6 }}
        />
        <button
          type="submit"
          disabled={busy}
          style={{ padding: "8px 16px", fontSize: 15, borderRadius: 6, cursor: "pointer" }}
        >
          {busy ? "…" : mode === "login" ? "Log in" : "Sign up"}
        </button>
      </form>

      {error && <p style={{ margin: 0, color: "#991b1b" }}>{error}</p>}
      {notice && <p style={{ margin: 0, color: "#166534" }}>{notice}</p>}

      <button
        type="button"
        onClick={() => {
          setMode(mode === "login" ? "signup" : "login");
          setError(null);
          setNotice(null);
        }}
        style={{
          background: "none",
          border: "none",
          color: "#2563eb",
          cursor: "pointer",
          padding: 0,
          fontSize: 14,
          justifySelf: "start",
        }}
      >
        {mode === "login" ? "Need an account? Sign up" : "Have an account? Log in"}
      </button>
    </main>
  );
}
