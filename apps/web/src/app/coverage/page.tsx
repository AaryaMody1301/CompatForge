import type { Metadata } from "next";
import Link from "next/link";
import { devices } from "@/lib/catalog";
import { formatArchitecture, formatDate, formatOsFamily, getDeviceEvidence, observations, supportStatements } from "@/lib/evidence";

export const metadata: Metadata = { title: "Coverage" };

export default function CoveragePage() {
  const rows = devices.map((device) => {
    const evidence = getDeviceEvidence(device.id);
    const platforms = new Set([
      ...evidence.supportStatements.map((statement) => `${formatOsFamily(statement.scope.operating_system.family)} ${formatArchitecture(statement.scope.architecture)}`),
      ...evidence.observations.map((observation) => `${formatOsFamily(observation.host.operating_system.family)} ${formatArchitecture(observation.host.architecture)}`),
    ]);
    const dates = [
      ...evidence.supportStatements.map((statement) => statement.reviewed_at),
      ...evidence.observations.map((observation) => observation.observed_at),
    ].sort();
    return { device, evidence, platforms: [...platforms].sort(), latest: dates.at(-1) };
  });

  return (
    <main className="shell page-stack">
      <section className="compact-hero">
        <p className="eyebrow">Coverage</p>
        <h1>See what the corpus can—and cannot—answer.</h1>
        <p>Coverage counts evidence presence, not compatibility success. Zero observations is a meaningful gap.</p>
        <div className="metrics">
          <div><strong>{devices.length}</strong><span>devices</span></div>
          <div><strong>{supportStatements.length}</strong><span>support statements</span></div>
          <div><strong>{observations.length}</strong><span>observations</span></div>
        </div>
      </section>

      <section>
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
