import type { Metadata } from "next";
import Link from "next/link";

import { devices } from "@/lib/catalog";
import {
  formatArchitecture,
  formatDate,
  formatOsFamily,
  getDeviceEvidence,
  observations,
  supportStatements,
} from "@/lib/evidence";
import { pageMetadata } from "@/lib/site";

export const metadata: Metadata = pageMetadata(
  "Coverage",
  "See which USB identities have reviewed vendor support or observed compatibility evidence, and which remain unknown.",
  "/coverage",
);

const evidenceDeviceIds = new Set([
  ...supportStatements.map((statement) => statement.device_id),
  ...observations.map((observation) => observation.device_id),
]);
const evidenceDevices = devices.filter((device) => evidenceDeviceIds.has(device.id));

export default function CoveragePage() {
  const rows = evidenceDevices.map((device) => {
    const evidence = getDeviceEvidence(device.id);
    const platforms = new Set([
      ...evidence.supportStatements.map(
        (statement) =>
          `${formatOsFamily(statement.scope.operating_system.family)} ${formatArchitecture(statement.scope.architecture)}`,
      ),
      ...evidence.observations.map(
        (observation) =>
          `${formatOsFamily(observation.host.operating_system.family)} ${formatArchitecture(observation.host.architecture)}`,
      ),
    ]);
    const dates = [
      ...evidence.supportStatements.map((statement) => statement.reviewed_at),
      ...evidence.observations.map((observation) => observation.observed_at),
    ].sort();
    return { device, evidence, platforms: [...platforms].sort(), latest: dates.at(-1) };
  });

  const identityOnly = devices.length - evidenceDevices.length;

  return (
    <main className="shell page-stack">
      <section className="compact-hero">
        <p className="eyebrow">Coverage</p>
        <h1>See what the corpus can—and cannot—answer.</h1>
        <p>
          The identity catalog is intentionally much broader than reviewed compatibility evidence.
          Coverage counts evidence presence, not compatibility success.
        </p>
        <div className="metrics">
          <div><strong>{devices.length.toLocaleString("en")}</strong><span>known identities</span></div>
          <div><strong>{evidenceDevices.length.toLocaleString("en")}</strong><span>evidence-backed devices</span></div>
          <div><strong>{supportStatements.length.toLocaleString("en")}</strong><span>{supportStatements.length === 1 ? "support statement" : "support statements"}</span></div>
          <div><strong>{observations.length.toLocaleString("en")}</strong><span>{observations.length === 1 ? "observation" : "observations"}</span></div>
        </div>
      </section>

      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Reviewed evidence</p>
            <h2>Evidence-backed devices.</h2>
            <p>
              {identityOnly.toLocaleString("en")} catalog identities currently have no reviewed
              compatibility evidence and therefore remain unknown.
            </p>
          </div>
          <Link href="/devices">Browse all identities</Link>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Device</th><th>Platforms</th><th>Support</th><th>Observed</th><th>Latest evidence</th></tr></thead>
            <tbody>
              {rows.map(({ device, evidence, platforms, latest }) => (
                <tr key={device.id}>
                  <th scope="row"><Link href={`/devices/${device.slug}`}>{device.manufacturer} {device.name}</Link><code>{device.id}</code></th>
                  <td>{platforms.length ? platforms.join(" · ") : "Unknown"}</td>
                  <td>{evidence.supportStatements.length}</td>
                  <td>{evidence.observations.length}</td>
                  <td>{latest ? formatDate(latest) : "No evidence"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <p className="eyebrow">Interpretation</p>
        <h2>Coverage is not confidence.</h2>
        <p>
          A device can have broad vendor-support coverage and still have no host-level observations.
          CompatForge exposes that gap instead of turning documentation volume into a score.
        </p>
        <Link href="/methodology">Read the methodology →</Link>
      </section>
    </main>
  );
}
