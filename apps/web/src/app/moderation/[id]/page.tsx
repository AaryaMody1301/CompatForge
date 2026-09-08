import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getDeviceById } from "@/lib/catalog";
import { createServerSupabaseClient } from "@/lib/supabase/server";

import {
  publishCommunitySubmission,
  reviewCommunitySubmission,
} from "../actions";

export const metadata: Metadata = {
  title: "Review community submission",
  description: "Validate, review, accept, and publish a community compatibility reproduction.",
};

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

type SubmissionDetail = {
  submission: {
    id: string;
    device_id: string;
    observed_outcome: string;
    state: string;
    payload: Record<string, unknown>;
    payload_sha256: string;
    submission_fingerprint: string;
    published_observation_id: string | null;
    created_at: string;
    updated_at: string;
  };
  moderation: {
    validation_errors: string[];
    risk_flags: string[];
    decision_reason: string | null;
    reviewer_assigned: boolean;
    updated_at: string | null;
  };
  candidate: null | {
    observation_id: string;
    observation: Record<string, unknown>;
    observation_sha256: string;
    source_payload_sha256: string;
    created_at: string;
    published_at: string | null;
    snapshot_commit_sha: string | null;
  };
  events: Array<{
    actor_kind: string;
    from_state: string | null;
    to_state: string;
    reason: string | null;
    created_at: string;
  }>;
};

type PageProps = {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function formatUtc(value: string | null) {
  if (!value) return "Not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

function actionError(code: string | undefined) {
  switch (code) {
    case "forbidden":
      return "Your authenticated account does not have the moderator role required for this action.";
    case "blockers":
      return "This report still has canonicalization blockers. Reject it with an actionable reason or request a corrected resubmission outside this queue.";
    case "state":
      return "The requested action is not valid from the submission's current lifecycle state.";
    case "hash":
      return "Publication hashes did not match the accepted candidate or the snapshot commit format.";
    case "reason":
      return "Acceptance and rejection require a decision reason of at least 10 characters.";
    case "unconfigured":
      return "Community moderation is not configured on this deployment.";
    case "action_failed":
      return "The moderation action failed at the database boundary.";
    default:
      return null;
  }
}

function updatedMessage(action: string | undefined) {
  return {
    validate: "Submission validated and publication blockers recorded.",
    queue_review: "Submission moved to pending review.",
    accept: "Submission accepted and an immutable canonical observation candidate was created.",
    reject: "Submission rejected with an auditable decision reason.",
    published: "Publication receipt recorded against the merged static snapshot commit.",
  }[action ?? ""] ?? null;
}

function ReviewForm({ id, action, label, requireReason = false }: {
  id: string;
  action: "validate" | "queue_review" | "accept" | "reject";
  label: string;
  requireReason?: boolean;
}) {
  return (
    <form action={reviewCommunitySubmission} className="form-section">
      <input name="submission_id" type="hidden" value={id} />
      <input name="review_action" type="hidden" value={action} />
      <label>
        Decision reason {requireReason ? "" : "(optional)"}
        <textarea
          maxLength={1000}
          minLength={requireReason ? 10 : undefined}
          name="decision_reason"
          placeholder={requireReason ? "Record the evidence-based reason for this decision." : "Optional audit note."}
          required={requireReason}
        />
      </label>
      <button className={action === "reject" ? "button" : "button button-primary"} type="submit">
        {label}
      </button>
    </form>
  );
}

export default async function ModerationDetailPage({ params, searchParams }: PageProps) {
  const { id } = await params;
  const query = await searchParams;
  if (!UUID_PATTERN.test(id)) notFound();

  const supabase = await createServerSupabaseClient();
  if (!supabase) {
    return (
      <main className="shell page-stack">
        <section className="compact-hero">
          <p className="eyebrow">Moderator access</p>
          <h1>Community moderation is not configured.</h1>
        </section>
      </main>
    );
  }

  const { data: authData } = await supabase.auth.getUser();
  if (!authData.user) {
    return (
      <main className="shell page-stack">
        <section className="compact-hero">
          <p className="eyebrow">Moderator access</p>
          <h1>Sign in before reviewing this submission.</h1>
          <div className="actions">
            <Link className="button button-primary" href={`/auth/github?next=/moderation/${id}`}>
              Sign in with GitHub
            </Link>
          </div>
        </section>
      </main>
    );
  }

  const { data: role } = await supabase.rpc("get_moderator_role");
  if (!role) {
    return (
      <main className="shell page-stack">
        <section className="compact-hero">
          <p className="eyebrow">Moderator access</p>
          <h1>Your account is not in the moderator allowlist.</h1>
          <div className="actions"><Link className="button" href="/submissions">Return</Link></div>
        </section>
      </main>
    );
  }

  const { data, error } = await supabase.rpc("get_moderation_submission", { submission_id: id });
  if (error) {
    return (
      <main className="shell page-stack">
        <section className="compact-hero">
          <p className="eyebrow">Moderation error</p>
          <h1>The bounded review record could not be loaded.</h1>
          <div className="actions"><Link className="button" href="/moderation">Back to queue</Link></div>
        </section>
      </main>
    );
  }
  if (!data) notFound();

  const detail = data as SubmissionDetail;
  const submission = detail.submission;
  const device = getDeviceById(submission.device_id);
  const errorNotice = actionError(first(query.error));
  const successNotice = updatedMessage(first(query.updated));

  return (
    <main className="shell page-stack">
      <section className="compact-hero">
        <p className="eyebrow">Community evidence review</p>
        <h1>{device?.name ?? submission.device_id}</h1>
        <p className="lede">
          Review the privacy-minimized reproduction, publication blockers, audit history, and any
          canonical candidate without exposing the submitter's identity in this product surface.
        </p>
        <div className="inline-meta">
          <span>Role: {String(role)}</span>
          <span>Outcome: {submission.observed_outcome.replaceAll("_", " ")}</span>
          <span className={`badge badge-${submission.state}`}>{submission.state.replaceAll("_", " ")}</span>
        </div>
        <div className="actions">
          <Link className="button" href="/moderation">Back to queue</Link>
        </div>
      </section>

      <section>
        {errorNotice ? <div className="notice error-notice">{errorNotice}</div> : null}
        {successNotice ? <div className="notice success-notice">{successNotice}</div> : null}

        <div className="grid grid-two">
          <article className="card">
            <p className="kicker">Provenance</p>
            <h3>Private source record</h3>
            <p>Payload SHA-256</p>
            <code>{submission.payload_sha256}</code>
            <p>Semantic fingerprint</p>
            <code>{submission.submission_fingerprint}</code>
            <p className="meta">Created: {formatUtc(submission.created_at)}</p>
          </article>
          <article className="card">
            <p className="kicker">Review metadata</p>
            <h3>Publication blockers and risk signals</h3>
            <p>Blockers: {detail.moderation.validation_errors.length}</p>
            <p>Risk flags: {detail.moderation.risk_flags.length}</p>
            <p>Reviewer assigned: {detail.moderation.reviewer_assigned ? "yes" : "no"}</p>
            {detail.moderation.decision_reason ? <p>{detail.moderation.decision_reason}</p> : null}
          </article>
        </div>

        {detail.moderation.validation_errors.length > 0 ? (
          <div className="notice error-notice">
            <strong>Canonicalization blockers</strong>
            <ul>{detail.moderation.validation_errors.map((item) => <li key={item}>{item}</li>)}</ul>
          </div>
        ) : null}
        {detail.moderation.risk_flags.length > 0 ? (
          <div className="notice">
            <strong>Risk signals</strong>
            <ul>{detail.moderation.risk_flags.map((item) => <li key={item}>{item.replaceAll("_", " ")}</li>)}</ul>
          </div>
        ) : null}
      </section>

      <section>
        <p className="kicker">Submitted reproduction</p>
        <h2>Normalized private payload</h2>
        <p>
          This is the allowlisted community submission, not a raw diagnostic upload. It remains
          evidence-ready false until the separate reviewed conversion and publication gates complete.
        </p>
        <pre className="json-preview"><code>{JSON.stringify(submission.payload, null, 2)}</code></pre>
      </section>

      {detail.candidate ? (
        <section>
          <p className="kicker">Canonical candidate</p>
          <h2>{detail.candidate.observation_id}</h2>
          <p>
            Acceptance freezes this exact observation payload. Its SHA-256 must match the value used
            by the public snapshot promotion before an admin may record publication.
          </p>
          <div className="inline-meta">
            <span>Candidate SHA-256: <code>{detail.candidate.observation_sha256}</code></span>
            <span>Created: {formatUtc(detail.candidate.created_at)}</span>
            <span>Snapshot commit: {detail.candidate.snapshot_commit_sha ?? "not published"}</span>
          </div>
          <pre className="json-preview"><code>{JSON.stringify(detail.candidate.observation, null, 2)}</code></pre>
        </section>
      ) : null}

      <section>
        <p className="kicker">Lifecycle audit</p>
        <h2>State transitions</h2>
        <ol className="timeline">
          {detail.events.map((event, index) => (
            <li key={`${event.created_at}-${index}`}>
              <time>{formatUtc(event.created_at)}</time>
              <div>
                <strong>{event.from_state ?? "new"} → {event.to_state}</strong>
                <span>Actor: {event.actor_kind}</span>
                {event.reason ? <span>{event.reason}</span> : null}
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section>
        <p className="kicker">Moderator actions</p>
        <h2>Advance only through explicit gates</h2>
        <div className="stack compact-stack">
          {submission.state === "submitted" ? (
            <ReviewForm action="validate" id={submission.id} label="Validate submission" />
          ) : null}
          {submission.state === "validated" ? (
            <>
              <ReviewForm action="queue_review" id={submission.id} label="Move to pending review" />
              <ReviewForm action="reject" id={submission.id} label="Reject submission" requireReason />
            </>
          ) : null}
          {submission.state === "pending_review" ? (
            <>
              <ReviewForm action="accept" id={submission.id} label="Accept and freeze canonical candidate" requireReason />
              <ReviewForm action="reject" id={submission.id} label="Reject submission" requireReason />
            </>
          ) : null}
          {submission.state === "accepted" ? (
            <>
              <ReviewForm action="reject" id={submission.id} label="Reject accepted candidate" requireReason />
              {String(role) === "admin" && detail.candidate ? (
                <form action={publishCommunitySubmission} className="form-section">
                  <input name="submission_id" type="hidden" value={submission.id} />
                  <input
                    name="expected_observation_sha256"
                    type="hidden"
                    value={detail.candidate.observation_sha256}
                  />
                  <p className="kicker">Admin publication receipt</p>
                  <p>
                    Use this only after the exact candidate is present in a reviewed public snapshot
                    and that snapshot commit is merged to the canonical branch.
                  </p>
                  <label>
                    Full merged snapshot commit SHA
                    <input
                      autoComplete="off"
                      maxLength={40}
                      minLength={40}
                      name="snapshot_commit_sha"
                      pattern="[0-9A-Fa-f]{40}"
                      placeholder="40-character Git commit SHA"
                      required
                    />
                  </label>
                  <button className="button button-primary" type="submit">Record publication</button>
                </form>
              ) : null}
            </>
          ) : null}
          {submission.state === "published" ? (
            <div className="notice success-notice">
              Published as <code>{submission.published_observation_id}</code>.
            </div>
          ) : null}
          {submission.state === "rejected" ? (
            <div className="notice">This submission is terminally rejected.</div>
          ) : null}
        </div>
      </section>
    </main>
  );
}
