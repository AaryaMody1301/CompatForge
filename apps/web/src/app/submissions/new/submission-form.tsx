"use client";

import { useActionState, type ReactNode } from "react";

import { submitCommunityEvidence, type SubmissionActionState } from "../actions";

export function SubmissionForm({
  children,
  initialError,
  errors,
}: {
  children: ReactNode;
  initialError: string | null;
  errors: Record<string, string>;
}) {
  const [state, formAction] = useActionState<SubmissionActionState, FormData>(
    submitCommunityEvidence,
    { error: initialError },
  );
  return (
    <>
      {state.error ? <div className="notice error-notice" role="alert">{errors[state.error] ?? errors.submit_failed}</div> : null}
      <form action={formAction} className="community-form">{children}</form>
    </>
  );
}
