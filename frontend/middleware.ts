// Next.js middleware entrypoint (spec 007 task 3). Delegates to the Supabase
// session refresh + auth gate. The matcher skips static assets and image files
// so only real page/navigation requests pay the cost.

import { type NextRequest } from "next/server";

import { updateSession } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  return await updateSession(request);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
