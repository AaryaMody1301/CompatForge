"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { createServerSupabaseClient } from "@/lib/supabase/server";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const SNAPSHOT_SHA_PATTERN = /^[0-9a-f]{40}$/i;
const SHA256_PATTERN = /^[0-9a-f]{64}$/i;
const REVIEW_ACTIONS = new Set(["validate", "queue_review", "accept", "reject"]);

function formText(formData: FormData, name: string, maxLength: number, required = true) {
  const entry = formData.get(name);
  const value = typeof entry === "string" ? entry.trim() : "";
  if (required && !value) {
    throw new Error(`missing_${name}`);
  }
  if (value.length > maxLength) {
    throw new Error(`invalid_${name}`);
  }
  return value;
}

function moderationErrorCode(error: unknown) {
  const message =
    typeof error === "object" && error && "message" in error
      ? String(error.message)
      : String(error);

  if (message.includes("authorization required")) return "forbidden";
  if (message.includes("canonicalization blockers")) return "blockers";
  if (message.includes("requires") || message.includes("cannot be rejected")) return "state";
  if (message.includes("SHA")) return "hash";
  if (message.includes("decision reason")) return "reason";
  return "action_failed";
}

async function authenticatedSupabase(detailPath: string) {
  const supabase = await createServerSupabaseClient();
  if (!supabase) {
    redirect(`${detailPath}?error=unconfigured`);
  }

  const { data: authData, error: authError } = await supabase.auth.getUser();
  if (authError || !authData.user) {
    redirect("/submissions?auth=required");
  }

  return supabase;
}

export async function reviewCommunitySubmission(formData: FormData) {
  let submissionId: string;
  let reviewAction: string;
  let decisionReason: string;

  try {
    submissionId = formText(formData, "submission_id", 36);
    if (!UUID_PATTERN.test(submissionId)) throw new Error("invalid_submission_id");

    reviewAction = formText(formData, "review_action", 32);
    if (!REVIEW_ACTIONS.has(reviewAction)) throw new Error("invalid_review_action");

    decisionReason = formText(formData, "decision_reason", 1000, false);
    if ((reviewAction === "accept" || reviewAction === "reject") && decisionReason.length < 10) {
      throw new Error("decision reason must contain at least 10 characters");
    }
  } catch (error) {
    redirect(`/moderation?error=${encodeURIComponent(moderationErrorCode(error))}`);
  }

  const detailPath = `/moderation/${submissionId}`;
  const supabase = await authenticatedSupabase(detailPath);
  const { error } = await supabase.rpc("review_community_submission", {
    submission_id: submissionId,
    review_action: reviewAction,
    decision_reason: decisionReason || null,
  });

  if (error) {
    redirect(`${detailPath}?error=${encodeURIComponent(moderationErrorCode(error))}`);
  }

  revalidatePath("/moderation");
  revalidatePath(detailPath);
  revalidatePath("/submissions");
  redirect(`${detailPath}?updated=${encodeURIComponent(reviewAction)}`);
}

export async function publishCommunitySubmission(formData: FormData) {
  let submissionId: string;
  let snapshotCommitSha: string;
  let expectedObservationSha256: string;

  try {
    submissionId = formText(formData, "submission_id", 36);
    if (!UUID_PATTERN.test(submissionId)) throw new Error("invalid_submission_id");

    snapshotCommitSha = formText(formData, "snapshot_commit_sha", 40).toLowerCase();
    expectedObservationSha256 = formText(
      formData,
      "expected_observation_sha256",
      64,
    ).toLowerCase();

    if (!SNAPSHOT_SHA_PATTERN.test(snapshotCommitSha)) throw new Error("invalid snapshot SHA");
    if (!SHA256_PATTERN.test(expectedObservationSha256)) throw new Error("invalid observation SHA");
  } catch (error) {
    redirect(`/moderation?error=${encodeURIComponent(moderationErrorCode(error))}`);
  }

  const detailPath = `/moderation/${submissionId}`;
  const supabase = await authenticatedSupabase(detailPath);
  const { error } = await supabase.rpc("publish_community_submission", {
    submission_id: submissionId,
    snapshot_commit_sha: snapshotCommitSha,
    expected_observation_sha256: expectedObservationSha256,
  });

  if (error) {
    redirect(`${detailPath}?error=${encodeURIComponent(moderationErrorCode(error))}`);
  }

  revalidatePath("/moderation");
  revalidatePath(detailPath);
  revalidatePath("/submissions");
  redirect(`${detailPath}?updated=published`);
}
