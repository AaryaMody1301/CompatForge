import type { Metadata } from "next";
import Link from "next/link";

import {
  catalogCounts,
  catalogSource,
  compareDeviceNames,
  devices,
  searchDevices,
} from "@/lib/catalog";
import { getDeviceEvidence, observations, supportStatements } from "@/lib/evidence";
import { pageMetadata } from "@/lib/site";

export const metadata: Metadata = pageMetadata(
  "Devices",
  "Search the published USB identity snapshot and inspect CompatForge compatibility evidence separately.",
  "/devices",
);

const PAGE_SIZE = 48;
const evidenceDeviceIds = new Set([
  ...supportStatements.map((statement) => statement.device_id),
  ...observations.map((observation) => observation.device_id),
]);

type Props = {
  searchParams: Promise<{ q?: string | string[]; page?: string | string[] }>;
};

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function pageHref(query: string, page: number) {
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  if (page > 1) params.set("page", String(page));
  const suffix = params.toString();
  return suffix ? `/devices?${suffix}` : "/devices";
}

const defaultBrowseDevices = [...devices].sort(
  (left, right) =>
    Number(evidenceDeviceIds.has(right.id)) - Number(evidenceDeviceIds.has(left.id)) ||
    Number(right.reviewed_metadata) - Number(left.reviewed_metadata) ||
    compareDeviceNames(left, right),
);

export default async function DevicesPage({ searchParams }: Props) {
  const params = await searchParams;
  const query = (first(params.q) ?? "").trim();
  const parsedPage = Number.parseInt(first(params.page) ?? "1", 10);

  const results = query ? searchDevices(query) : defaultBrowseDevices;
  const pageCount = Math.max(1, Math.ceil(results.length / PAGE_SIZE));
  const currentPage =
    Number.isFinite(parsedPage) && parsedPage > 0 ? Math.min(parsedPage, pageCount) : 1;
  const offset = (currentPage - 1) * PAGE_SIZE;
  const visibleDevices = results.slice(offset, offset + PAGE_SIZE);
  const rangeStart = results.length ? offset + 1 : 0;
  const rangeEnd = Math.min(offset + PAGE_SIZE, results.length);
  const sourceVersion = catalogSource.version ? ` ${catalogSource.version}` : "";

  return (
    <main className="shell page-stack">
      <section className="compact-hero">
        <p className="eyebrow">Device catalog</p>
        <h1>Browse known hardware identities.</h1>
        <p>
          CompatForge publishes the USB ID Repository identity snapshot separately from compatibility
          evidence. A registry entry means the VID/PID is known; it does not mean the device is
          supported or observed working.
        </p>
        <p className="meta">
          Source: <a href={catalogSource.homepage} rel="noreferrer" target="_blank">
            usb.ids{sourceVersion} ↗
          </a>
          {catalogSource.snapshot_date ? ` · snapshot ${catalogSource.snapshot_date}` : ""}
          {" · "}
          {catalogCounts.devices.toLocaleString("en")} product identities
        </p>
        <form className="search-form" action="/devices" method="get">
          <label htmlFor="device-search">Search devices</label>
          <div className="search-row">
            <input
              id="device-search"
              name="q"
              defaultValue={query}
              placeholder="Arduino Uno, FT232R, Logitech, usb:046D:C52B…"
            />
            <button type="submit">Search</button>
          </div>
        </form>
      </section>

      <section>
        <p className="meta">
          Showing {rangeStart}–{rangeEnd} of {results.length.toLocaleString("en")} result(s)
          {query ? ` for “${query}”` : ""} · {catalogCounts.devices.toLocaleString("en")} total identities
        </p>
        {!query ? (
          <p className="meta">
            Evidence-backed and curated developer hardware is shown first; the remaining registry is
            ordered by vendor and product name.
          </p>
        ) : null}
        <div className="grid grid-two">
          {visibleDevices.map((device) => {
            const evidence = getDeviceEvidence(device.id);
            const hasEvidence =
              evidence.supportStatements.length > 0 || evidence.observations.length > 0;
            return (
              <article className="card device-card" key={device.id}>
                <p className="kicker">{device.category}</p>
                <h2 className="card-title">{device.manufacturer} {device.name}</h2>
                <code>{device.id}</code>
                <p>{device.summary}</p>
                <p className="meta">
                  {hasEvidence
                    ? `${evidence.supportStatements.length} support · ${evidence.observations.length} observed`
                    : "Identity known · compatibility evidence unknown"}
                </p>
                <div className="card-actions">
                  <Link href={`/devices/${device.slug}`}>
                    {hasEvidence ? "Review evidence" : "Identity details"}
                  </Link>
                  <Link href={`/check?device=${encodeURIComponent(device.id)}`}>Check configuration</Link>
                </div>
              </article>
            );
          })}
        </div>

        {results.length === 0 ? (
          <div className="empty-state">
            <h2>No catalog identity matches that search.</h2>
            <p>Try separate product/vendor words, an alias, or a canonical USB VID/PID.</p>
          </div>
        ) : null}

        {pageCount > 1 ? (
          <nav className="pagination" aria-label="Device catalog pages">
            {currentPage > 1 ? (
              <Link className="button" href={pageHref(query, currentPage - 1)}>Previous</Link>
            ) : (
              <span className="button button-disabled" aria-disabled="true">Previous</span>
            )}
            <span className="meta">Page {currentPage.toLocaleString("en")} of {pageCount.toLocaleString("en")}</span>
            {currentPage < pageCount ? (
              <Link className="button" href={pageHref(query, currentPage + 1)}>Next</Link>
            ) : (
              <span className="button button-disabled" aria-disabled="true">Next</span>
            )}
          </nav>
        ) : null}
      </section>
    </main>
  );
}
