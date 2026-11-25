// Supabase browser client (spec 007 task 3).
// One client per browser session, used by the auth UI and session gating. On
// first creation it wires the access token into lib/api.ts so every backend call
// carries the user's JWT as a Bearer header.
"use client";

import { createBrowserClient } from "@supabase/ssr";

import { setTokenProvider } from "@/lib/api";

let client: ReturnType<typeof createBrowserClient> | undefined;

/** The shared browser client. Reads the public Supabase URL + anon key from env. */
export function getSupabaseBrowserClient() {
  if (!client) {
    client = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    );
    // Hand the access token to the API layer without coupling it to Supabase.
    setTokenProvider(async () => {
      const { data } = await client!.auth.getSession();
      return data.session?.access_token ?? null;
    });
  }
  return client;
}
