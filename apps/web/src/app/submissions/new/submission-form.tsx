"use client";

import { useActionState, useLayoutEffect, useRef, type FormEvent, type ReactNode } from "react";

import { submitCommunityEvidence, type SubmissionActionState } from "../actions";
import { captureSubmissionDraft, restoreSubmissionDraft, type SubmissionFormDraft } from "./form-draft";

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
  const formRef = useRef<HTMLFormElement>(null);
  const draftRef = useRef<SubmissionFormDraft | null>(null);

  function captureDraft(event: FormEvent<HTMLFormElement>) {
    draftRef.current = captureSubmissionDraft(event.currentTarget);
  }

  function restoreDraft() {
    if (formRef.current && draftRef.current) {
      restoreSubmissionDraft(formRef.current, draftRef.current);
    }
  }

  useLayoutEffect(() => {
    if (state.error) restoreDraft();
  }, [state]);

  return (
    <>
      {state.error ? <div className="notice error-notice" role="alert">{errors[state.error] ?? errors.submit_failed}</div> : null}
      <form
        ref={formRef}
        action={formAction}
        className="community-form"
        onSubmit={captureDraft}
        onReset={() => {
          const submittedDraft = draftRef.current;
          if (submittedDraft) {
            window.requestAnimationFrame(() => {
              if (draftRef.current === submittedDraft) restoreDraft();
            });
          }
        }}
      >
        {children}
      </form>
    </>
  );
}
