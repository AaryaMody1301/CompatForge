import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { curatedDevices, getDeviceBySlug } from "@/lib/catalog";
import {
  formatArchitecture,
  formatConnection,
  formatDate,
  formatOsFamily,
  formatReleaseChannel,
  formatVersionScope,
  getDeviceEvidence,
} from "@/lib/evidence";
import { countLabel, pageMetadata } from "@/lib/site";

export const dynamicParams = true;

export function generateStaticParams() {
  return curatedDevices.map((device) => ({ slug: device.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const device = getDeviceBySlug(slug);
  if (!device) {
    return { title: "Device not found", robots: { index: false, follow: false } };
  }
  const metadata = pageMetadata(
    `${device.manufacturer} ${device.name}`,
    device.summary,
    `/devices/${device.slug}`,
  );
  const evidence = getDeviceEvidence(device.id);
  const indexable =
    device.curated_metadata ||
    evidence.supportStatements.length > 0 ||
    evidence.observations.length > 0;
  return indexable
    ? metadata
    : { ...metadata, robots: { index: false, follow: true } };
}

export default async function DevicePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const device = getDeviceBySlug(slug);
  if (!device) notFound();

  const evidence = getDeviceEvidence(device.id);
  const hasEvidence = evidence.supportStatements.length > 0 || evidence.observations.length > 0;
  const timeline = [
    ...evidence.supportStatements.map((statement) => ({
      id: statement.statement_id,
      date: statement.reviewed_at,
      type: "Support reviewed",
      label: `${formatOsFamily(statement.scope.operating_system.family)} ${formatArchitecture(statement.scope.architecture)}`,
    })),
    ...evidence.observations.map((observation) => ({
      id: observation.observation_id,
      date: observation.observed_at,
      type: "Observation",
      label: `${formatOsFamily(observation.host.operating_system.family)} ${formatArchitecture(observation.host.architecture)} · ${observation.outcome.replaceAll("_", " ")}`,
    })),
  ].sort((left, right) => right.date.localeCompare(left.date));

  return (
    <main className="shell page-stack">
      <section className="compact-hero">
        <p className="eyebrow">{device.category}</p>
        <h1>{device.manufacturer} {device.name}</h1>
        <p className="lede">{device.summary}</p>
        <div className="inline-meta">
          <code>{device.id}</code>
          <span>{countLabel(evidence.supportStatements.length, "support statement")}</span>
          <span>{countLabel(evidence.observations.length, "observation")}</span>
        </div>
        <div className="actions">
          <Link className="button button-primary" href={`/check?device=${encodeURIComponent(device.id)}`}>
            Check this device
          </Link>
          <a className="button" href={device.identity_source} rel="noreferrer" target="_blank">
            Identity source ↗
          </a>
        </div>
        {!hasEvidence ? (
          <div className="notice">
            <strong>Compatibility evidence is unknown.</strong>
            <p>
              This USB identity is recognized, but CompatForge has not reviewed a matching vendor
              support statement or real-world observation yet.
            </p>
          </div>
        ) : null}
      </section>

      <section>
        <p className="eyebrow">Vendor support</p>
        <h2>Documented platform scope.</h2>
        {evidence.supportStatements.length ? (
          <div className="stack">
            {evidence.supportStatements.map((statement) => (
              <article className="evidence-card" key={statement.statement_id}>
                <div className="evidence-heading">
                  <div>
                    <h3>{formatOsFamily(statement.scope.operating_system.family)} {formatVersionScope(statement)}</h3>
                    <p className="meta">
                      {formatArchitecture(statement.scope.architecture)} · {formatConnection(statement.scope.connection.kind)} · {formatReleaseChannel(statement.release_channel)} · reviewed {formatDate(statement.reviewed_at)}
                    </p>
                  </div>
                  <span className={`badge badge-${statement.support_status}`}>
                    {statement.support_status.replaceAll("_", " ")}
                  </span>
                </div>
                {statement.conditions?.length ? (
                  <ul>{statement.conditions.map((condition) => <li key={condition}>{condition}</li>)}</ul>
                ) : null}
                <p>{statement.evidence.source_note}</p>
                {statement.limitations?.length ? (
                  <div className="notice compact-notice">
                    <strong>Scope limitations</strong>
                    <ul>{statement.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
                  </div>
                ) : null}
                <div className="sources">
                  {statement.evidence.sources.map((source) => (
                    <a href={source.source_url} key={source.source_url} rel="noreferrer" target="_blank">
                      {source.source_title} ↗
                    </a>
                  ))}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <h3>No reviewed vendor statement yet.</h3>
            <p>Known identity does not imply documented platform support.</p>
          </div>
        )}
      </section>

      <section>
        <p className="eyebrow">Observed compatibility</p>
        <h2>Configuration-level reports.</h2>
        {evidence.observations.length ? (
          <div className="stack">
            {evidence.observations.map((observation) => (
              <article className="evidence-card" key={observation.observation_id}>
                <div className="evidence-heading">
                  <div>
                    <h3>{observation.host.manufacturer} {observation.host.model}</h3>
                    <p className="meta">
                      {formatOsFamily(observation.host.operating_system.family)} {observation.host.operating_system.version} · {formatArchitecture(observation.host.architecture)} · {formatConnection(observation.connection_path[0].kind)}
                    </p>
                  </div>
                  <span className={`badge badge-${observation.outcome}`}>
                    {observation.outcome.replaceAll("_", " ")}
                  </span>
                </div>
                {observation.conditions?.length ? (
                  <ul>{observation.conditions.map((condition) => <li key={condition}>{condition}</li>)}</ul>
                ) : null}
                {observation.notes ? <p>{observation.notes}</p> : null}
                {observation.limitations?.length ? (
                  <div className="notice">
                    <strong>Limitations</strong>
                    <ul>{observation.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
                  </div>
                ) : null}
                <a href={observation.evidence.source_url} rel="noreferrer" target="_blank">
                  {observation.evidence.source_title} ↗
                </a>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <h3>No reviewed observation yet.</h3>
            <p>CompatForge will not infer an observed result from identity or vendor support alone.</p>
          </div>
        )}
      </section>

      <section>
        <p className="eyebrow">Timeline</p>
        <h2>When this evidence was observed or reviewed.</h2>
        {timeline.length ? (
          <ol className="timeline">
            {timeline.map((item) => (
              <li key={item.id}>
                <time dateTime={item.date}>{formatDate(item.date)}</time>
                <div><strong>{item.type}</strong><span>{item.label}</span></div>
              </li>
            ))}
          </ol>
        ) : (
          <div className="empty-state">
            <h3>No evidence timeline yet.</h3>
            <p>This page will populate as reviewed compatibility evidence is added.</p>
          </div>
        )}
      </section>
    </main>
  );
}
