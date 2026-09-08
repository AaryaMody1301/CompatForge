import type { Metadata } from "next";
import Link from "next/link";

import { getDeviceById } from "@/lib/catalog";
import { createServerSupabaseClient } from "@/lib/supabase/server";

export const metadata: Metadata = {
  title: "Moderation queue",
  description: "Review community compatibility reproductions before canonical publication.",
};

type ModerationRow = {
  submission_id: string;
  device_id: string;
  observed_outcome: string;
  state: string;
  created_at: string;
  updated_at: string;
  validation_error_count: number;
  risk_flags: string[];
  duplicate_candidate: boolean;
  candidate_observation_id: string | null;
  candidate_sha256: string | null;
};

type PageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function formatUtc(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

function pageError(code: string | undefined) {
  if (code === "forbidden") return "Moderator authorization is required for this action.";
  if (code === "unconfigured") return "Community moderation is not configured on this deployment.";
  if (code) return "The moderation action could not be completed.";
  return null;
}

export default async function ModerationPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const errorNotice = pageError(first(params.error));
  const supabase = await createServerSupabaseClient();

  if (!supabase) {
    return (
      <main className="shell page-stack">
        <section className="compact-hero">
          <p className="eyebrow">Community evidence</p>
          <h1>Moderation is not configured on this deployment.</h1>
          <p className="lede">
            Public compatibility pages remain independent of the hosted moderation database.
          </p>
        </section>
      </main>
    );
  }

  const { data: authData } = await supabase.auth.getUser();
  const user = authData.user;
  if (!user) {
    return (
      <main className="shell page-stack">
        <section className="compact-hero">
          <p className="eyebrow">Moderator access</p>
          <h1>Sign in before opening the review queue.</h1>
          <div className="actions">
            <Link className="button button-primary" href="/auth/github?next=/moderation">
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
          <p className="lede">
            Authentication proves identity. Database membership separately determines review authority.
          </p>
          <div className="actions">
            <Link className="button" href="/submissions">Return to submissions</Link>
          </div>
        </section>
      </main>
    );
  }

  const { data, error } = await supabase.rpc("get_moderation_queue");
  const rows = (data ?? []) as ModerationRow[];
  const counts = rows.reduce<Record<string, number>>((accumulator, row) => {
    accumulator[row.state] = (accumulator[row.state] ?? 0) + 1;
    return accumulator;
  }, {});

  return (
    <main className="shell page-stack">
      <section className="compact-hero">
        <p className="eyebrow">Phase 6C moderation</p>
        <h1>Review reports without turning review authority into publication authority.</h1>
        <p className="lede">
          Validation records publication blockers, acceptance creates an immutable canonical candidate,
          and only admins can record publication after the matching static snapshot commit is merged.
        </p>
        <div className="inline-meta">
          <span>Role: {String(role)}</span>
          <span>Total rows: {rows.length}</span>
          <span>Pending review: {counts.pending_review ?? 0}</span>
          <span>Accepted: {counts.accepted ?? 0}</span>
        </div>
      </section>

      <section>
        <div className="section-heading">
          <div>
            <p className="kicker">Bounded queue</p>
            <h2>Community submissions</h2>
            <p>
              The queue intentionally omits submitter identity. Raw private moderation tables remain
              inaccessible to normal authenticated sessions.
            </p>
          </div>
          <div className="actions compact-actions">
            <Link className="button" href="/submissions">My submissions</Link>
          </div>
        </div>

        {errorNotice ? <div className="notice error-notice">{errorNotice}</div> : null}
        {error ? (
          <div className="notice error-notice">
            The bounded moderation queue could not be loaded.
          </div>
        ) : rows.length === 0 ? (
          <div className="empty-state">No community submissions are waiting in the queue.</div>
        ) : (
          <div className="status-list">
            {rows.map((row) => {
              const device = getDeviceById(row.device_id);
              return (
                <article className="status-card" key={row.submission_id}>
                  <div className="status-header">
                    <div>
                      <p className="kicker">{device?.manufacturer ?? "USB device"}</p>
                      <h3>{device?.name ?? row.device_id}</h3>
                    </div>
                    <span className={`badge badge-${row.state}`}>{row.state.replaceAll("_", " ")}</span>
                  </div>
                  <div className="status-meta">
                    <span>Outcome: {row.observed_outcome.replaceAll("_", " ")}</span>
                    <span>Created: {formatUtc(row.created_at)}</span>
                    <span>Publication blockers: {row.validation_error_count}</span>
                    <span>Risk flags: {row.risk_flags.length}</span>
                  </div>
                  {row.duplicate_candidate ? (
                    <div className="notice compact-notice">
                      Duplicate candidate signal present. This is review context, not an automatic rejection.
                    </div>
                  ) : null}
                  {row.candidate_observation_id ? (
                    <p className="meta">
                      Canonical candidate: <code>{row.candidate_observation_id}</code>
                    </p>
                  ) : null}
                  <div className="card-actions">
                    <Link className="button button-primary" href={`/moderation/${row.submission_id}`}>
                      Review submission
                    </Link>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
