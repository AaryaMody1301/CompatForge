import type { Metadata } from "next";
import Link from "next/link";
import { devices, getDeviceById } from "@/lib/catalog";
import {
  architectures,
  connectionKinds,
  evidenceAge,
  formatArchitecture,
  formatConnection,
  formatDate,
  formatOsFamily,
  formatReleaseChannel,
  getDeviceEvidence,
  osFamilies,
  resolveCompatibility,
  type Architecture,
  type ConnectionKind,
  type OsFamily,
} from "@/lib/evidence";
import { pageMetadata } from "@/lib/site";
import { DeviceSearchInput } from "./device-search-input";

export const metadata: Metadata = pageMetadata(
  "Check compatibility",
  "Check a USB device configuration against reviewed vendor support and observed compatibility evidence.",
  "/check",
);

type SearchParams = Record<string, string | string[] | undefined>;
type Props = { searchParams: Promise<SearchParams> };

function value(params: SearchParams, key: string) {
  return typeof params[key] === "string" ? params[key] : "";
}

function member<T extends readonly string[]>(values: T, candidate: string): T[number] | null {
  return values.includes(candidate as T[number]) ? (candidate as T[number]) : null;
}

export default async function CheckPage({ searchParams }: Props) {
  const params = await searchParams;
  const rawDeviceId = value(params, "device");
  const rawArchitecture = value(params, "architecture");
  const rawOsFamily = value(params, "os");
  const rawConnectionKind = value(params, "connection");
  const rawOsVersion = value(params, "version");
  const rawPath = value(params, "path");
  const connectionPath = rawPath ? rawPath.split(">").map((item) => item.trim()) : [];
  const invalidPath = Boolean(rawPath) && (
    connectionPath.length > 8 || connectionPath.some((item) => !member(connectionKinds, item))
  );
  const osBuild = value(params, "os_build");
  const driverName = value(params, "driver_name");
  const driverVersion = value(params, "driver_version");
  const softwareName = value(params, "software_name");
  const softwareVersion = value(params, "software_version");
  const firmwareVersion = value(params, "firmware_version");
  const usbGeneration = value(params, "usb_generation");

  const requestedDevice = rawDeviceId ? getDeviceById(rawDeviceId) : undefined;
  const requestedArchitecture = rawArchitecture ? member(architectures, rawArchitecture) : null;
  const requestedOsFamily = rawOsFamily ? member(osFamilies, rawOsFamily) : null;
  const requestedConnectionKind = rawConnectionKind
    ? member(connectionKinds, rawConnectionKind)
    : null;

  const defaultDevice = getDeviceById("usb:0403:6001") ?? devices[0];
  const device = requestedDevice ?? defaultDevice;
  const architecture = (requestedArchitecture ?? "x86_64") as Architecture;
  const osFamily = (requestedOsFamily ?? "windows") as OsFamily;
  const connectionKind = (requestedConnectionKind ?? "direct_port") as ConnectionKind;
  const osVersion = rawOsVersion || "11";
  const hostManufacturer = value(params, "host_manufacturer");
  const hostModel = value(params, "host_model");

  const hasQuery = Boolean(
    rawDeviceId && rawArchitecture && rawOsFamily && rawConnectionKind && rawOsVersion,
  );
  const invalidFields = [
    rawDeviceId && !requestedDevice ? "device" : null,
    rawArchitecture && !requestedArchitecture ? "architecture" : null,
    rawOsFamily && !requestedOsFamily ? "operating system" : null,
    rawConnectionKind && !requestedConnectionKind ? "connection" : null,
    invalidPath ? "connection path" : null,
    rawOsVersion && !/^\d+(?:\.\d+)*$/.test(rawOsVersion.trim()) ? "OS version" : null,
    usbGeneration && !["1.1", "2.0", "3.0", "3.1", "3.2", "4"].includes(usbGeneration) ? "USB generation" : null,
  ].filter((field): field is string => field !== null);
  const hasInvalidQuery = invalidFields.length > 0;

  const result = hasQuery && !hasInvalidQuery && requestedDevice
    ? resolveCompatibility({
        deviceId: requestedDevice.id,
        architecture,
        osFamily,
        osVersion,
        connectionKind,
        connectionPath: rawPath ? connectionPath as ConnectionKind[] : undefined,
        hostManufacturer: hostManufacturer || undefined,
        hostModel: hostModel || undefined,
        osBuild: osBuild || undefined,
        driverName: driverName || undefined,
        driverVersion: driverVersion || undefined,
        softwareName: softwareName || undefined,
        softwareVersion: softwareVersion || undefined,
        firmwareVersion: firmwareVersion || undefined,
        usbGeneration: usbGeneration || undefined,
      })
    : null;
  const related = getDeviceEvidence(device.id);

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
            Device USB ID
            <DeviceSearchInput name="device" initialValue={rawDeviceId || device.id} />
            <span className="field-help">
              Enter a canonical USB VID/PID. <Link href="/devices">Search the catalog</Link> to find
              the device and open its prefilled checker link.
            </span>
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
            Ordered connection path <span className="optional">optional</span>
            <input name="path" defaultValue={rawPath} placeholder="direct_port>usb_hub" maxLength={120} />
            <span className="field-help">If supplied, this replaces the single connection choice above. Separate components with &gt;.</span>
          </label>
          <label>OS build <span className="optional">optional</span><input name="os_build" defaultValue={osBuild} maxLength={80} /></label>
          <label>Driver name <span className="optional">optional</span><input name="driver_name" defaultValue={driverName} maxLength={160} /></label>
          <label>Driver version <span className="optional">optional</span><input name="driver_version" defaultValue={driverVersion} maxLength={80} /></label>
          <label>Software name <span className="optional">optional</span><input name="software_name" defaultValue={softwareName} maxLength={160} /></label>
          <label>Software version <span className="optional">optional</span><input name="software_version" defaultValue={softwareVersion} maxLength={80} /></label>
          <label>Firmware version <span className="optional">optional</span><input name="firmware_version" defaultValue={firmwareVersion} maxLength={80} /></label>
          <label>USB generation <span className="optional">optional</span>
            <select name="usb_generation" defaultValue={usbGeneration}>
              <option value="">Unknown</option>
              {["1.1", "2.0", "3.0", "3.1", "3.2", "4"].map((generation) => <option key={generation} value={generation}>{generation}</option>)}
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

      {hasInvalidQuery ? (
        <section aria-live="polite">
          <div className="notice">
            <strong>Invalid configuration.</strong>
            <p>
              {invalidFields
                .map((field) =>
                  field === "device"
                    ? "device is outside the known USB identity catalog"
                    : `${field} is invalid or outside the available checker options`,
                )
                .join("; ")}.
              {" "}No compatibility claim was generated. Choose values from the form and try again.
            </p>
          </div>
        </section>
      ) : null}

      {result ? (
        <section>
          <p className="eyebrow">Result</p>
          <h2>{device.manufacturer} {device.name}</h2>
          <div className="result-grid">
            <article className="result-card">
              <span className="result-label">Observed compatibility</span>
              <strong className={`result-state badge-${result.claimState}`}>{result.claimState.replaceAll("_", " ")}</strong>
              <p>
                {result.specificity === "exact" ? "Matched the supplied host, OS version, architecture, and connection path. This is not a full-configuration guarantee." : null}
                {result.specificity === "host_relaxed" ? "Matched evidence on another or unspecified host; host specificity was relaxed." : null}
                {result.specificity === "os_version_relaxed" ? "Matched evidence only after relaxing both host and OS version." : null}
                {result.specificity === "none" ? "No observation matches the requested architecture, OS family, and connection path." : null}
              </p>
              {result.observations.length ? <p className="meta">Not checked: {result.uncheckedDimensions.join(", ")}.</p> : null}
            </article>
            <article className="result-card">
              <span className="result-label">Vendor support</span>
              <strong className={`result-state badge-${result.supportState}`}>{result.supportState.replaceAll("_", " ")}</strong>
              <p>
                {result.supportStatements.length
                  ? `${result.supportStatements.length} best-matching support ${result.supportStatements.length === 1 ? "statement" : "statements"}.`
                  : "No reviewed vendor statement matches this request."}
              </p>
              {result.supportStatements.length ? <p className="meta">Vendor scopes may specify an unqueried driver, software release, or minimum USB generation. Inspect the statements below before relying on support.</p> : null}
            </article>
          </div>

          {result.observationConditions.length ? (
            <div className="notice">
              <strong>Observed conditions</strong>
              <ul>{result.observationConditions.map((condition) => <li key={condition}>{condition}</li>)}</ul>
            </div>
          ) : null}
          {result.supportConditions.length ? <div className="notice"><strong>Vendor conditions</strong><ul>{result.supportConditions.map((condition) => <li key={condition}>{condition}</li>)}</ul></div> : null}

          <div className="stack compact-stack">
            {result.observations.map((observation) => (
              <article className="evidence-card" key={observation.observation_id}>
                <h3>Matched observation</h3>
                <p>{observation.host.manufacturer} {observation.host.model} · {observation.evidence.source_title}</p>
                <p className="meta">Observed {formatDate(observation.observed_at)} ({evidenceAge(observation.observed_at).status}; {evidenceAge(observation.observed_at).days} days old) · OS {observation.host.operating_system.version}{observation.host.operating_system.build ? ` build ${observation.host.operating_system.build}` : ""} · {observation.connection_path.map((item) => formatConnection(item.kind)).join(" → ")}</p>
                {observation.driver ? <p>Driver: {observation.driver.name} {observation.driver.version}</p> : null}
                {observation.software ? <p>Software: {observation.software.name} {observation.software.version}</p> : null}
                {observation.firmware_version ? <p>Firmware: {observation.firmware_version}</p> : null}
                {observation.limitations?.length ? <div className="notice compact-notice"><strong>Observation limitations</strong><ul>{observation.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul></div> : null}
                <a href={observation.evidence.source_url} rel="noreferrer" target="_blank">Open source ↗</a>
              </article>
            ))}
            {result.supportStatements.map((statement) => (
              <article className="evidence-card" key={statement.statement_id}>
                <h3>Matched support statement</h3>
                <p className="meta">{formatReleaseChannel(statement.release_channel)}</p>
                <p className="meta">Reviewed {formatDate(statement.reviewed_at)} ({evidenceAge(statement.reviewed_at).status}; {evidenceAge(statement.reviewed_at).days} days old){statement.scope.connection.minimum_usb_generation ? ` · Requires USB ${statement.scope.connection.minimum_usb_generation}+` : ""}</p>
                {statement.driver ? <p>Documented driver: {statement.driver.name}{statement.driver.version ? ` ${statement.driver.version}` : ""}</p> : null}
                {statement.software ? <p>Documented software: {statement.software.name}{statement.software.version ? ` ${statement.software.version}` : ""}</p> : null}
                <p>{statement.evidence.source_note}</p>
                {statement.limitations?.length ? (
                  <div className="notice compact-notice">
                    <strong>Scope limitations</strong>
                    <ul>{statement.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
                  </div>
                ) : null}
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
