import type { Metadata } from "next";
import Link from "next/link";
import { devices, getDeviceById } from "@/lib/catalog";
import {
  architectures,
  connectionKinds,
  formatArchitecture,
  formatConnection,
  formatOsFamily,
  getDeviceEvidence,
  osFamilies,
  resolveCompatibility,
  type Architecture,
  type ConnectionKind,
  type OsFamily,
} from "@/lib/evidence";

export const metadata: Metadata = { title: "Check compatibility" };

type SearchParams = Record<string, string | string[] | undefined>;
type Props = { searchParams: Promise<SearchParams> };

function value(params: SearchParams, key: string) {
  return typeof params[key] === "string" ? params[key] : "";
}

function member<T extends readonly string[]>(values: T, candidate: string, fallback: T[number]) {
  return values.includes(candidate as T[number]) ? (candidate as T[number]) : fallback;
}

export default async function CheckPage({ searchParams }: Props) {
  const params = await searchParams;
  const deviceId = getDeviceById(value(params, "device"))?.id ?? devices[0].id;
  const architecture = member(architectures, value(params, "architecture"), "arm64") as Architecture;
  const osFamily = member(osFamilies, value(params, "os"), "windows") as OsFamily;
  const connectionKind = member(
    connectionKinds,
    value(params, "connection"),
    "direct_port",
  ) as ConnectionKind;
  const osVersion = value(params, "version") || "11";
  const hostManufacturer = value(params, "host_manufacturer");
  const hostModel = value(params, "host_model");
  const hasQuery = Boolean(value(params, "device") && value(params, "architecture") && value(params, "os") && value(params, "connection") && value(params, "version"));
  const device = getDeviceById(deviceId)!;
  const result = hasQuery
    ? resolveCompatibility({
        deviceId,
        architecture,
        osFamily,
        osVersion,
        connectionKind,
        hostManufacturer: hostManufacturer || undefined,
        hostModel: hostModel || undefined,
      })
    : null;
  const related = getDeviceEvidence(deviceId);

  return (
    <main className="shell page-stack">
      <section className="compact-hero">
        <p className="eyebrow">Compatibility checker</p>
        <h1>Ask a configuration-level question.</h1>
        <p>
          Vendor support and observed compatibility are resolved separately. A supported platform can
          still have an observed result of unknown.
        </p>
      </section>

      <section>
        <form className="config-form" action="/check" method="get">
          <label>
            Device
            <select name="device" defaultValue={deviceId} required>
              {devices.map((option) => (
                <option key={option.id} value={option.id}>{option.manufacturer} {option.name}</option>
              ))}
            </select>
          </label>
          <label>
            Operating system
            <select name="os" defaultValue={osFamily} required>
              {osFamilies.map((option) => <option key={option} value={option}>{formatOsFamily(option)}</option>)}
            </select>
          </label>
          <label>
            OS version
            <input name="version" defaultValue={osVersion} required placeholder="11 or 15.6" />
          </label>
          <label>
            Architecture
            <select name="architecture" defaultValue={architecture} required>
              {architectures.map((option) => <option key={option} value={option}>{formatArchitecture(option)}</option>)}
            </select>
          </label>
          <label>
            Connection
            <select name="connection" defaultValue={connectionKind} required>
              {connectionKinds.map((option) => <option key={option} value={option}>{formatConnection(option)}</option>)}
            </select>
          </label>
          <label>
            Host manufacturer <span className="optional">optional</span>
            <input name="host_manufacturer" defaultValue={hostManufacturer} placeholder="Acer" />
          </label>
          <label>
            Host model <span className="optional">optional</span>
            <input name="host_model" defaultValue={hostModel} placeholder="Aspire 14 AI (2025)" />
          </label>
          <button className="button button-primary" type="submit">Check compatibility</button>
        </form>
      </section>

      {result ? (
        <section>
          <p className="eyebrow">Result</p>
          <h2>{device.manufacturer} {device.name}</h2>
          <div className="result-grid">
            <article className="result-card">
              <span className="result-label">Observed compatibility</span>
              <strong className={`result-state badge-${result.claimState}`}>{result.claimState.replaceAll("_", " ")}</strong>
              <p>
                {result.specificity === "exact" ? "Matched the host, OS version, architecture, and connection path." : null}
                {result.specificity === "host_relaxed" ? "Matched evidence on another or unspecified host; host specificity was relaxed." : null}
                {result.specificity === "os_version_relaxed" ? "Matched evidence only after relaxing both host and OS version." : null}
                {result.specificity === "none" ? "No observation matches the requested architecture, OS family, and connection path." : null}
              </p>
            </article>
            <article className="result-card">
              <span className="result-label">Vendor support</span>
              <strong className={`result-state badge-${result.supportState}`}>{result.supportState.replaceAll("_", " ")}</strong>
              <p>{result.supportStatements.length ? `${result.supportStatements.length} best-matching support statement(s).` : "No reviewed vendor statement matches this request."}</p>
            </article>
          </div>

          {[...result.observationConditions, ...result.supportConditions].length ? (
            <div className="notice">
              <strong>Conditions</strong>
              <ul>{[...new Set([...result.observationConditions, ...result.supportConditions])].map((condition) => <li key={condition}>{condition}</li>)}</ul>
            </div>
          ) : null}

          <div className="stack compact-stack">
            {result.observations.map((observation) => (
              <article className="evidence-card" key={observation.observation_id}>
                <h3>Matched observation</h3>
                <p>{observation.host.manufacturer} {observation.host.model} · {observation.evidence.source_title}</p>
                <a href={observation.evidence.source_url} rel="noreferrer" target="_blank">Open source ↗</a>
              </article>
            ))}
            {result.supportStatements.map((statement) => (
              <article className="evidence-card" key={statement.statement_id}>
                <h3>Matched support statement</h3>
                <p>{statement.evidence.source_note}</p>
                <div className="sources">
                  {statement.evidence.sources.map((source) => <a href={source.source_url} key={source.source_url} rel="noreferrer" target="_blank">{source.source_title} ↗</a>)}
                </div>
              </article>
            ))}
          </div>

          {result.observations.length === 0 && related.observations.length > 0 ? (
            <div className="notice">
              <strong>Related observation exists, but it does not match this query.</strong>
              <p>CompatForge keeps connection-path and architecture mismatches from silently becoming a successful claim.</p>
              <Link href={`/devices/${device.slug}`}>Inspect all evidence for this device →</Link>
            </div>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}
