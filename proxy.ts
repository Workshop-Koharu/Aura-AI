import type { NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/proxy";

export async function proxy(request: NextRequest) {
  return updateSession(request);
}

// Only refresh Supabase sessions on routes that actually need them.
// Public pages and static assets bypass the auth proxy entirely.
export const config = {
  matcher: ["/chat/:path*", "/settings/:path*", "/api/:path*", "/auth/:path*"],
};
