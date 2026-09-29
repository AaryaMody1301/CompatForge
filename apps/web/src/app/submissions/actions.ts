"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  parseCommunitySubmission,
  SubmissionFormError,
} from "@/lib/community-submission";
import { createServerSupabaseClient } from "@/lib/supabase/server";

function errorCode(error: unknown) {
  if (error instanceof SubmissionFormError) {
    return error.code;
  }

  const message =
    typeof error === "object" && error && "message" in error
      ? String(error.message)
      : String(error);

  if (message.includes("submission rate limit exceeded")) {
    return "rate_limit";
  }
  return "submit_failed";
}

export type SubmissionActionState = { error: string | null };

export async function submitCommunityEvidence(
  _previous: SubmissionActionState,
  formData: FormData,
): Promise<SubmissionActionState> {
  const supabase = await createServerSupabaseClient();
  if (!supabase) {
    return { error: "unconfigured" };
  }

  const { data: authData, error: authError } = await supabase.auth.getUser();
  if (authError || !authData.user) {
    redirect("/submissions?auth=required");
  }

  let submission;
  try {
    submission = parseCommunitySubmission(formData);
  } catch (error) {
    return { error: errorCode(error) };
  }

  const { data, error } = await supabase.rpc("submit_community_evidence", { submission });
  if (error) {
    return { error: errorCode(error) };
  }

  revalidatePath("/submissions");
  redirect(`/submissions?submitted=${encodeURIComponent(String(data))}`);
}
