import type { Metadata } from "next";
import Link from "next/link";

import { getDeviceById } from "@/lib/catalog";
import { getSupabaseConfig } from "@/lib/supabase/config";
import { createServerSupabaseClient } from "@/lib/supabase/server";

export const metadata: Metadata = {
  title: "Community submissions",
  description: "Submit and track privacy-minimized hardware compatibility reproductions.",
};

type DashboardRow = {
  id: string;
  client_submission_id: string;
  device_id: string;
  observed_outcome: string;
  state: string;
  created_at: string;
  updated_at: string;
  duplicate_candidate: boolean;
};

type PageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function authMessage(code: string | undefined) {
  switch (code) {
    case "required":
      return "Sign in with GitHub before creating a community submission.";
    case "unconfigured":
      return "Community authentication is not configured on this deployment yet.";
    case "oauth_start_failed":
    case "callback_failed":
    case "callback_missing_code":
      return "GitHub sign-in could not be completed. Try again or check the Supabase OAuth configuration.";
    default:
      return null;
  }
}

function formatUtc(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

export default async function SubmissionsPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const configured = Boolean(getSupabaseConfig());
  const authNotice = authMessage(first(params.auth));
  const submitted = first(params.submitted);
  const signedOut = first(params.signed_out) === "1";

  const supabase = await createServerSupabaseClient();
  const { data: authData } = supabase
    ? await supabase.auth.getUser()
    : { data: { user: null } };
  const user = authData.user;

  let rows: DashboardRow[] = [];
  let dashboardError = false;
  if (supabase && user) {
    const { data, error } = await supabase.rpc("get_my_submission_dashboard");
    dashboardError = Boolean(error);
    rows = (data ?? []) as DashboardRow[];
  }

  return (
    <main className="shell page-stack">
      <section className="compact-hero">
        <p className="eyebrow">Community evidence</p>
        <h1>Reproductions enter a review queue, not the evidence corpus.</h1>
        <p className="lede">
          Sign in with GitHub to contribute an anonymized compatibility reproduction and track its
          moderation state. CompatForge never auto-publishes a community report.
        </p>
      </section>

      {!configured ? (
        <section>
          <div className="notice">
            <h2>Community auth is not configured</h2>
            <p>
              Add the Supabase project URL and publishable key to this deployment before enabling
              GitHub sign-in. Public compatibility pages remain available without these values.
            </p>
          </div>
        </section>
      ) : !user ? (
        <section>
          <div className="auth-panel">
            <div>
              <p className="kicker">Authentication required</p>
              <h2>Use GitHub only to establish a Supabase user identity.</h2>
              <p>
                CompatForge does not request repository access and does not store GitHub provider
                tokens. Your Supabase user ID is used to enforce Row Level Security on your queue.
              </p>
              {authNotice ? <p className="notice inline-notice">{authNotice}</p> : null}
              {signedOut ? <p className="notice inline-notice">You are signed out.</p> : null}
            </div>
            <Link className="button button-primary" href="/auth/github?next=/submissions">
              Sign in with GitHub
            </Link>
          </div>
        </section>
      ) : (
        <>
          <section>
            <div className="section-heading">
              <div>
                <p className="kicker">Your queue</p>
                <h2>Submission status</h2>
                <p>
                  Only you and moderators can read these rows. Duplicate signals are deliberately
                  opaque and never reveal another contributor's report.
                </p>
              </div>
              <div className="actions compact-actions">
                <Link className="button button-primary" href="/submissions/new">
                  New submission
                </Link>
                <form action="/auth/signout" method="post">
                  <button type="submit">Sign out</button>
                </form>
              </div>
            </div>

            {submitted ? (
              <div className="notice success-notice">
                Submission <code>{submitted}</code> entered the moderation queue.
              </div>
            ) : null}

            {dashboardError ? (
              <div className="notice">
                Submission status could not be loaded. The database API may not be deployed yet.
              </div>
            ) : rows.length === 0 ? (
              <div className="empty-state">
                <p>No community submissions yet.</p>
                <Link href="/submissions/new">Create your first reviewed reproduction</Link>
              </div>
            ) : (
              <div className="status-list">
                {rows.map((row) => {
                  const device = getDeviceById(row.device_id);
                  return (
                    <article className="status-card" key={row.id}>
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
                        <span>Updated: {formatUtc(row.updated_at)}</span>
                      </div>
                      {row.duplicate_candidate ? (
                        <div className="notice compact-notice">
                          Similar configuration evidence exists. Moderators will review it as a
                          duplicate candidate; this does not reject your reproduction.
                        </div>
                      ) : null}
                      <code>{row.id}</code>
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
