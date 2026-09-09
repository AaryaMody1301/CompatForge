import { type NextRequest, NextResponse } from "next/server";

import { safeInternalPath } from "@/lib/navigation";
import { createServerSupabaseClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const supabase = await createServerSupabaseClient();
  if (!supabase) {
    return NextResponse.redirect(new URL("/submissions?auth=unconfigured", request.url));
  }

  const code = request.nextUrl.searchParams.get("code");
  if (!code) {
    return NextResponse.redirect(new URL("/submissions?auth=callback_missing_code", request.url));
  }

  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) {
    return NextResponse.redirect(new URL("/submissions?auth=callback_failed", request.url));
  }

  return NextResponse.redirect(
    new URL(safeInternalPath(request.nextUrl.searchParams.get("next")), request.url),
  );
}
