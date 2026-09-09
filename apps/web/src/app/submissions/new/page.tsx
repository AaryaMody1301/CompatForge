import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { devices } from "@/lib/catalog";
import { getSupabaseConfig } from "@/lib/supabase/config";
import { createServerSupabaseClient } from "@/lib/supabase/server";

import { submitCommunityEvidence } from "../actions";

export const metadata: Metadata = {
  title: "New community submission",
};

type PageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

const ERRORS: Record<string, string> = {
  unconfigured: "Community authentication is not configured on this deployment.",
  missing_field: "Complete every required field before submitting.",
  field_too_long: "One or more values exceed the community-submission contract limits.",
  invalid_choice: "One of the selected configuration values is unsupported.",
  invalid_device: "Select a device currently reviewed by CompatForge.",
  invalid_handoff: "Enter the lowercase SHA-256 printed for your approved contribution handoff.",
  conditions_required: "A conditional result must include at least one condition.",
  limitations_required: "Document at least one limitation of this reproduction.",
  steps_too_short: "Provide at least 20 characters describing how you reproduced the result.",
  invalid_timestamp: "Use an ISO 8601 observation time with Z or an explicit UTC offset.",
  future_timestamp: "The observation time cannot be in the future.",
  invalid_reference: "Reference links must be valid HTTPS URLs.",
  consent_required: "Anonymized-publication consent is required before entering review.",
  too_many_items: "One of the list fields contains too many items.",
  schema_validation_failed: "The normalized submission did not satisfy the public JSON Schema.",
  rate_limit: "Submission rate limit reached. Try again after the rolling window clears.",
  submit_failed: "The submission could not be accepted by the moderation database.",
};

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function NewSubmissionPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const errorCode = first(params.error);

  if (!getSupabaseConfig()) {
    return (
      <main className="shell page-stack">
        <section className="compact-hero">
          <p className="eyebrow">Community evidence</p>
          <h1>Submission service is not configured.</h1>
          <p className="lede">
            Add the Supabase project URL and publishable key before accepting authenticated reports.
          </p>
          <Link className="button" href="/submissions">
            Back to submissions
          </Link>
        </section>
      </main>
    );
  }

  const supabase = await createServerSupabaseClient();
  const { data } = supabase ? await supabase.auth.getUser() : { data: { user: null } };
  if (!data.user) {
    redirect("/submissions?auth=required");
  }

  return (
    <main className="shell page-stack">
      <section className="compact-hero">
        <p className="eyebrow">New community reproduction</p>
        <h1>Describe what you actually reproduced.</h1>
        <p className="lede">
          This form creates a private moderation record. It does not publish evidence and it does not
          accept raw diagnostic files, serial numbers, network identifiers, or unrelated USB inventory.
        </p>
        <div className="notice">
          <p>
            First run the local <code>compatforge-hw prepare-contribution --approve-export</code> flow.
            Paste only its SHA-256 below; keep the inspected handoff file locally unless a moderator
            explicitly requests additional context later.
          </p>
        </div>
      </section>

      <section>
        {errorCode ? <div className="notice error-notice">{ERRORS[errorCode] ?? ERRORS.submit_failed}</div> : null}

        <form action={submitCommunityEvidence} className="community-form">
          <fieldset className="form-section">
            <legend>1. Handoff and device</legend>
            <label>
              Reviewed device
              <select name="target_device_id" required defaultValue="">
                <option value="" disabled>Select a device</option>
                {devices.map((device) => (
                  <option key={device.id} value={device.id}>
                    {device.manufacturer} {device.name} — {device.id}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Approved handoff SHA-256
              <input
                name="handoff_sha256"
                required
                inputMode="text"
                minLength={64}
                maxLength={64}
                pattern="[0-9a-fA-F]{64}"
                placeholder="64 hexadecimal characters"
              />
            </label>
          </fieldset>

          <fieldset className="form-section">
            <legend>2. Configuration</legend>
            <div className="grid grid-two form-grid">
              <label>
                Host manufacturer <span className="optional">optional</span>
                <input name="host_manufacturer" maxLength={200} />
              </label>
              <label>
                Host model <span className="optional">optional</span>
                <input name="host_model" maxLength={200} />
              </label>
              <label>
                Operating system
                <select name="os_family" required defaultValue="">
                  <option value="" disabled>Select OS</option>
                  <option value="windows">Windows</option>
                  <option value="macos">macOS</option>
                  <option value="ubuntu">Ubuntu</option>
                  <option value="linux">Other Linux</option>
                  <option value="unknown">Unknown</option>
                </select>
              </label>
              <label>
                OS version
                <input name="os_version" required maxLength={100} placeholder="e.g. 11 24H2" />
              </label>
              <label>
                OS build <span className="optional">optional</span>
                <input name="os_build" maxLength={100} />
              </label>
              <label>
                CPU architecture
                <select name="architecture" required defaultValue="">
                  <option value="" disabled>Select architecture</option>
                  <option value="x86_64">x86-64</option>
                  <option value="arm64">ARM64</option>
                  <option value="unknown">Unknown</option>
                </select>
              </label>
              <label>
                Connection path
                <select name="connection_path" required defaultValue="">
                  <option value="" disabled>Select connection</option>
                  <option value="direct_port">Direct USB port</option>
                  <option value="usb_hub">USB hub/dock</option>
                  <option value="unspecified">Unspecified / not verified</option>
                </select>
              </label>
            </div>

            <div className="grid grid-three form-grid">
              <label>
                Driver name <span className="optional">optional</span>
                <input name="driver_name" maxLength={200} />
              </label>
              <label>
                Driver provider <span className="optional">optional</span>
                <input name="driver_provider" maxLength={200} />
              </label>
              <label>
                Driver version <span className="optional">optional</span>
                <input name="driver_version" maxLength={200} />
              </label>
            </div>
          </fieldset>

          <fieldset className="form-section">
            <legend>3. Reproduction</legend>
            <div className="grid grid-two form-grid">
              <label>
                Observed outcome
                <select name="outcome" required defaultValue="">
                  <option value="" disabled>Select outcome</option>
                  <option value="works">Works</option>
                  <option value="works_with_conditions">Works with conditions</option>
                  <option value="fails">Fails</option>
                </select>
              </label>
              <label>
                Observed at
                <input
                  name="observed_at"
                  required
                  maxLength={100}
                  placeholder="2026-09-08T10:30:00+05:30"
                />
                <span className="optional">ISO 8601 with Z or an explicit UTC offset.</span>
              </label>
              <label>
                Firmware version <span className="optional">optional</span>
                <input name="firmware_version" maxLength={200} />
              </label>
              <label>
                Supporting software version <span className="optional">optional</span>
                <input name="software_version" maxLength={200} />
              </label>
            </div>

            <label>
              Reproduction steps
              <textarea
                name="steps_summary"
                required
                minLength={20}
                maxLength={4000}
                rows={7}
                placeholder="Describe the exact operation you attempted, what you expected, and what happened."
              />
            </label>
            <label>
              Conditions <span className="optional">one per line; required for a conditional result</span>
              <textarea name="conditions" rows={4} placeholder="Example: Direct USB 3 port required" />
            </label>
            <label>
              Limitations <span className="optional">one per line; at least one required</span>
              <textarea
                name="limitations"
                required
                rows={4}
                placeholder="Example: Only tested one firmware version"
              />
            </label>
            <label>
              Supporting references <span className="optional">optional; HTTPS URL per line, max 5</span>
              <textarea name="references" rows={4} placeholder="https://example.com/relevant-source" />
            </label>
          </fieldset>

          <fieldset className="form-section consent-section">
            <legend>4. Review boundary</legend>
            <label className="checkbox-row">
              <input name="anonymized_publication" type="checkbox" value="yes" required />
              <span>
                I consent to an anonymized reviewed observation being published later if moderators
                accept this reproduction. This submission itself remains private and evidence-ready is false.
              </span>
            </label>
            <p className="meta">
              Database limits: 5 submissions per rolling hour and 20 per rolling 24 hours. Similar
              fingerprints are flagged for review but are not rejected automatically.
            </p>
          </fieldset>

          <div className="actions">
            <button className="button-primary" type="submit">Submit for review</button>
            <Link className="button" href="/submissions">Cancel</Link>
          </div>
        </form>
      </section>
    </main>
  );
}
