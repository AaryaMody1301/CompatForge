import { type NextRequest, NextResponse } from "next/server";

import { safeInternalPath } from "@/lib/navigation";
import { getCommunityFeatureState } from "@/lib/supabase/config";
import { createServerSupabaseClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const communityState = getCommunityFeatureState();
  if (communityState !== "ready") {
    const code = communityState === "disabled" ? "disabled" : "unconfigured";
    return NextResponse.redirect(new URL(`/submissions?auth=${code}`, request.url));
  }

  const supabase = await createServerSupabaseClient();
  if (!supabase) {
    return NextResponse.redirect(new URL("/submissions?auth=unconfigured", request.url));
  }

  const callback = new URL("/auth/callback", request.url);
  callback.searchParams.set("next", safeInternalPath(request.nextUrl.searchParams.get("next")));

  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "github",
    options: { redirectTo: callback.toString() },
  });

  if (error || !data.url) {
    return NextResponse.redirect(new URL("/submissions?auth=oauth_start_failed", request.url));
  }

  return NextResponse.redirect(data.url);
}
