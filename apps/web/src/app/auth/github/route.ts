import { type NextRequest, NextResponse } from "next/server";

import { createServerSupabaseClient } from "@/lib/supabase/server";

function safeNextPath(value: string | null) {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/submissions";
  }
  return value;
}

export async function GET(request: NextRequest) {
  const supabase = await createServerSupabaseClient();
  if (!supabase) {
    return NextResponse.redirect(new URL("/submissions?auth=unconfigured", request.url));
  }

  const callback = new URL("/auth/callback", request.url);
  callback.searchParams.set("next", safeNextPath(request.nextUrl.searchParams.get("next")));

  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "github",
    options: { redirectTo: callback.toString() },
  });

  if (error || !data.url) {
    return NextResponse.redirect(new URL("/submissions?auth=oauth_start_failed", request.url));
  }

  return NextResponse.redirect(data.url);
}
